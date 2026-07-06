"""
Job Tools API routes - Search, Match, Analyze, and Generate CV endpoints.
These endpoints power the hosted API service for CV tailoring.
"""
import logging
import asyncio
from typing import Optional, List
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, Depends, HTTPException

from api.schemas.auth import UserInfo
from api.schemas.job_tools import (
    JobSearchRequest,
    JobSearchResponse,
    JobItem,
    JobSource,
    JobMatchRequest,
    JobMatchResponse,
    JobAnalyzeRequest,
    JobAnalyzeResponse,
    CVGenerateRequest,
    CVGenerateResponse,
    CVFormat,
)
from api.middleware.auth_middleware import get_current_user
from api.services.job_analyzer import JobAnalyzerService
from api.services.cv_generator_service import CVGeneratorService

from config.settings import Config
from data_store.airtable_manager import AirtableManager
from utils.cv_loader import load_cv_content

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Job Tools"])

# Thread pool for CPU-bound scraping tasks
_executor = ThreadPoolExecutor(max_workers=3)


def _get_user_cv_text(user_email: str, cv_id: Optional[str] = None) -> str:
    """
    Get user's CV text from their saved configuration or CV library.

    Args:
        user_email: User's email address
        cv_id: Optional specific CV version ID

    Returns:
        CV text content

    Raises:
        HTTPException if CV not found
    """
    try:
        if cv_id:
            # Load specific CV version from library
            from data_store.cv_version_manager import get_cv_version_manager
            cv_manager = get_cv_version_manager()
            version = cv_manager.get_version(cv_id, user_email)
            if not version:
                raise HTTPException(status_code=404, detail="CV version not found")

            storage_path = version.get('storage_path')
            if not storage_path:
                raise HTTPException(status_code=404, detail="CV file not found in storage")

            cv_text = load_cv_content(f"minio://{storage_path}")
        else:
            # Load from user's saved config (base CV)
            airtable = AirtableManager(
                Config.AIRTABLE_API_KEY,
                Config.AIRTABLE_BASE_ID,
                Config.AIRTABLE_TABLE_ID
            )
            user_config = airtable.get_user_config(user_email)
            if not user_config:
                raise HTTPException(
                    status_code=400,
                    detail="No CV configured. Please upload a CV or configure your profile."
                )

            cv_path = user_config.get('base_cv_path')
            if not cv_path:
                raise HTTPException(
                    status_code=400,
                    detail="No CV found in your configuration. Please upload a CV."
                )

            cv_text = load_cv_content(cv_path)

        if not cv_text or not cv_text.strip():
            raise HTTPException(
                status_code=400,
                detail="Could not extract text from CV. Please ensure it's a valid document."
            )

        return cv_text

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to load CV for user {user_email}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to load CV: {str(e)}")


def _scrape_linkedin_jobs(keywords: str, location: str, max_jobs: int) -> List[JobItem]:
    """Scrape LinkedIn jobs (runs in thread pool)."""
    try:
        from api.routes.jobs import build_linkedin_search_url
        from job_sources.linkedin_job_scraper import LinkedInJobScraper

        url = build_linkedin_search_url(keywords, location)
        scraper = LinkedInJobScraper(url, max_jobs_to_scrape=max_jobs)
        raw_jobs = scraper.scrape_job_page(url) or []

        jobs = []
        for idx, job in enumerate(raw_jobs[:max_jobs]):
            jobs.append(JobItem(
                id=f"linkedin_{idx}_{hash(job.get('job_link', '')) % 10000}",
                title=job.get('title', 'Unknown Title'),
                company=job.get('company', 'Unknown Company'),
                location=job.get('location'),
                url=job.get('job_link', ''),
                source=JobSource.LINKEDIN,
                posted_date=job.get('posted_date'),
                salary=job.get('salary'),
                description=job.get('description')
            ))
        return jobs
    except Exception as e:
        logger.error(f"LinkedIn scraping failed: {e}")
        return []


