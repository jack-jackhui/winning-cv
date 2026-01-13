"""
CV Generation routes for WinningCV API.
Handles CV generation, upload, and history.
Uses MinIO for file storage.
"""
import os
import uuid
import logging
import tempfile
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import FileResponse

from api.schemas.auth import UserInfo
from api.schemas.cv import (
    CVGenerateRequest,
    CVGenerateResponse,
    CVUploadResponse,
    CVHistoryItem,
    CVHistoryResponse,
    CVAnalysisResponse,
    KeywordMatchSchema,
    TechnicalSkillsSchema,
    SoftSkillsSchema,
    SkillsCoverageSchema,
    ExperienceRelevanceSchema,
    ATSOptimizationSchema,
    GapAnalysisSchema,
    TalkingPointsSchema,
)
from api.middleware.auth_middleware import get_current_user, get_optional_user

# Import existing functionality
from cv.cv_generator import CVGenerator
from cv.cv_analyzer import CVAnalyzer, analyze_cv_fit
from utils.utils import extract_text_from_file, create_pdf, create_docx
from utils.minio_storage import get_minio_storage
from ui.helpers import extract_title_from_jd
from data_store.airtable_manager import AirtableManager
from config.settings import Config

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cv", tags=["CV Generation"])


# ──────────────────────────────────────────────────────────
# BACKGROUND TASK FOR CV ANALYSIS
# ──────────────────────────────────────────────────────────

def run_cv_analysis_background(
    history_id: str,
    cv_markdown: str,
    job_description: str
):
    """
    Background task to analyze CV-JD fit after CV generation.

    Args:
        history_id: Airtable record ID to update with analysis
        cv_markdown: Generated CV content
        job_description: Job description used for generation
    """
    import json

    logger.info(f"Starting background CV analysis for history_id={history_id}")

    try:
        cfg = Config()
        history_at = AirtableManager(
            cfg.AIRTABLE_API_KEY,
            cfg.AIRTABLE_BASE_ID,
            cfg.AIRTABLE_TABLE_ID_HISTORY
        )

        # Run the analysis
        analyzer = CVAnalyzer()
        analysis = analyzer.analyze(cv_markdown, job_description)

        # Store as JSON in Airtable
        analysis_json = json.dumps(analysis.to_dict())
        history_at.update_history_analysis(history_id, analysis_json, status="ready")

        logger.info(f"CV analysis complete for history_id={history_id}, score={analysis.overall_score}")

    except Exception as e:
        logger.error(f"CV analysis failed for history_id={history_id}: {e}")

        # Update status to failed
        try:
            cfg = Config()
            history_at = AirtableManager(
                cfg.AIRTABLE_API_KEY,
                cfg.AIRTABLE_BASE_ID,
                cfg.AIRTABLE_TABLE_ID_HISTORY
            )
            history_at.update_history_analysis(history_id, json.dumps({"error": str(e)}), status="failed")
        except Exception as update_error:
            logger.error(f"Failed to update analysis status: {update_error}")


class FileWrapper:
    """Wrapper to make UploadFile compatible with extract_text_from_file"""
    def __init__(self, upload_file: UploadFile, content: bytes):
        self.name = upload_file.filename
        self.type = upload_file.content_type
        self._content = content

    def getvalue(self) -> bytes:
        return self._content


