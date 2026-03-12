"""
CV Knowledge Base API Routes.

Endpoints for indexing, searching, and generating CVs using the knowledge base.
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from api.middleware.auth_middleware import get_current_user
from api.schemas.auth import UserInfo
from cv.cv_knowledge_base import get_knowledge_base
from data_store.cv_version_manager import get_cv_version_manager
from utils.cv_loader import load_cv_content

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/knowledge-base", tags=["Knowledge Base"])


# =============================================================================
# Request/Response Schemas
# =============================================================================


class IndexCVRequest(BaseModel):
    """Request to index a CV version."""
    cv_version_id: str = Field(..., description="Airtable CV version record ID")


class IndexCVResponse(BaseModel):
    """Response from indexing a CV."""
    status: str
    cv_version_id: str
    sections_count: Optional[int] = None
    bullets_count: Optional[int] = None
    reason: Optional[str] = None


class IndexedVersionResponse(BaseModel):
    """Summary of an indexed CV version."""
    cv_version_id: str
    version_name: Optional[str]
    indexed_at: Optional[str]
    section_count: int
    bullet_count: int


class SearchRequest(BaseModel):
    """Request to search CV content."""
    query: str = Field(..., min_length=2, description="Search query")
    section_types: Optional[list[str]] = Field(
        None, description="Filter by section types (summary, experience, skills, etc.)"
    )
    limit: int = Field(20, ge=1, le=100, description="Maximum results")


class SearchResultItem(BaseModel):
    """A single search result."""
    cv_version_id: str
    version_name: Optional[str]
    section_type: str
    section_title: Optional[str]
    content: str
    relevance_score: float


class SearchResponse(BaseModel):
    """Response from searching CV content."""
    results: list[SearchResultItem]
    total: int


class GenerateSmartCVRequest(BaseModel):
    """Request to generate a CV using the knowledge base."""
    job_description: str = Field(..., min_length=50, description="Job description")
    instructions: Optional[str] = Field(None, description="Additional instructions")
    base_cv_version_id: Optional[str] = Field(
        None, description="CV version ID to use as template structure"
    )


class GenerateSmartCVResponse(BaseModel):
    """Response from smart CV generation."""
    cv_content: str
    sources_used: int
    generation_method: str = "knowledge_base"


# =============================================================================
# Endpoints
# =============================================================================


@router.post("/index", response_model=IndexCVResponse)
async def index_cv_version(
    request: IndexCVRequest,
    user: UserInfo = Depends(get_current_user)
) -> IndexCVResponse:
    """
    Index a CV version into the knowledge base.

    Extracts sections and content from the CV and stores them in PostgreSQL
    for full-text search and intelligent CV generation.
    """
    # Get the CV version from Airtable
    manager = get_cv_version_manager()
    version = manager.get_version(request.cv_version_id, user.email)

    if not version:
        raise HTTPException(status_code=404, detail="CV version not found")

    # Get the CV content
    storage_path = version.get('storage_path')
    if not storage_path:
        raise HTTPException(status_code=400, detail="CV version has no file")

    try:
        # Download and extract text from the CV
        import tempfile
        from pathlib import Path

        from utils.minio_storage import get_minio_storage

        minio = get_minio_storage()

        # Download to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
            minio.client.fget_object(minio.bucket, storage_path, tmp.name)
            tmp_path = tmp.name

        # Extract text content
        cv_content = load_cv_content(tmp_path)

        # Cleanup temp file
        Path(tmp_path).unlink(missing_ok=True)

        if not cv_content or not cv_content.strip():
            raise HTTPException(
                status_code=400,
                detail="Could not extract text content from CV"
            )

        # Index the CV
        kb = get_knowledge_base()
        result = await kb.index_cv(
            cv_version_id=request.cv_version_id,
            user_email=user.email,
            cv_content=cv_content,
            version_name=version.get('version_name'),
        )

        return IndexCVResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to index CV {request.cv_version_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to index CV: {str(e)}"
        )


@router.get("/versions", response_model=list[IndexedVersionResponse])
async def list_indexed_versions(
    user: UserInfo = Depends(get_current_user)
) -> list[IndexedVersionResponse]:
    """
    List all indexed CV versions for the current user.

    Returns summary information about each indexed version including
    the number of sections and experience bullets extracted.
    """
    kb = get_knowledge_base()
    versions = await kb.get_indexed_versions(user.email)

    return [IndexedVersionResponse(**v) for v in versions]


@router.delete("/versions/{cv_version_id}")
async def delete_cv_index(
    cv_version_id: str,
    user: UserInfo = Depends(get_current_user)
) -> dict:
    """
    Delete indexed content for a CV version.

    Removes all extracted content from the knowledge base.
    This does not delete the CV file or Airtable record.
    """
    kb = get_knowledge_base()
    deleted = await kb.delete_cv_index(cv_version_id, user.email)

    if not deleted:
        raise HTTPException(status_code=404, detail="Indexed version not found")

    return {"success": True, "cv_version_id": cv_version_id}


@router.post("/search", response_model=SearchResponse)
async def search_content(
    request: SearchRequest,
    user: UserInfo = Depends(get_current_user)
) -> SearchResponse:
    """
    Full-text search across all indexed CV content.

    Searches summaries, experience, skills, and other sections
    using PostgreSQL's powerful full-text search capabilities.
    """
    kb = get_knowledge_base()

    results = await kb.search_sections(
        user_email=user.email,
        query=request.query,
        section_types=request.section_types,
        limit=request.limit,
    )

    return SearchResponse(
        results=[SearchResultItem(**r) for r in results],
        total=len(results)
    )


@router.get("/unified-experience")
async def get_unified_experience(
    skills: Optional[str] = Query(None, description="Comma-separated skills to filter"),
    limit: int = Query(100, ge=1, le=500),
    user: UserInfo = Depends(get_current_user)
) -> dict:
    """
    Get unified experience from all CV versions.

    Merges and deduplicates experience bullets, summaries, and skills
    from all indexed CV versions. Useful for understanding the full
    scope of experience available for CV generation.
    """
    kb = get_knowledge_base()

    skills_filter = None
    if skills:
        skills_filter = [s.strip().lower() for s in skills.split(',') if s.strip()]

    unified = await kb.build_unified_experience(
        user_email=user.email,
        skills_filter=skills_filter,
        limit=limit,
    )

    return unified


@router.post("/cv/generate-smart", response_model=GenerateSmartCVResponse)
async def generate_smart_cv(
    request: GenerateSmartCVRequest,
    user: UserInfo = Depends(get_current_user)
) -> GenerateSmartCVResponse:
    """
    Generate an optimal CV using the knowledge base.

    This endpoint uses ALL indexed CV versions to create the best possible
    CV for the given job description. It intelligently selects the most
    relevant content from your CV history.

    Optionally provide a base_cv_version_id to use as the template structure.
    """
    from cv.cv_generator import generate_cv_with_knowledge

    # Get base CV content if specified
    base_cv_content = None
    if request.base_cv_version_id:
        manager = get_cv_version_manager()
        version = manager.get_version(request.base_cv_version_id, user.email)

        if not version:
            raise HTTPException(
                status_code=404,
                detail="Base CV version not found"
            )

        storage_path = version.get('storage_path')
        if storage_path:
            try:
                import tempfile
                from pathlib import Path

                from utils.minio_storage import get_minio_storage

                minio = get_minio_storage()

                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
                    minio.client.fget_object(minio.bucket, storage_path, tmp.name)
                    base_cv_content = load_cv_content(tmp.name)
                    Path(tmp.name).unlink(missing_ok=True)
            except Exception as e:
                logger.warning(f"Could not load base CV: {e}")

    try:
        # Check if user has indexed content
        kb = get_knowledge_base()
        versions = await kb.get_indexed_versions(user.email)

        if not versions and not base_cv_content:
            raise HTTPException(
                status_code=400,
                detail="No indexed CV versions found. Please index at least one CV first."
            )

        # Generate the CV
        cv_content = await generate_cv_with_knowledge(
            user_email=user.email,
            job_desc=request.job_description,
            instructions=request.instructions or "",
            base_cv_content=base_cv_content,
        )

        return GenerateSmartCVResponse(
            cv_content=cv_content,
            sources_used=len(versions),
            generation_method="knowledge_base"
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Smart CV generation failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"CV generation failed: {str(e)}"
        )


@router.post("/index-all")
async def index_all_versions(
    user: UserInfo = Depends(get_current_user)
) -> dict:
    """
    Index all CV versions for the current user.

    Iterates through all CV versions in Airtable and indexes them
    into the knowledge base. Skips versions already indexed with
    the same content.
    """
    manager = get_cv_version_manager()
    kb = get_knowledge_base()

    # Get all versions
    versions = manager.list_versions(user.email, include_archived=False, limit=100)

    indexed = 0
    skipped = 0
    failed = 0
    errors = []

    for version in versions:
        try:
            storage_path = version.get('storage_path')
            if not storage_path:
                skipped += 1
                continue

            # Download and extract text
            import tempfile
            from pathlib import Path

            from utils.minio_storage import get_minio_storage

            minio = get_minio_storage()

            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
                minio.client.fget_object(minio.bucket, storage_path, tmp.name)
                cv_content = load_cv_content(tmp.name)
                Path(tmp.name).unlink(missing_ok=True)

            if not cv_content or not cv_content.strip():
                skipped += 1
                continue

            result = await kb.index_cv(
                cv_version_id=version.get('version_id') or version.get('id'),
                user_email=user.email,
                cv_content=cv_content,
                version_name=version.get('version_name'),
            )

            if result['status'] == 'indexed':
                indexed += 1
            else:
                skipped += 1

        except Exception as e:
            failed += 1
            errors.append({
                'version_id': version.get('version_id') or version.get('id'),
                'error': str(e)
            })

    return {
        'total_versions': len(versions),
        'indexed': indexed,
        'skipped': skipped,
        'failed': failed,
        'errors': errors[:5] if errors else []  # Return first 5 errors
    }