def _scrape_seek_jobs(keywords: str, location: str, max_jobs: int) -> List[JobItem]:
    """Scrape Seek jobs (runs in thread pool)."""
    try:
        from api.routes.jobs import build_seek_url
        from job_sources.seek_job_scraper import SeekJobScraper

        url = build_seek_url(keywords, "information communication technology", location)
        scraper = SeekJobScraper(url, max_jobs_to_scrape=max_jobs)
        raw_jobs = scraper.scrape_jobs() or []

        jobs = []
        for idx, job in enumerate(raw_jobs[:max_jobs]):
            jobs.append(JobItem(
                id=f"seek_{idx}_{hash(job.get('job_link', '')) % 10000}",
                title=job.get('title', 'Unknown Title'),
                company=job.get('company', 'Unknown Company'),
                location=job.get('location'),
                url=job.get('job_link', ''),
                source=JobSource.SEEK,
                posted_date=job.get('posted_date'),
                salary=job.get('salary'),
                description=job.get('description')
            ))
        return jobs
    except Exception as e:
        logger.error(f"Seek scraping failed: {e}")
        return []


@router.post("/jobs/tools/search", response_model=JobSearchResponse)
async def search_jobs(
    request: JobSearchRequest,
    user: UserInfo = Depends(get_current_user)
) -> JobSearchResponse:
    """
    Search for jobs on LinkedIn and Seek.

    Args:
        request: Search parameters (keywords, location, sources, limit)
        user: Authenticated user

    Returns:
        List of matching jobs from specified sources
    """
    try:
        keywords = " ".join(request.keywords)
        location = request.location
        limit = request.limit or 20

        # Determine which sources to search
        sources = request.sources or [JobSource.LINKEDIN, JobSource.SEEK]

        all_jobs: List[JobItem] = []
        loop = asyncio.get_event_loop()

        # Calculate per-source limit
        per_source_limit = limit // len(sources) + 1

        # Run scrapers in parallel using thread pool
        tasks = []
        if JobSource.LINKEDIN in sources:
            tasks.append(loop.run_in_executor(
                _executor,
                _scrape_linkedin_jobs,
                keywords, location, per_source_limit
            ))
        if JobSource.SEEK in sources:
            tasks.append(loop.run_in_executor(
                _executor,
                _scrape_seek_jobs,
                keywords, location, per_source_limit
            ))

        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Scraping task failed: {result}")
                elif isinstance(result, list):
                    all_jobs.extend(result)

        # Limit total results
        all_jobs = all_jobs[:limit]

        return JobSearchResponse(
            jobs=all_jobs,
            total=len(all_jobs)
        )

    except Exception as e:
        logger.error(f"Job search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Job search failed: {str(e)}")


@router.post("/jobs/tools/match", response_model=JobMatchResponse)
async def match_jobs(
    request: JobMatchRequest,
    user: UserInfo = Depends(get_current_user)
) -> JobMatchResponse:
    """
    Score jobs against a user's CV using AI.

    Args:
        request: Jobs to match and CV source (cv_id or cv_text)
        user: Authenticated user

    Returns:
        Match results with scores, strengths, gaps, and recommendations
    """
    try:
        # Get CV text
        if request.cv_text:
            cv_text = request.cv_text
        else:
            cv_text = _get_user_cv_text(user.email, request.cv_id)

        # Run matching
        analyzer = JobAnalyzerService()
        loop = asyncio.get_event_loop()

        # Match all jobs (CPU-bound, run in thread pool)
        matches = await loop.run_in_executor(
            _executor,
            analyzer.batch_match_jobs,
            request.jobs,
            cv_text
        )

        return JobMatchResponse(matches=matches)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Job matching failed: {e}")
        raise HTTPException(status_code=500, detail=f"Job matching failed: {str(e)}")