@router.post("/generate", response_model=CVGenerateResponse)
async def generate_cv(
    background_tasks: BackgroundTasks,
    job_description: str = Form(..., min_length=50),
    cv_file: UploadFile = File(...),
    instructions: Optional[str] = Form(None),
    user: UserInfo = Depends(get_current_user)
) -> CVGenerateResponse:
    """
    Generate a tailored CV based on job description and user's CV.
    Also triggers background analysis of CV-JD fit.

    Args:
        background_tasks: FastAPI background tasks handler
        job_description: The job description to tailor the CV for
        cv_file: The user's current CV (PDF/DOCX/TXT)
        instructions: Optional special instructions for CV generation
        user: Authenticated user

    Returns:
        Generated CV in markdown format, PDF URL, and history_id for analysis lookup
    """
    # Validate file type
    allowed_types = [
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "text/plain"
    ]
    if cv_file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: PDF, DOCX, TXT"
        )

    try:
        # Read file content
        file_content = await cv_file.read()

        # Extract text from CV
        file_wrapper = FileWrapper(cv_file, file_content)
        orig_cv = extract_text_from_file(file_wrapper)

        if len(orig_cv.strip()) < 30:
            raise HTTPException(
                status_code=400,
                detail="Could not parse CV content. Try a different format."
            )

        # Generate tailored CV
        generator = CVGenerator()
        raw_md = generator.generate_cv(orig_cv, job_description, instructions or "")

        # Generate file names
        job_title = extract_title_from_jd(job_description)
        safe_title = re.sub(r'[^\w]+', '_', job_title)[:30].strip('_')
        today = datetime.now().strftime("%Y-%m-%d")
        unique_id = uuid.uuid4().hex[:8]

        # Create temp directory for files
        output_dir = Path("customised_cv")
        output_dir.mkdir(exist_ok=True)

        base_filename = f"{today}_{safe_title}_{unique_id}_cv"
        pdf_filename = f"{base_filename}.pdf"
        docx_filename = f"{base_filename}.docx"
        pdf_path = output_dir / pdf_filename
        docx_path = output_dir / docx_filename

        # Generate PDF
        pdf_result = create_pdf(raw_md, str(pdf_path))
        if not pdf_result:
            raise HTTPException(
                status_code=500,
                detail="Failed to generate PDF"
            )

        # Generate DOCX
        docx_result = create_docx(raw_md, str(docx_path))
        if not docx_result:
            logger.warning("Failed to generate DOCX, continuing with PDF only")

        # Upload to MinIO storage
        minio = get_minio_storage()
        cv_pdf_url = ""
        cv_docx_url = ""

        # Upload PDF to MinIO
        try:
            pdf_object_path = minio.upload_cv(
                file_path=str(pdf_path),
                user_id=user.email,
                filename=pdf_filename
            )
            cv_pdf_url = minio.get_download_url_by_path(pdf_object_path, expires_hours=24)
            logger.info(f"Uploaded PDF to MinIO: {pdf_object_path}")
        except Exception as e:
            logger.error(f"Failed to upload PDF to MinIO: {e}")
            # Continue without URL - file is still available locally

        # Upload DOCX to MinIO
        if docx_result:
            try:
                docx_object_path = minio.upload_cv(
                    file_path=str(docx_path),
                    user_id=user.email,
                    filename=docx_filename,
                    content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
                cv_docx_url = minio.get_download_url_by_path(docx_object_path, expires_hours=24)
                logger.info(f"Uploaded DOCX to MinIO: {docx_object_path}")
            except Exception as e:
                logger.error(f"Failed to upload DOCX to MinIO: {e}")

        # Save to history and get record ID for analysis
        history_id = None
        try:
            cfg = Config()
            history_at = AirtableManager(
                cfg.AIRTABLE_API_KEY,
                cfg.AIRTABLE_BASE_ID,
                cfg.AIRTABLE_TABLE_ID_HISTORY
            )
            history_data = {
                "user_email": user.email,
                "job_title": job_title,
                "job_description": job_description,
                "instructions": instructions or "",
                "cv_markdown": raw_md,
                "cv_pdf_url": cv_pdf_url,
                "analysis_status": "pending",  # Mark as pending analysis
            }
            history_id = history_at.create_history_record(history_data)

            # Trigger background analysis if history was saved
            if history_id:
                background_tasks.add_task(
                    run_cv_analysis_background,
                    history_id=history_id,
                    cv_markdown=raw_md,
                    job_description=job_description
                )
                logger.info(f"Queued background analysis for history_id={history_id}")

        except Exception as e:
            logger.error(f"Failed to save history: {e}")
            # Continue - generation was successful

        return CVGenerateResponse(
            cv_markdown=raw_md,
            cv_pdf_url=cv_pdf_url,
            cv_docx_url=cv_docx_url if cv_docx_url else None,
            job_title=job_title,
            history_id=history_id  # Return for frontend to poll analysis status
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"CV generation failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"CV generation failed: {str(e)}"
        )


@router.post("/upload", response_model=CVUploadResponse)
async def upload_cv(
    cv_file: UploadFile = File(...),
    user: UserInfo = Depends(get_current_user)
) -> CVUploadResponse:
    """
    Upload a base CV for job search configuration.

    Args:
        cv_file: The CV file to upload (PDF/DOCX)
        user: Authenticated user

    Returns:
        Path and URL of uploaded CV
    """
    allowed_types = [
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ]
    if cv_file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Allowed: PDF, DOCX"
        )

    try:
        # Create user-specific directory
        cv_dir = Path(f"user_cv/{user.email}")
        cv_dir.mkdir(parents=True, exist_ok=True)

        # Generate unique filename
        suffix = Path(cv_file.filename).suffix
        unique_filename = f"base_cv_{uuid.uuid4().hex[:8]}{suffix}"
        cv_path = cv_dir / unique_filename

        # Save file locally
        content = await cv_file.read()
        with open(cv_path, "wb") as f:
            f.write(content)

        # Upload to MinIO for web access
        cv_url = ""
        try:
            minio = get_minio_storage()
            # Determine content type from suffix
            content_type = "application/pdf"
            if suffix.lower() == ".docx":
                content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

            object_path = minio.upload_cv(
                file_path=str(cv_path),
                user_id=user.email,
                filename=unique_filename,
                content_type=content_type
            )
            cv_url = minio.get_download_url_by_path(object_path, expires_hours=24)
            logger.info(f"Uploaded base CV to MinIO: {object_path}")
        except Exception as e:
            logger.warning(f"Failed to upload CV to MinIO: {e}")

        return CVUploadResponse(
            path=str(cv_path),
            url=cv_url or None,
            filename=unique_filename
        )

    except Exception as e:
        logger.error(f"CV upload failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload CV: {str(e)}"
        )


