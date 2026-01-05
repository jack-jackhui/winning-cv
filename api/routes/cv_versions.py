"""
CV Version Management API Routes.

Handles CRUD operations for CV versions, smart matching, and analytics.
"""
import logging
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query

from api.schemas.auth import UserInfo
from api.schemas.cv import (
    CVVersionCreate,
    CVVersionUpdate,
    CVVersionResponse,
    CVVersionListResponse,
    CVVersionForkRequest,
    CVVersionMatchRequest,
    CVVersionMatchResponse,
    CVVersionMatchScore,
    CVVersionAnalyticsResponse,
    CVVersionBulkActionRequest,
    CVVersionBulkActionResponse,
)
from api.middleware.auth_middleware import get_current_user
from data_store.cv_version_manager import get_cv_version_manager, CVVersionManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cv/versions", tags=["CV Versions"])


def _version_to_response(version: dict, include_url: bool = False) -> CVVersionResponse:
    """Convert version dict to response schema."""
    # Parse tags from comma-separated string
    tags = []
    if version.get('user_tags'):
        tags = [t.strip() for t in version['user_tags'].split(',') if t.strip()]

    # Parse created_at
    created_at = datetime.now()
    if version.get('created_at'):
        try:
            created_at = datetime.fromisoformat(version['created_at'].replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            pass

    return CVVersionResponse(
        id=version.get('id', ''),
        version_id=version.get('version_id', ''),
        user_email=version.get('user_email', ''),
        version_name=version.get('version_name', ''),
        auto_category=version.get('auto_category') or None,
        user_tags=tags,
        storage_path=version.get('storage_path', ''),
        parent_version_id=version.get('parent_version_id') or None,
        is_archived=version.get('is_archived', False),
        usage_count=version.get('usage_count', 0),
        response_count=version.get('response_count', 0),
        source_job_link=version.get('source_job_link') or None,
        source_job_title=version.get('source_job_title') or None,
        file_size=version.get('file_size', 0),
        content_hash=version.get('content_hash') or None,
        created_at=created_at,
        download_url=version.get('download_url') if include_url else None
    )


@router.get("", response_model=CVVersionListResponse)
async def list_versions(
    user: UserInfo = Depends(get_current_user),
    include_archived: bool = Query(False, description="Include archived versions"),
    category: Optional[str] = Query(None, description="Filter by category"),
    tags: Optional[str] = Query(None, description="Filter by tags (comma-separated)"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0)
) -> CVVersionListResponse:
    """
    List all CV versions for the authenticated user.

    Supports filtering by category and tags, with pagination.
    """
    manager = get_cv_version_manager()

    tag_list = None
    if tags:
        tag_list = [t.strip() for t in tags.split(',') if t.strip()]

    versions = manager.list_versions(
        user_email=user.email,
        include_archived=include_archived,
        category=category,
        tags=tag_list,
        limit=limit,
        offset=offset
    )

    # Get all versions count for total (without pagination)
    all_versions = manager.list_versions(
        user_email=user.email,
        include_archived=include_archived,
        limit=1000
    )

    # Get categories and tags for filtering UI
    categories = manager.get_categories(user.email)
    all_tags = manager.get_all_tags(user.email)

    items = [_version_to_response(v) for v in versions]

    return CVVersionListResponse(
        items=items,
        total=len(all_versions),
        categories=categories,
        tags=all_tags
    )


@router.post("", response_model=CVVersionResponse)
async def create_version(
    cv_file: UploadFile = File(..., description="CV file (PDF/DOCX)"),
    version_name: str = Form(..., min_length=1, max_length=100),
    auto_category: Optional[str] = Form(None),
    user_tags: Optional[str] = Form(None, description="Comma-separated tags"),
    source_job_link: Optional[str] = Form(None),
    source_job_title: Optional[str] = Form(None),
    parent_version_id: Optional[str] = Form(None),
    user: UserInfo = Depends(get_current_user)
) -> CVVersionResponse:
    """
    Create a new CV version by uploading a file.

    The file is stored in MinIO and metadata in Airtable.
    """
    # Validate file type
    allowed_types = [
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ]
    if cv_file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Allowed: PDF, DOCX"
        )

    # Parse tags
    tags = None
    if user_tags:
        tags = [t.strip() for t in user_tags.split(',') if t.strip()]

    try:
        # Save to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
            content = await cv_file.read()
            tmp.write(content)
            tmp_path = tmp.name

        manager = get_cv_version_manager()
        version = manager.create_version(
            user_email=user.email,
            file_path=tmp_path,
            version_name=version_name,
            auto_category=auto_category,
            user_tags=tags,
            parent_version_id=parent_version_id,
            source_job_link=source_job_link,
            source_job_title=source_job_title
        )

        # Cleanup temp file
        Path(tmp_path).unlink(missing_ok=True)

        return _version_to_response(version)

    except Exception as e:
        logger.error(f"Failed to create CV version: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create CV version: {str(e)}"
        )


