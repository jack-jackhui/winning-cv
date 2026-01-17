# utils/cv_loader.py
from utils.utils import extract_text_from_file
import os
import io
import logging
import tempfile

logger = logging.getLogger(__name__)


def _download_from_minio_by_path(storage_path: str) -> str:
    """
    Download CV from MinIO using a direct storage path.

    Args:
        storage_path: Full MinIO object path (e.g., "user@example.com/versions/cv.docx")

    Returns:
        Local temp file path if successful, empty string otherwise
    """
    try:
        from utils.minio_storage import get_minio_storage

        storage = get_minio_storage()
        filename = os.path.basename(storage_path)

        # Always use temp directory for direct MinIO downloads
        temp_dir = tempfile.mkdtemp(prefix="cv_download_")
        download_path = os.path.join(temp_dir, filename)

        logger.info(f"Downloading CV from MinIO path: {storage_path}")

        if storage.download_cv_by_path(storage_path, download_path):
            logger.info(f"Successfully downloaded CV from MinIO to {download_path}")
            return download_path

        logger.warning(f"CV not found in MinIO at path: {storage_path}")
        return ""

    except Exception as e:
        logger.error(f"MinIO direct download failed: {str(e)}")
        return ""


def _try_download_from_minio(file_path: str) -> str:
    """
    Attempt to download CV from MinIO storage when local file is missing.

    Parses the expected path format: user_cv/{user_email}/{filename}
    and downloads from MinIO to a temp directory (to avoid permission issues in Docker).

    Args:
        file_path: Expected local path (e.g., "user_cv/user@example.com/base_cv_xxx.docx")

    Returns:
        The local path if download successful, empty string otherwise
    """
    try:
        from utils.minio_storage import get_minio_storage

        # Parse path: user_cv/{user_email}/{filename}
        parts = file_path.replace("\\", "/").split("/")
        if len(parts) < 3 or parts[0] != "user_cv":
            logger.warning(f"Cannot parse CV path for MinIO lookup: {file_path}")
            return ""

        user_email = parts[1]
        filename = parts[-1]

        logger.info(f"Attempting MinIO download: user={user_email}, file={filename}")

        storage = get_minio_storage()

        # Use temp directory to avoid permission issues in Docker
        # Try original path first, fallback to temp directory
        download_path = file_path
        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
        except (PermissionError, OSError) as e:
            # Fallback to temp directory if we can't create the original path
            logger.warning(f"Cannot create directory for {file_path}: {e}. Using temp directory.")
            temp_dir = tempfile.mkdtemp(prefix="cv_download_")
            download_path = os.path.join(temp_dir, filename)

        # Try to download from MinIO
        if storage.download_cv_to_local(user_email, filename, download_path):
            logger.info(f"Successfully downloaded CV from MinIO to {download_path}")
            return download_path

        logger.warning(f"CV not found in MinIO for user={user_email}, file={filename}")
        return ""

    except Exception as e:
        logger.error(f"MinIO download failed: {str(e)}")
        return ""

def load_cv_content(file_path="user_cv/CV_Jack_HUI_08042025_EL.docx"):
    """
    Load CV content using unified text extraction.

    Supports multiple path formats:
    - minio://{storage_path}: Direct MinIO storage path (from CV library selection)
    - user_cv/{email}/{filename}: Local path with MinIO fallback

    For Docker deployments where local files may not persist, automatically
    falls back to MinIO storage.
    """
    try:
        # Check for direct MinIO path (from CV library selection)
        if file_path.startswith("minio://"):
            storage_path = file_path[8:]  # Remove "minio://" prefix
            logger.info(f"Loading CV from MinIO storage path: {storage_path}")
            file_path = _download_from_minio_by_path(storage_path)
            if not file_path:
                logger.error("CV not found in MinIO storage")
                return ""
        else:
            logger.info(f"Loading CV from: {os.path.abspath(file_path)}")

            # Try local filesystem first
            if not os.path.exists(file_path):
                logger.warning(f"Local file not found: {os.path.abspath(file_path)}")

                # Try to download from MinIO
                file_path = _try_download_from_minio(file_path)
                if not file_path:
                    logger.error("CV not found locally or in MinIO storage")
                    return ""

        # Create file-like object for utils processing
        with open(file_path, 'rb') as f:
            file_bytes = f.read()

        # Create mock FileStorage-like object
        class FileWrapper:
            def __init__(self, content, content_type):
                self.file = io.BytesIO(content)
                self.type = content_type

            def getvalue(self):
                return self.file.getvalue()

        # Detect MIME type from extension
        if file_path.lower().endswith('.docx'):
            file_obj = FileWrapper(file_bytes,
                                   'application/vnd.openxmlformats-officedocument.wordprocessingml.document')
        elif file_path.lower().endswith('.pdf'):
            file_obj = FileWrapper(file_bytes, 'application/pdf')

        elif file_path.lower().endswith('.txt') or file_path.lower().endswith('.md'):
            file_obj = FileWrapper(file_bytes, 'text/plain')

        else:
            logger.error("Unsupported file format")
            return ""

        return extract_text_from_file(file_obj)

    except Exception as e:
        logger.error(f"CV load failed: {str(e)}")
        return ""