@router.get("/history", response_model=CVHistoryResponse)
async def get_cv_history(
    user: UserInfo = Depends(get_current_user),
    limit: int = 50
) -> CVHistoryResponse:
    """
    Get the user's CV generation history.

    Args:
        user: Authenticated user
        limit: Maximum number of records to return

    Returns:
        List of CV history items
    """
    try:
        cfg = Config()
        history_at = AirtableManager(
            cfg.AIRTABLE_API_KEY,
            cfg.AIRTABLE_BASE_ID,
            cfg.AIRTABLE_TABLE_ID_HISTORY
        )

        records = history_at.get_history_by_user(user.email)

        items = []
        for r in records[:limit]:
            fields = r.get("fields", {})
            items.append(CVHistoryItem(
                id=r.get("id", ""),
                job_title=fields.get("job_title", "Untitled"),
                created_at=fields.get("created_at", datetime.now().isoformat()),
                cv_pdf_url=fields.get("cv_pdf_url", ""),
                job_description=fields.get("job_description"),
                instructions=fields.get("Instructions")
            ))

        return CVHistoryResponse(
            items=items,
            total=len(items)
        )

    except Exception as e:
        logger.error(f"Failed to fetch history: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch history: {str(e)}"
        )


@router.get("/download/{filename}")
async def download_cv(
    filename: str,
    user: UserInfo = Depends(get_current_user)
) -> FileResponse:
    """
    Download a generated CV PDF.

    Args:
        filename: Name of the PDF file
        user: Authenticated user

    Returns:
        PDF file response
    """
    # Sanitize filename to prevent path traversal
    safe_filename = Path(filename).name

    # Check customised_cv directory
    pdf_path = Path("customised_cv") / safe_filename

    if not pdf_path.exists():
        raise HTTPException(
            status_code=404,
            detail="File not found"
        )

    return FileResponse(
        path=str(pdf_path),
        filename=safe_filename,
        media_type="application/pdf"
    )


# ──────────────────────────────────────────────────────────
# CV-JD FIT ANALYSIS ENDPOINT
# ──────────────────────────────────────────────────────────