@router.get("/{version_id}", response_model=CVVersionResponse)
async def get_version(
    version_id: str,
    include_url: bool = Query(False, description="Include download URL"),
    user: UserInfo = Depends(get_current_user)
) -> CVVersionResponse:
    """Get a specific CV version by ID."""
    manager = get_cv_version_manager()
    version = manager.get_version(version_id, user.email)

    if not version:
        raise HTTPException(status_code=404, detail="Version not found")

    # Get download URL if requested
    if include_url:
        version['download_url'] = manager.get_download_url(version_id, user.email)

    return _version_to_response(version, include_url=include_url)


@router.patch("/{version_id}", response_model=CVVersionResponse)
async def update_version(
    version_id: str,
    updates: CVVersionUpdate,
    user: UserInfo = Depends(get_current_user)
) -> CVVersionResponse:
    """Update CV version metadata (name, tags, category, archived status)."""
    manager = get_cv_version_manager()

    update_data = updates.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No updates provided")

    version = manager.update_version(version_id, user.email, update_data)

    if not version:
        raise HTTPException(status_code=404, detail="Version not found or update failed")

    return _version_to_response(version)


@router.delete("/{version_id}")
async def delete_version(
    version_id: str,
    permanent: bool = Query(False, description="Permanently delete (vs archive)"),
    user: UserInfo = Depends(get_current_user)
) -> dict:
    """
    Delete a CV version.

    By default, archives the version. Use permanent=true for hard delete.
    """
    manager = get_cv_version_manager()

    if permanent:
        success = manager.delete_version(version_id, user.email)
    else:
        success = manager.archive_version(version_id, user.email)

    if not success:
        raise HTTPException(status_code=404, detail="Version not found")

    return {
        "success": True,
        "action": "deleted" if permanent else "archived",
        "version_id": version_id
    }


@router.post("/{version_id}/restore")
async def restore_version(
    version_id: str,
    user: UserInfo = Depends(get_current_user)
) -> dict:
    """Restore an archived CV version."""
    manager = get_cv_version_manager()
    success = manager.restore_version(version_id, user.email)

    if not success:
        raise HTTPException(status_code=404, detail="Version not found")

    return {"success": True, "version_id": version_id}


@router.post("/{version_id}/fork", response_model=CVVersionResponse)
async def fork_version(
    version_id: str,
    request: CVVersionForkRequest,
    user: UserInfo = Depends(get_current_user)
) -> CVVersionResponse:
    """
    Fork an existing CV version to create a new one.

    Creates a copy with the same content but new ID and metadata.
    """
    manager = get_cv_version_manager()

    new_version = manager.fork_version(
        source_version_id=version_id,
        user_email=user.email,
        new_name=request.new_name
    )

    if not new_version:
        raise HTTPException(status_code=404, detail="Source version not found")

    return _version_to_response(new_version)


@router.get("/{version_id}/download")
async def get_download_url(
    version_id: str,
    expires_hours: int = Query(1, ge=1, le=24),
    user: UserInfo = Depends(get_current_user)
) -> dict:
    """Get a presigned download URL for a CV version."""
    manager = get_cv_version_manager()
    url = manager.get_download_url(version_id, user.email, expires_hours)

    if not url:
        raise HTTPException(status_code=404, detail="Version not found")

    return {
        "version_id": version_id,
        "download_url": url,
        "expires_hours": expires_hours
    }


@router.post("/{version_id}/use")
async def record_usage(
    version_id: str,
    user: UserInfo = Depends(get_current_user)
) -> dict:
    """Record that a CV version was used for a job application."""
    manager = get_cv_version_manager()
    success = manager.increment_usage(version_id, user.email)

    if not success:
        raise HTTPException(status_code=404, detail="Version not found")

    return {"success": True, "version_id": version_id}


