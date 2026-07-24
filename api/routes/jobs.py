"""
Job Search routes for WinningCV API.
Handles job search configuration, execution, and results.
"""
import fcntl
import json
import logging
import math
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import quote, urlencode

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile

from api.middleware.auth_middleware import get_current_user
from api.schemas.auth import UserInfo
from api.schemas.jobs import (
    ApplicationStatusUpdate,
    JobConfigResponse,
    JobResult,
    JobResultsResponse,
    ScoreBreakdown,
    SearchStatus,
    SearchStatusResponse,
    SearchTaskResponse,
)
from config.settings import Config

# Import storage factory for backend-agnostic access
from data_store.storage_factory import get_cv_version_manager, get_data_manager, get_history_manager
from job_processing.core import JobProcessor
from job_sources.linkedin_cookie_manager import get_cookie_manager
from ui.helpers import upload_pdf_to_wordpress
from utils.minio_storage import MinIOStorage
from utils.utils import Struct

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/jobs", tags=["Job Search"])

# Thread pool for background tasks
_executor = ThreadPoolExecutor(max_workers=3)


# =============================================================================
# File-based task manager (fallback when Postgres unavailable)
# =============================================================================

class FileBasedTaskManager:
    """
    File-based task storage for development/fallback.
    Uses /tmp storage with file locking for cross-process sharing.
    """
    _TASKS_FILE = Path("/tmp/winningcv_search_tasks.json")

    def _read_tasks(self) -> Dict[str, dict]:
        """Read tasks from shared file with locking."""
        if not self._TASKS_FILE.exists():
            return {}
        try:
            with open(self._TASKS_FILE, 'r') as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                try:
                    return json.load(f)
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        except (json.JSONDecodeError, IOError):
            return {}

    def _write_tasks(self, tasks: Dict[str, dict]):
        """Write tasks to shared file with locking."""
        with open(self._TASKS_FILE, 'w') as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                json.dump(tasks, f)
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)

    def create_task(
        self,
        task_id: str,
        user_email: str,
        status: str = "pending",
        message: str = "Task created"
    ) -> Dict[str, Any]:
        """Create a new task."""
        tasks = self._read_tasks()
        task_data = {
            "task_id": task_id,
            "user_email": user_email,
            "status": status,
            "progress": 0,
            "message": message,
            "results_count": None,
            "created_at": datetime.now().isoformat(),
        }
        tasks[task_id] = task_data
        self._write_tasks(tasks)
        return task_data

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task by ID."""
        tasks = self._read_tasks()
        return tasks.get(task_id)

    def update_task(
        self,
        task_id: str,
        status: Optional[str] = None,
        progress: Optional[int] = None,
        message: Optional[str] = None,
        results_count: Optional[int] = None,
        error_details: Optional[str] = None
    ) -> bool:
        """Update task fields."""
        tasks = self._read_tasks()
        if task_id not in tasks:
            return False

        if status is not None:
            tasks[task_id]["status"] = status
        if progress is not None:
            tasks[task_id]["progress"] = progress
        if message is not None:
            tasks[task_id]["message"] = message
        if results_count is not None:
            tasks[task_id]["results_count"] = results_count
        if error_details is not None:
            tasks[task_id]["error_details"] = error_details

        self._write_tasks(tasks)
        return True


# Cached task manager instance
_task_manager = None


def _get_task_manager():
    """Get the task manager, preferring Postgres for durability."""
    global _task_manager
    if _task_manager is not None:
        return _task_manager

    try:
        from data_store.storage_factory import get_task_manager
        _task_manager = get_task_manager()
    except Exception as e:
        logger.warning(f"Using file-based task manager: {e}")
        _task_manager = FileBasedTaskManager()

    return _task_manager

# LinkedIn GeoID mapping
LINKEDIN_GEOID_MAP = {
    "Australia": "101452733",
    "Greater Sydney": "90009524",
    "Greater Melbourne": "90009521",
    "United States": "103644278",
    "United Kingdom": "101165590",
    "Canada": "101174742",
    "Hong Kong": "103291313",
    "Singapore": "102454443"
}


def build_linkedin_search_url(
    keywords: str,
    location: str,
    posted_hours: Optional[int] = None,
    geoId_map: Optional[dict] = None
) -> str:
    """Build LinkedIn job search URL from parameters"""
    if geoId_map is None:
        geoId_map = LINKEDIN_GEOID_MAP

    base = "https://www.linkedin.com/jobs/search/"
    params = {}

    if keywords:
        params['keywords'] = keywords.replace(",", " OR ")
    if location:
        geoId = geoId_map.get(location, "")
        if geoId:
            params['geoId'] = geoId
        params['location'] = location
    if posted_hours:
        try:
            seconds = int(posted_hours) * 3600
            params['f_TPR'] = f"r{seconds}"
        except:
            pass

    return f"{base}?{urlencode(params)}"


def build_seek_url(
    keywords: str,
    category: str,
    location: str,
    daterange: Optional[int] = None,
    salaryrange: Optional[str] = None,
    salarytype: str = "annual"
) -> str:
    """Build SEEK job search URL from parameters"""
    keywords_path = quote(keywords.replace(" ", "-"))
    category_path = quote(category.strip().replace(" ", "-").lower())
    location_path = quote(location.strip().replace(" ", "-").lower())

    base = f"https://www.seek.com.au/{keywords_path}-jobs-in-{category_path}/in-{location_path}"
    params = {}

    if daterange:
        params['daterange'] = str(daterange)
    if salaryrange:
        params['salaryrange'] = salaryrange
    if salarytype:
        params['salarytype'] = salarytype

    if params:
        return f"{base}?{urlencode(params)}"
    return base


@router.get("/config", response_model=JobConfigResponse)
async def get_job_config(
    user: UserInfo = Depends(get_current_user)
) -> JobConfigResponse:
    """
    Get the user's saved job search configuration.

    Args:
        user: Authenticated user

    Returns:
        Job search configuration
    """
    try:
        cfg = Config
        manager = get_data_manager()

        user_config = manager.get_user_config(user.email)

        if not user_config:
            # Return defaults
            return JobConfigResponse(
                user_email=user.email,
                location=cfg.LOCATION,
                hours_old=cfg.HOURS_OLD,
                results_wanted=cfg.RESULTS_WANTED,
                country=cfg.COUNTRY,
                max_jobs_to_scrape=cfg.MAX_JOBS_TO_SCRAPE
            )

        return JobConfigResponse(
            user_email=user.email,
            base_cv_path=user_config.get("base_cv_path"),
            base_cv_link=user_config.get("base_cv_link"),
            linkedin_job_url=user_config.get("linkedin_job_url"),
            seek_job_url=user_config.get("seek_job_url"),
            max_jobs_to_scrape=user_config.get("max_jobs_to_scrape", 10),
            additional_search_term=user_config.get("additional_search_term"),
            google_search_term=user_config.get("google_search_term"),
            location=user_config.get("location", cfg.LOCATION),
            hours_old=user_config.get("hours_old", cfg.HOURS_OLD),
            results_wanted=user_config.get("results_wanted", cfg.RESULTS_WANTED),
            country=user_config.get("country", cfg.COUNTRY)
        )

    except Exception as e:
        logger.error(f"Failed to get job config: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get configuration: {str(e)}"
        )


@router.post("/config", response_model=JobConfigResponse)
async def save_job_config(
    # Form fields instead of Pydantic model (frontend sends FormData)
    search_keywords: str = Form(..., min_length=2, description="Keywords for job search"),
    location: str = Form(..., description="Job location"),
    search_term: str = Form(default="", description="Indeed/Glassdoor search terms"),
    google_term: str = Form(default="", description="Google custom search terms"),
    seek_category: str = Form(default="information communication technology"),
    seek_salaryrange: Optional[str] = Form(default=None),
    seek_salarytype: str = Form(default="annual"),
    max_jobs: int = Form(default=10, ge=1, le=50),
    hours_old: int = Form(default=168, ge=24, le=720),
    results_wanted: int = Form(default=10, ge=1, le=50),
    country: str = Form(default="Australia"),
    cv_file: Optional[UploadFile] = File(None),
    selected_cv_version_id: Optional[str] = Form(None, description="ID of CV version from library to use as base CV"),
    user: UserInfo = Depends(get_current_user)
) -> JobConfigResponse:
    """
    Save job search configuration.

    Args:
        Form fields for job search configuration
        cv_file: Optional CV file to upload (takes priority over selected_cv_version_id)
        selected_cv_version_id: Optional CV version ID from library to use as base CV
        user: Authenticated user

    Returns:
        Saved configuration
    """
    try:
        cfg = Config
        manager = get_data_manager()

        # Handle CV: either upload new file or select from library
        cv_path = ""
        cv_url = ""

        if cv_file:
            # Option 1: Upload new CV file
            cv_dir = Path(f"user_cv/{user.email}")
            cv_dir.mkdir(parents=True, exist_ok=True)

            suffix = Path(cv_file.filename).suffix
            unique_filename = f"base_cv_{uuid.uuid4().hex[:8]}{suffix}"
            cv_path = str(cv_dir / unique_filename)

            content = await cv_file.read()
            with open(cv_path, "wb") as f:
                f.write(content)

            # Upload to MinIO for persistent storage (survives container restarts)
            try:
                minio = MinIOStorage()
                content_type = "application/pdf"
                if suffix.lower() == ".docx":
                    content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

                object_path = minio.upload_cv(
                    file_path=cv_path,
                    user_id=user.email,
                    filename=unique_filename,
                    content_type=content_type
                )
                cv_url = minio.get_download_url_by_path(object_path, expires_hours=24)
                logger.info(f"Uploaded base CV to MinIO: {object_path}")
            except Exception as e:
                logger.warning(f"Failed to upload CV to MinIO: {e}")
                # Fallback to WordPress (deprecated)
                try:
                    cv_url = upload_pdf_to_wordpress(
                        file_path=cv_path,
                        filename=unique_filename,
                        wp_site=cfg.WORDPRESS_SITE,
                        wp_user=cfg.WORDPRESS_USERNAME,
                        wp_app_password=cfg.WORDPRESS_APP_PASSWORD
                    )
                except Exception as wp_e:
                    logger.warning(f"Failed to upload CV to WordPress: {wp_e}")

        elif selected_cv_version_id:
            # Option 2: Use CV from library
            try:
                cv_manager = get_cv_version_manager()
                version = cv_manager.get_version(selected_cv_version_id, user.email)

                if not version:
                    raise HTTPException(status_code=404, detail="Selected CV version not found")

                storage_path = version.get('storage_path')
                if not storage_path:
                    raise HTTPException(status_code=404, detail="CV file not found in storage")

                # Use a special path format that cv_loader can recognize as MinIO storage path
                # Format: minio://{storage_path} - cv_loader will handle this specially
                cv_path = f"minio://{storage_path}"

                # Get presigned URL for the version
                cv_url = cv_manager.get_download_url(selected_cv_version_id, user.email)

                logger.info(f"Using CV from library: {version.get('version_name')} -> {cv_path}")

            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Failed to use CV from library: {e}")
                raise HTTPException(status_code=500, detail=f"Failed to load CV from library: {str(e)}")

        # Get existing config to preserve CV path if not uploading/selecting new one
        existing_config = manager.get_user_config(user.email)
        if not cv_path and existing_config:
            cv_path = existing_config.get("base_cv_path", "")
            cv_url = existing_config.get("base_cv_link", "")

        # Build URLs from search parameters
        linkedin_url = build_linkedin_search_url(
            search_keywords,
            location,
            posted_hours=hours_old
        )

        seek_url = build_seek_url(
            search_keywords,
            seek_category,
            location,
            daterange=int(math.ceil(hours_old / 24)),
            salaryrange=seek_salaryrange,
            salarytype=seek_salarytype
        )

        # Build config dict for storage
        config_data = {
            "user_email": user.email,
            "base_cv_path": cv_path,
            "base_cv_link": cv_url,
            "linkedin_job_url": linkedin_url,
            "seek_job_url": seek_url,
            "max_jobs_to_scrape": max_jobs,
            "additional_search_term": search_term,
            "google_search_term": google_term,
            "location": location,
            "hours_old": hours_old,
            "results_wanted": results_wanted,
            "country": country
        }

        if not manager.save_user_config(config_data):
            raise HTTPException(
                status_code=500,
                detail="Failed to save configuration"
            )

        return JobConfigResponse(**config_data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to save job config: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save configuration: {str(e)}"
        )


def _run_job_search(task_id: str, user_email: str, config_data: dict):
    """
    Background task to run job search.

    Synchronous fallback for environments without the durable worker queue.
    Production job searches are enqueued into task_queue and processed by run_worker.py.
    """
    task_mgr = _get_task_manager()
    try:
        task_mgr.update_task(task_id, status=SearchStatus.RUNNING.value, progress=10, message="Initializing search...")

        # Progress callback to update task status in real-time
        def update_progress(progress: int, message: str):
            task_mgr.update_task(task_id, progress=progress, message=message)

        # Merge with defaults
        defaults = {k.lower(): v for k, v in Config.__dict__.items() if not k.startswith("_")}
        merged = {**defaults, **{k.lower(): v for k, v in config_data.items()}}
        merged["user_email"] = user_email

        update_progress(20, "Connecting to job boards...")

        # Get storage manager (backend-aware)
        joblist_mgr = get_data_manager()

        # Create processor with progress callback
        processor = JobProcessor(
            config=Struct(**merged),
            airtable=joblist_mgr,
            progress_callback=update_progress
        )

        # process_jobs() will now call update_progress internally
        results = processor.process_jobs()

        task_mgr.update_task(
            task_id,
            progress=100,
            status=SearchStatus.COMPLETED.value,
            message=f"Complete! Generated {len(results)} tailored CVs",
            results_count=len(results)
        )

    except Exception as e:
        logger.error(f"Job search failed: {e}")
        task_mgr.update_task(task_id, status=SearchStatus.FAILED.value, message=str(e), error_details=str(e))


@router.post("/search", response_model=SearchTaskResponse)
async def start_job_search(
    background_tasks: BackgroundTasks,
    user: UserInfo = Depends(get_current_user)
) -> SearchTaskResponse:
    """
    Start an asynchronous job search.

    Args:
        user: Authenticated user

    Returns:
        Task ID to poll for status
    """
    try:
        manager = get_data_manager()

        # Get user's config
        user_config = manager.get_user_config(user.email)
        if not user_config:
            raise HTTPException(
                status_code=400,
                detail="No job search configuration found. Please configure search settings first."
            )

        # Create task using durable storage (Postgres preferred, file fallback)
        task_id = str(uuid.uuid4())
        task_mgr = _get_task_manager()
        task_mgr.create_task(
            task_id=task_id,
            user_email=user.email,
            status=SearchStatus.PENDING.value,
            message="Task created"
        )

        # Prefer the durable Postgres queue for long-running scraping/generation jobs.
        # Fall back to the API thread pool only if the queue is unavailable (e.g. dev).
        queued = False
        try:
            from data_store.postgres_manager import get_postgres_task_queue
            queue = get_postgres_task_queue()
            queue.enqueue(
                task_id=f"job-search-{task_id}",
                task_type="job_search",
                payload={"search_task_id": task_id, "user_email": user.email, "config_data": user_config},
                priority=5,
                max_attempts=2,
                user_email=user.email,
                correlation_id=task_id,
            )
            task_mgr.update_task(task_id, message="Queued for worker processing", progress=2)
            queued = True
        except Exception as queue_error:
            logger.warning(f"Durable queue unavailable; falling back to API thread: {queue_error}")

        if not queued:
            _executor.submit(_run_job_search, task_id, user.email, user_config)

        return SearchTaskResponse(
            task_id=task_id,
            status=SearchStatus.PENDING,
            message="Job search queued" if queued else "Job search started"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start job search: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start search: {str(e)}"
        )


@router.get("/search/{task_id}/status", response_model=SearchStatusResponse)
async def get_search_status(
    task_id: str,
    user: UserInfo = Depends(get_current_user)
) -> SearchStatusResponse:
    """
    Get the status of a job search task.

    Args:
        task_id: Task ID from start_job_search
        user: Authenticated user

    Returns:
        Current status of the search task
    """
    task_mgr = _get_task_manager()
    task = task_mgr.get_task(task_id)
    if not task:
        raise HTTPException(
            status_code=404,
            detail="Task not found"
        )

    return SearchStatusResponse(
        task_id=task_id,
        status=task["status"],
        progress=task["progress"],
        message=task["message"],
        results_count=task.get("results_count")
    )


@router.get("/search/tasks", response_model=List[SearchStatusResponse])
async def get_user_search_tasks(
    user: UserInfo = Depends(get_current_user),
    include_completed: bool = False,
    limit: int = 5
) -> List[SearchStatusResponse]:
    """
    Get the user's recent search tasks.

    Enables task resumption after page refresh.

    Args:
        user: Authenticated user
        include_completed: Whether to include completed/failed tasks
        limit: Maximum number of tasks to return

    Returns:
        List of recent search tasks
    """
    task_mgr = _get_task_manager()

    # Check if task manager supports user tasks (Postgres-backed)
    if hasattr(task_mgr, 'get_user_tasks'):
        tasks = task_mgr.get_user_tasks(
            user_email=user.email,
            limit=limit,
            include_completed=include_completed
        )
    else:
        # File-based fallback: scan all tasks for user's tasks
        # This is less efficient but maintains compatibility
        tasks = []
        if hasattr(task_mgr, '_read_tasks'):
            all_tasks = task_mgr._read_tasks()
            for task_id, task in all_tasks.items():
                if task.get('user_email') == user.email:
                    if include_completed or task.get('status') not in ('completed', 'failed'):
                        tasks.append({
                            'task_id': task_id,
                            'status': task.get('status', 'pending'),
                            'progress': task.get('progress', 0),
                            'message': task.get('message', ''),
                            'results_count': task.get('results_count')
                        })
            tasks = tasks[:limit]

    return [
        SearchStatusResponse(
            task_id=t.get('task_id', ''),
            status=t.get('status', 'pending'),
            progress=t.get('progress', 0),
            message=t.get('message', ''),
            results_count=t.get('results_count')
        )
        for t in tasks
    ]


def _user_jobs_formula(user_email: str) -> str:
    """Build an Airtable-compatible, escaped user ownership filter."""
    safe_email = user_email.replace("'", "\\'")
    return f"{{User Email}} = '{safe_email}'"


def _cv_dates_by_url(history_records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Map generated CV URLs to their creation timestamps."""
    cv_dates = {}
    for record in history_records:
        fields = record.get("fields", {})
        cv_url = fields.get("cv_pdf_url", "")
        created_at = fields.get("created_at")
        if cv_url and created_at:
            cv_dates[cv_url] = created_at
    return cv_dates


