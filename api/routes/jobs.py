"""
Job Search routes for WinningCV API.
Handles job search configuration, execution, and results.
"""
import os
import uuid
import logging
import math
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks, Query
from urllib.parse import urlencode, quote

from api.schemas.auth import UserInfo
from api.schemas.jobs import (
    JobConfigRequest,
    JobConfigResponse,
    SearchTaskResponse,
    SearchStatusResponse,
    SearchStatus,
    JobResult,
    JobResultsResponse,
)
from api.middleware.auth_middleware import get_current_user

# Import existing functionality
from data_store.airtable_manager import AirtableManager
from job_processing.core import JobProcessor
from config.settings import Config
from utils.utils import Struct
from ui.helpers import upload_pdf_to_wordpress
from job_sources.linkedin_cookie_manager import get_cookie_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/jobs", tags=["Job Search"])

# In-memory task storage (in production, use Redis or similar)
_search_tasks: Dict[str, dict] = {}

# Thread pool for background tasks
_executor = ThreadPoolExecutor(max_workers=3)

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
        cfg = Config()
        airtable = AirtableManager(
            cfg.AIRTABLE_API_KEY,
            cfg.AIRTABLE_BASE_ID,
            cfg.AIRTABLE_TABLE_ID
        )

        user_config = airtable.get_user_config(user.email)

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
    user: UserInfo = Depends(get_current_user)
) -> JobConfigResponse:
    """
    Save job search configuration.

    Args:
        Form fields for job search configuration
        cv_file: Optional CV file to upload
        user: Authenticated user

    Returns:
        Saved configuration
    """
    try:
        cfg = Config()
        airtable = AirtableManager(
            cfg.AIRTABLE_API_KEY,
            cfg.AIRTABLE_BASE_ID,
            cfg.AIRTABLE_TABLE_ID
        )

        # Handle CV upload if provided
        cv_path = ""
        cv_url = ""
        if cv_file:
            cv_dir = Path(f"user_cv/{user.email}")
            cv_dir.mkdir(parents=True, exist_ok=True)

            suffix = Path(cv_file.filename).suffix
            unique_filename = f"base_cv_{uuid.uuid4().hex[:8]}{suffix}"
            cv_path = str(cv_dir / unique_filename)

            content = await cv_file.read()
            with open(cv_path, "wb") as f:
                f.write(content)

            try:
                cv_url = upload_pdf_to_wordpress(
                    file_path=cv_path,
                    filename=unique_filename,
                    wp_site=cfg.WORDPRESS_SITE,
                    wp_user=cfg.WORDPRESS_USERNAME,
                    wp_app_password=cfg.WORDPRESS_APP_PASSWORD
                )
            except Exception as e:
                logger.warning(f"Failed to upload CV to WordPress: {e}")

        # Get existing config to preserve CV path if not uploading new one
        existing_config = airtable.get_user_config(user.email)
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

        # Build config dict for Airtable
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

        if not airtable.save_user_config(config_data):
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
    """Background task to run job search"""
    try:
        _search_tasks[task_id]["status"] = SearchStatus.RUNNING
        _search_tasks[task_id]["progress"] = 10
        _search_tasks[task_id]["message"] = "Initializing search..."

        # Progress callback to update task status in real-time
        def update_progress(progress: int, message: str):
            _search_tasks[task_id]["progress"] = progress
            _search_tasks[task_id]["message"] = message

        # Merge with defaults
        defaults = {k.lower(): v for k, v in Config.__dict__.items() if not k.startswith("_")}
        merged = {**defaults, **{k.lower(): v for k, v in config_data.items()}}
        merged["user_email"] = user_email

        update_progress(20, "Connecting to job boards...")

        # Initialize Airtable manager
        joblist_mgr = AirtableManager(
            Config.AIRTABLE_API_KEY,
            Config.AIRTABLE_BASE_ID,
            Config.AIRTABLE_TABLE_ID
        )

        # Create processor with progress callback
        processor = JobProcessor(
            config=Struct(**merged),
            airtable=joblist_mgr,
            progress_callback=update_progress
        )

        # process_jobs() will now call update_progress internally
        results = processor.process_jobs()

        _search_tasks[task_id]["progress"] = 100
        _search_tasks[task_id]["status"] = SearchStatus.COMPLETED
        _search_tasks[task_id]["message"] = f"Complete! Generated {len(results)} tailored CVs"
        _search_tasks[task_id]["results_count"] = len(results)

    except Exception as e:
        logger.error(f"Job search failed: {e}")
        _search_tasks[task_id]["status"] = SearchStatus.FAILED
        _search_tasks[task_id]["message"] = str(e)


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
        cfg = Config()
        airtable = AirtableManager(
            cfg.AIRTABLE_API_KEY,
            cfg.AIRTABLE_BASE_ID,
            cfg.AIRTABLE_TABLE_ID
        )

        # Get user's config
        user_config = airtable.get_user_config(user.email)
        if not user_config:
            raise HTTPException(
                status_code=400,
                detail="No job search configuration found. Please configure search settings first."
            )

        # Create task
        task_id = str(uuid.uuid4())
        _search_tasks[task_id] = {
            "status": SearchStatus.PENDING,
            "progress": 0,
            "message": "Task created",
            "results_count": None,
            "created_at": datetime.now().isoformat()
        }

        # Run in background thread (job processing uses blocking I/O)
        _executor.submit(_run_job_search, task_id, user.email, user_config)

        return SearchTaskResponse(
            task_id=task_id,
            status=SearchStatus.PENDING,
            message="Job search started"
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
    if task_id not in _search_tasks:
        raise HTTPException(
            status_code=404,
            detail="Task not found"
        )

    task = _search_tasks[task_id]

    return SearchStatusResponse(
        task_id=task_id,
        status=task["status"],
        progress=task["progress"],
        message=task["message"],
        results_count=task.get("results_count")
    )


@router.get("/results", response_model=JobResultsResponse)
async def get_job_results(
    user: UserInfo = Depends(get_current_user),
    limit: int = 100
) -> JobResultsResponse:
    """
    Get the user's job search results.

    Args:
        user: Authenticated user
        limit: Maximum number of results

    Returns:
        List of job results
    """
    try:
        cfg = Config()
        joblist_manager = AirtableManager(
            cfg.AIRTABLE_API_KEY,
            cfg.AIRTABLE_BASE_ID,
            cfg.AIRTABLE_TABLE_ID
        )

        records = joblist_manager.get_records_by_filter(f"{{User Email}} = '{user.email}'")

        items = []
        for rec in records[:limit]:
            fields = rec.get("fields", {})

            # Parse match reasons and suggestions
            reasons_raw = fields.get("Match Reasons", "")
            suggestions_raw = fields.get("Match Suggestions", "")

            reasons = reasons_raw.split("\n") if reasons_raw else None
            suggestions = suggestions_raw.split("\n") if suggestions_raw else None

            items.append(JobResult(
                id=rec.get("id", ""),
                job_title=fields.get("Job Title", "Untitled"),
                company=fields.get("Company", "Unknown"),
                location=fields.get("Location"),
                score=float(fields.get("Matching Score", 0)),
                cv_link=fields.get("CV Link") or None,
                job_link=fields.get("Job Link", ""),
                posted_date=fields.get("Job Date"),
                description=fields.get("Job Description"),
                match_reasons=reasons,
                suggestions=suggestions
            ))

        # Sort by score descending
        items.sort(key=lambda x: x.score, reverse=True)

        return JobResultsResponse(
            items=items,
            total=len(items)
        )

    except Exception as e:
        logger.error(f"Failed to get job results: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get results: {str(e)}"
        )


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
        from job_sources.linkedin_cookie_health import check_cookie_health, CookieStatus

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