@router.post("/{version_id}/response")
async def record_response(
    version_id: str,
    user: UserInfo = Depends(get_current_user)
) -> dict:
    """Record that a CV version got a response (callback/interview)."""
    manager = get_cv_version_manager()
    success = manager.increment_response(version_id, user.email)

    if not success:
        raise HTTPException(status_code=404, detail="Version not found")

    return {"success": True, "version_id": version_id}


@router.post("/match", response_model=CVVersionMatchResponse)
async def match_versions(
    request: CVVersionMatchRequest,
    user: UserInfo = Depends(get_current_user)
) -> CVVersionMatchResponse:
    """
    Find the best matching CV versions for a job description.

    Uses smart matching algorithm considering:
    - Role title similarity
    - Skills overlap
    - Historical performance (response rate)
    - Category alignment
    """
    from utils.cv_matcher import CVVersionMatcher

    manager = get_cv_version_manager()

    # Get all active versions
    versions = manager.list_versions(user.email, include_archived=False, limit=100)

    if not versions:
        return CVVersionMatchResponse(
            suggestions=[],
            job_analysis={"error": "No CV versions available"}
        )

    # Use the matcher to score versions
    matcher = CVVersionMatcher()
    results = matcher.match_versions(
        versions=versions,
        job_description=request.job_description,
        job_title=request.job_title,
        company_name=request.company_name,
        limit=request.limit
    )

    # Add download URLs to top matches
    suggestions = []
    for result in results['suggestions']:
        url = manager.get_download_url(result['version_id'], user.email)
        suggestions.append(CVVersionMatchScore(
            version_id=result['version_id'],
            version_name=result['version_name'],
            auto_category=result.get('auto_category'),
            overall_score=result['overall_score'],
            role_similarity=result['role_similarity'],
            skills_overlap=result['skills_overlap'],
            usage_count=result.get('usage_count', 0),
            response_rate=result.get('response_rate', 0),
            download_url=url,
            reasons=result.get('reasons', [])
        ))

    return CVVersionMatchResponse(
        suggestions=suggestions,
        job_analysis=results.get('job_analysis', {})
    )


@router.get("/analytics/summary", response_model=CVVersionAnalyticsResponse)
async def get_analytics(
    user: UserInfo = Depends(get_current_user)
) -> CVVersionAnalyticsResponse:
    """Get analytics summary for user's CV versions."""
    manager = get_cv_version_manager()
    analytics = manager.get_analytics(user.email)

    return CVVersionAnalyticsResponse(
        total_versions=analytics.get('total_versions', 0),
        active_versions=analytics.get('active_versions', 0),
        archived_versions=analytics.get('archived_versions', 0),
        total_usage=analytics.get('total_usage', 0),
        total_responses=analytics.get('total_responses', 0),
        overall_response_rate=analytics.get('overall_response_rate', 0),
        top_performing=analytics.get('top_performing', []),
        categories=analytics.get('categories', []),
        tags=analytics.get('tags', [])
    )


@router.post("/bulk", response_model=CVVersionBulkActionResponse)
async def bulk_action(
    request: CVVersionBulkActionRequest,
    user: UserInfo = Depends(get_current_user)
) -> CVVersionBulkActionResponse:
    """
    Perform bulk actions on multiple CV versions.

    Supported actions: archive, restore, delete
    """
    if request.action not in ['archive', 'restore', 'delete']:
        raise HTTPException(status_code=400, detail="Invalid action. Use: archive, restore, delete")

    manager = get_cv_version_manager()
    success_count = 0
    failed_ids = []

    for version_id in request.version_ids:
        try:
            if request.action == 'archive':
                result = manager.archive_version(version_id, user.email)
            elif request.action == 'restore':
                result = manager.restore_version(version_id, user.email)
            else:  # delete
                result = manager.delete_version(version_id, user.email)

            if result:
                success_count += 1
            else:
                failed_ids.append(version_id)
        except Exception:
            failed_ids.append(version_id)

    return CVVersionBulkActionResponse(
        success_count=success_count,
        failed_count=len(failed_ids),
        failed_ids=failed_ids
    )