@router.post("/jobs/tools/analyze", response_model=JobAnalyzeResponse)
async def analyze_job(
    request: JobAnalyzeRequest,
    user: UserInfo = Depends(get_current_user)
) -> JobAnalyzeResponse:
    """
    Deep analysis of a single job posting.

    Args:
        request: Job URL or description, and CV source
        user: Authenticated user

    Returns:
        Detailed analysis including fit assessment, strengths, gaps,
        cover letter angles, and interview prep
    """
    try:
        # Get job description
        job_description = request.job_description
        job_title = None
        company = None

        if request.job_url and not job_description:
            # Fetch job description from URL
            job_description, job_title, company = await _fetch_job_from_url(request.job_url)

        if not job_description:
            raise HTTPException(
                status_code=400,
                detail="Either job_url or job_description must be provided"
            )

        # Get CV text
        if request.cv_text:
            cv_text = request.cv_text
        else:
            cv_text = _get_user_cv_text(user.email, request.cv_id)

        # Run analysis
        analyzer = JobAnalyzerService()
        loop = asyncio.get_event_loop()

        result = await loop.run_in_executor(
            _executor,
            analyzer.analyze_job,
            job_description,
            cv_text,
            job_title,
            company
        )

        return JobAnalyzeResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Job analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Job analysis failed: {str(e)}")


@router.post("/cv/tools/generate", response_model=CVGenerateResponse)
async def generate_cv(
    request: CVGenerateRequest,
    user: UserInfo = Depends(get_current_user)
) -> CVGenerateResponse:
    """
    Generate a tailored CV for a specific job.

    Args:
        request: Job URL or description, CV source, format, and tone
        user: Authenticated user

    Returns:
        Generated CV with keywords emphasized and changes made
    """
    try:
        # Get job description
        job_description = request.job_description
        job_title = None
        company = None

        if request.job_url and not job_description:
            # Fetch job description from URL
            job_description, job_title, company = await _fetch_job_from_url(request.job_url)

        if not job_description:
            raise HTTPException(
                status_code=400,
                detail="Either job_url or job_description must be provided"
            )

        # Get CV text
        cv_text = _get_user_cv_text(user.email, request.cv_id)

        # Generate CV
        generator = CVGeneratorService()
        loop = asyncio.get_event_loop()

        result = await loop.run_in_executor(
            _executor,
            generator.generate_cv,
            cv_text,
            job_description,
            request.format or CVFormat.MARKDOWN,
            request.tone,
            job_title,
            company
        )

        return CVGenerateResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"CV generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"CV generation failed: {str(e)}")


async def _fetch_job_from_url(url: str) -> tuple[str, Optional[str], Optional[str]]:
    """
    Fetch job description from a URL by scraping.

    Args:
        url: Job posting URL

    Returns:
        Tuple of (description, title, company)
    """
    try:
        loop = asyncio.get_event_loop()

        if "linkedin.com" in url:
            from job_sources.linkedin_job_scraper import LinkedInJobScraper
            scraper = LinkedInJobScraper(url, max_jobs_to_scrape=1)

            # Get job description
            description = await loop.run_in_executor(
                _executor,
                scraper.get_job_description,
                url
            )

            return description or "", None, None

        elif "seek.com" in url:
            from job_sources.seek_job_scraper import SeekJobScraper
            scraper = SeekJobScraper(url, max_jobs_to_scrape=1)

            # Get full description
            description = await loop.run_in_executor(
                _executor,
                scraper._get_full_description,
                url
            )

            return description or "", None, None

        else:
            # Generic URL - try basic fetch
            import httpx
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url)
                if response.status_code == 200:
                    # Return raw HTML/text - AI will extract relevant info
                    return response.text[:15000], None, None

            raise HTTPException(
                status_code=400,
                detail="Could not fetch job description from URL. Please provide job_description directly."
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch job from URL {url}: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Could not fetch job from URL: {str(e)}"
        )
