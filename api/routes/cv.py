"""
CV Generation routes for WinningCV API.
Handles CV generation, upload, and history.
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
)
from api.middleware.auth_middleware import get_current_user, get_optional_user

# Import existing functionality
from cv.cv_generator import CVGenerator
from utils.utils import extract_text_from_file, create_pdf
from ui.helpers import upload_pdf_to_wordpress, extract_title_from_jd
from data_store.airtable_manager import AirtableManager
from config.settings import Config

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cv", tags=["CV Generation"])


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
    job_description: str = Form(..., min_length=50),
    cv_file: UploadFile = File(...),
    instructions: Optional[str] = Form(None),
    user: UserInfo = Depends(get_current_user)
) -> CVGenerateResponse:
    """
    Generate a tailored CV based on job description and user's CV.

    Args:
        job_description: The job description to tailor the CV for
        cv_file: The user's current CV (PDF/DOCX/TXT)
        instructions: Optional special instructions for CV generation
        user: Authenticated user

    Returns:
        Generated CV in markdown format and PDF URL
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

        # Create PDF
        job_title = extract_title_from_jd(job_description)
        safe_title = re.sub(r'[^\w]+', '_', job_title)[:30].strip('_')
        today = datetime.now().strftime("%Y-%m-%d")
        unique_id = uuid.uuid4().hex[:8]

        # Create temp directory for PDF
        output_dir = Path("customised_cv")
        output_dir.mkdir(exist_ok=True)

        pdf_filename = f"{today}_{safe_title}_{unique_id}_cv.pdf"
        pdf_path = output_dir / pdf_filename

        pdf_result = create_pdf(raw_md, str(pdf_path))

        if not pdf_result:
            raise HTTPException(
                status_code=500,
                detail="Failed to generate PDF"
            )

        # Upload to WordPress
        cv_pdf_url = ""
        try:
            cv_pdf_url = upload_pdf_to_wordpress(
                file_path=str(pdf_path),
                filename=pdf_filename,
                wp_site=Config.WORDPRESS_SITE,
                wp_user=Config.WORDPRESS_USERNAME,
                wp_app_password=Config.WORDPRESS_APP_PASSWORD
            )
        except Exception as e:
            logger.error(f"Failed to upload PDF to WordPress: {e}")
            # Continue without URL - file is still available locally

        # Save to history
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
            }
            history_at.create_history_record(history_data)
        except Exception as e:
            logger.error(f"Failed to save history: {e}")
            # Continue - generation was successful

        return CVGenerateResponse(
            cv_markdown=raw_md,
            cv_pdf_url=cv_pdf_url,
            job_title=job_title
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

        # Save file
        content = await cv_file.read()
        with open(cv_path, "wb") as f:
            f.write(content)

        # Upload to WordPress for web access
        cv_url = ""
        try:
            cv_url = upload_pdf_to_wordpress(
                file_path=str(cv_path),
                filename=unique_filename,
                wp_site=Config.WORDPRESS_SITE,
                wp_user=Config.WORDPRESS_USERNAME,
                wp_app_password=Config.WORDPRESS_APP_PASSWORD
            )
        except Exception as e:
            logger.warning(f"Failed to upload CV to WordPress: {e}")

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