@router.get("/analysis/{history_id}", response_model=CVAnalysisResponse)
async def get_cv_analysis(
    history_id: str,
    user: UserInfo = Depends(get_current_user)
) -> CVAnalysisResponse:
    """
    Get the CV-JD fit analysis for a generated CV.

    Args:
        history_id: Airtable record ID from CV generation
        user: Authenticated user

    Returns:
        Analysis status and results if ready
    """
    import json

    try:
        cfg = Config()
        history_at = AirtableManager(
            cfg.AIRTABLE_API_KEY,
            cfg.AIRTABLE_BASE_ID,
            cfg.AIRTABLE_TABLE_ID_HISTORY
        )

        # Get the history record
        record = history_at.get_history_record(history_id)

        if not record:
            raise HTTPException(status_code=404, detail="History record not found")

        fields = record.get("fields", {})

        # Verify ownership
        if fields.get("user_email") != user.email:
            raise HTTPException(status_code=403, detail="Access denied")

        # Check analysis status
        status = fields.get("analysis_status", "pending")
        analysis_json = fields.get("cv_analysis")

        if status == "pending" or not analysis_json:
            return CVAnalysisResponse(status="pending")

        if status == "failed":
            error_data = json.loads(analysis_json) if analysis_json else {}
            return CVAnalysisResponse(
                status="failed",
                error=error_data.get("error", "Analysis failed")
            )

        # Parse the analysis JSON
        try:
            analysis_data = json.loads(analysis_json)
        except json.JSONDecodeError:
            return CVAnalysisResponse(status="failed", error="Invalid analysis data")

        # Build response with nested schemas
        return CVAnalysisResponse(
            status="ready",
            overall_score=analysis_data.get("overall_score"),
            summary=analysis_data.get("summary"),
            keyword_match=KeywordMatchSchema(
                score=analysis_data["keyword_match"]["score"],
                matched=analysis_data["keyword_match"]["matched"],
                missing=analysis_data["keyword_match"]["missing"],
                density_assessment=analysis_data["keyword_match"]["density_assessment"]
            ) if analysis_data.get("keyword_match") else None,
            skills_coverage=SkillsCoverageSchema(
                score=analysis_data["skills_coverage"]["score"],
                technical_skills=TechnicalSkillsSchema(
                    matched=analysis_data["skills_coverage"]["technical_skills"]["matched"],
                    partial=analysis_data["skills_coverage"]["technical_skills"]["partial"],
                    missing=analysis_data["skills_coverage"]["technical_skills"]["missing"]
                ),
                soft_skills=SoftSkillsSchema(
                    matched=analysis_data["skills_coverage"]["soft_skills"]["matched"],
                    demonstrated=analysis_data["skills_coverage"]["soft_skills"]["demonstrated"]
                )
            ) if analysis_data.get("skills_coverage") else None,
            experience_relevance=ExperienceRelevanceSchema(
                score=analysis_data["experience_relevance"]["score"],
                aligned_roles=analysis_data["experience_relevance"]["aligned_roles"],
                relevant_achievements=analysis_data["experience_relevance"]["relevant_achievements"],
                years_alignment=analysis_data["experience_relevance"]["years_alignment"]
            ) if analysis_data.get("experience_relevance") else None,
            ats_optimization=ATSOptimizationSchema(
                score=analysis_data["ats_optimization"]["score"],
                format_check=analysis_data["ats_optimization"]["format_check"],
                keyword_density=analysis_data["ats_optimization"]["keyword_density"],
                section_structure=analysis_data["ats_optimization"]["section_structure"],
                recommendations=analysis_data["ats_optimization"]["recommendations"]
            ) if analysis_data.get("ats_optimization") else None,
            gap_analysis=GapAnalysisSchema(
                critical_gaps=analysis_data["gap_analysis"]["critical_gaps"],
                minor_gaps=analysis_data["gap_analysis"]["minor_gaps"],
                mitigation_suggestions=analysis_data["gap_analysis"]["mitigation_suggestions"]
            ) if analysis_data.get("gap_analysis") else None,
            talking_points=TalkingPointsSchema(
                strengths_to_highlight=analysis_data["talking_points"]["strengths_to_highlight"],
                questions_to_prepare=analysis_data["talking_points"]["questions_to_prepare"],
                stories_to_ready=analysis_data["talking_points"]["stories_to_ready"]
            ) if analysis_data.get("talking_points") else None
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get analysis: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get analysis: {str(e)}"
        )