def _job_result_from_record(rec: Dict[str, Any], cv_dates: Dict[str, Any]) -> JobResult:
    """Convert a storage record into the public job result shape."""
    fields = rec.get("fields", {})
    reasons_raw = fields.get("Match Reasons", "")
    suggestions_raw = fields.get("Match Suggestions", "")
    reasons = reasons_raw.split("\n") if reasons_raw else None
    suggestions = suggestions_raw.split("\n") if suggestions_raw else None

    cv_link = fields.get("CV Link") or None
    cv_generated_at = None
    if cv_link and cv_link in cv_dates:
        try:
            cv_generated_at = datetime.fromisoformat(cv_dates[cv_link].replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            pass

    score_breakdown = None
    ats_score = fields.get("Matching Score")
    hr_score = fields.get("HR Score")
    if ats_score is not None or hr_score is not None:
        matched_kw_raw = fields.get("Matched Keywords", "")
        missing_kw_raw = fields.get("Missing Keywords", "")
        matched_keywords = [kw.strip() for kw in matched_kw_raw.split(",") if kw.strip()] if matched_kw_raw else None
        missing_keywords = [kw.strip() for kw in missing_kw_raw.split(",") if kw.strip()] if missing_kw_raw else None
        score_breakdown = ScoreBreakdown(
            ats_score=float(ats_score) if ats_score else None,
            hr_score=float(hr_score) if hr_score else None,
            llm_score=float(fields.get("LLM Score")) if fields.get("LLM Score") else None,
            recommendation=fields.get("HR Recommendation"),
            matched_keywords=matched_keywords,
            missing_keywords=missing_keywords,
        )

    return JobResult(
        id=rec.get("id", ""),
        job_title=fields.get("Job Title", "Untitled"),
        company=fields.get("Company", "Unknown"),
        location=fields.get("Location"),
        score=float(fields.get("Matching Score", 0)),
        score_breakdown=score_breakdown,
        cv_link=cv_link,
        cv_generated_at=cv_generated_at,
        job_link=fields.get("Job Link", ""),
        posted_date=fields.get("Job Date"),
        description=fields.get("Job Description"),
        match_reasons=reasons,
        suggestions=suggestions,
        application_status=fields.get("Application Status") or "saved",
        application_notes=fields.get("Application Notes"),
        applied_at=fields.get("Applied At"),
    )


@router.get("/results", response_model=JobResultsResponse)
async def get_job_results(
    user: UserInfo = Depends(get_current_user),
    limit: int = 100,
    sort_by: str = "date"  # "date" or "score"
) -> JobResultsResponse:
    """Get the authenticated user's job search results."""
    try:
        joblist_manager = get_data_manager()
        history_manager = get_history_manager()
        cv_dates = _cv_dates_by_url(history_manager.get_history_by_user(user.email))
        records = joblist_manager.get_records_by_filter(_user_jobs_formula(str(user.email)))
        items = [_job_result_from_record(rec, cv_dates) for rec in records[:limit]]

        def parse_date(date_str):
            """Parse date string to datetime."""
            if not date_str:
                return datetime.min
            try:
                return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                try:
                    return datetime.strptime(date_str, "%Y-%m-%d")
                except (ValueError, AttributeError):
                    return datetime.min

        if sort_by == "score":
            items.sort(key=lambda item: (item.score, parse_date(item.posted_date)), reverse=True)
        else:
            items.sort(key=lambda item: (parse_date(item.posted_date), item.score), reverse=True)

        return JobResultsResponse(items=items, total=len(items))
    except Exception as e:
        logger.error(f"Failed to get job results: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get results: {str(e)}")


@router.get("/results/{job_id}", response_model=JobResult)
async def get_job_result(
    job_id: str,
    user: UserInfo = Depends(get_current_user),
) -> JobResult:
    """Get one owned job by its path-safe PostgreSQL UUID or Airtable record ID."""
    try:
        manager = get_data_manager()
        record = manager.get_job_result(job_id=job_id, user_email=str(user.email))
        if record is None:
            raise HTTPException(status_code=404, detail="Job not found")

        history = get_history_manager().get_history_by_user(user.email)
        return _job_result_from_record(record, _cv_dates_by_url(history))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get job result: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get result: {str(e)}")


@router.patch("/results/{job_id}/application", response_model=JobResult)
async def update_application_status_result(
    job_id: str,
    update: ApplicationStatusUpdate,
    user: UserInfo = Depends(get_current_user)
) -> JobResult:
    """Update tracking for a path-safe PostgreSQL UUID or Airtable record ID."""
    try:
        manager = get_data_manager()
        if not hasattr(manager, "update_application_status"):
            raise HTTPException(status_code=501, detail="Application tracking is only available on the Postgres backend")

        updated = manager.update_application_status(
            job_id=job_id,
            user_email=user.email,
            application_status=update.application_status.value,
            application_notes=update.application_notes,
        )
        if not updated:
            raise HTTPException(status_code=404, detail="Job not found")

        record = manager.get_job_result(job_id=job_id, user_email=str(user.email))
        if record is None:
            raise HTTPException(status_code=404, detail="Job not found")
        history = get_history_manager().get_history_by_user(user.email)
        return _job_result_from_record(record, _cv_dates_by_url(history))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update application status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update application status: {str(e)}")


@router.get("/linkedin/status")
async def get_linkedin_status(
    user: UserInfo = Depends(get_current_user)
) -> dict:
    """
    Check LinkedIn authentication status.

    Returns information about whether LinkedIn cookies are saved
    and when they were last updated.

    Args:
        user: Authenticated user

    Returns:
        LinkedIn authentication status
    """
    try:
        cookie_manager = get_cookie_manager()

        if not cookie_manager.has_cookies():
            return {
                "authenticated": False,
                "message": "No LinkedIn session saved. Run the login utility to enable authenticated access.",
                "instructions": "python -m job_sources.linkedin_login"
            }

        info = cookie_manager.get_cookie_info()
        if info:
            return {
                "authenticated": True,
                "saved_at": info.get("saved_at"),
                "cookie_count": info.get("cookie_count"),
                "message": "LinkedIn session available. Scraping will use authenticated access."
            }
        else:
            return {
                "authenticated": False,
                "message": "Could not read saved session. Try re-authenticating.",
                "instructions": "python -m job_sources.linkedin_login --clear && python -m job_sources.linkedin_login"
            }

    except Exception as e:
        logger.error(f"Failed to check LinkedIn status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to check status: {str(e)}"
        )


@router.get("/linkedin/health")
async def get_linkedin_cookie_health(
    user: UserInfo = Depends(get_current_user)
) -> dict:
    """
    Get detailed LinkedIn cookie health status.

    Returns comprehensive information about cookie age, health status,
    and whether refresh is recommended.

    Args:
        user: Authenticated user

    Returns:
        Cookie health information including status, age, and recommendations
    """
    try:
        from job_sources.linkedin_cookie_health import check_cookie_health

        health = check_cookie_health()

        # Convert enum to string for JSON serialization
        return {
            "status": health["status"].value,
            "age_days": health["age_days"],
            "age_hours": health["age_hours"],
            "saved_at": health["saved_at"],
            "cookie_count": health["cookie_count"],
            "message": health["message"],
            "needs_refresh": health["needs_refresh"],
            "status_level": _get_status_level(health["status"]),
            "instructions": "python -m job_sources.linkedin_login" if health["needs_refresh"] else None
        }

    except Exception as e:
        logger.error(f"Failed to check LinkedIn cookie health: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to check cookie health: {str(e)}"
        )


def _get_status_level(status) -> str:
    """Map cookie status to severity level for UI display."""
    from job_sources.linkedin_cookie_health import CookieStatus
    level_map = {
        CookieStatus.HEALTHY: "success",
        CookieStatus.AGING: "info",
        CookieStatus.STALE: "warning",
        CookieStatus.EXPIRED: "error",
        CookieStatus.MISSING: "error",
        CookieStatus.INVALID: "error",
    }
    return level_map.get(status, "unknown")
