"""
MinIO Storage Client for WinningCV

Provides secure CV storage with:
- Private bucket access (no public URLs)
- Time-limited presigned URLs for downloads
- User-isolated storage paths
- Automatic bucket initialization
"""

import os
import logging
from datetime import timedelta
from typing import Optional
from urllib.parse import urlparse

from minio import Minio
from minio.error import S3Error

logger = logging.getLogger(__name__)


class MinIOStorage:
    """
    MinIO storage client for CV file management.

    Usage:
        storage = MinIOStorage()

        # Upload a CV
        url = storage.upload_cv(
            file_path="/path/to/cv.pdf",
            user_id="user123",
            filename="backend_engineer_cv.pdf"
        )

        # Get download URL (time-limited)
        download_url = storage.get_download_url(
            user_id="user123",
            filename="backend_engineer_cv.pdf",
            expires_hours=1
        )

        # List user's CVs
        cvs = storage.list_user_cvs("user123")

        # Delete a CV
        storage.delete_cv("user123", "old_cv.pdf")
    """

    DEFAULT_BUCKET = "winningcv-cvs"
    DEFAULT_URL_EXPIRY_HOURS = 1

    def __init__(
        self,
        endpoint: Optional[str] = None,
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        bucket: Optional[str] = None,
        secure: bool = False
    ):
        """
        Initialize MinIO client.

        Args:
            endpoint: MinIO server endpoint (default: from MINIO_ENDPOINT env)
            access_key: Access key (default: from MINIO_ROOT_USER env)
            secret_key: Secret key (default: from MINIO_ROOT_PASSWORD env)
            bucket: Bucket name (default: winningcv-cvs)
            secure: Use HTTPS (default: False for Docker internal network)
        """
        self.endpoint = endpoint or os.getenv("MINIO_ENDPOINT", "minio:9000")
        self.access_key = access_key or os.getenv("MINIO_ROOT_USER", "minioadmin")
        self.secret_key = secret_key or os.getenv("MINIO_ROOT_PASSWORD", "minioadmin123")
        self.bucket = bucket or os.getenv("MINIO_BUCKET", self.DEFAULT_BUCKET)
        self.secure = secure or os.getenv("MINIO_SECURE", "false").lower() == "true"

        # External endpoint for generating presigned URLs (accessible from browser)
        # Format: "https://domain.com/storage" (with /storage prefix for nginx proxy)
        self.external_endpoint = os.getenv("MINIO_EXTERNAL_ENDPOINT", "")

        self.client = Minio(
            self.endpoint,
            access_key=self.access_key,
            secret_key=self.secret_key,
            secure=self.secure
        )

        # Ensure bucket exists
        self._ensure_bucket()

    def _ensure_bucket(self) -> None:
        """Create bucket if it doesn't exist."""
        try:
            if not self.client.bucket_exists(self.bucket):
                self.client.make_bucket(self.bucket)
                logger.info(f"Created MinIO bucket: {self.bucket}")
        except S3Error as e:
            logger.error(f"Failed to create/check bucket: {e}")
            raise

    def _transform_url_for_external(self, internal_url: str) -> str:
        """
        Transform internal MinIO URL to external URL accessible from browser.

        Internal URL format: http://minio:9000/bucket/path?signature...
        External URL format: https://domain.com/storage/bucket/path?signature...

        The nginx proxy at /storage/ rewrites to MinIO root.
        """
        if not self.external_endpoint:
            return internal_url

        parsed = urlparse(internal_url)
        # parsed.path = /bucket/object/path, parsed.query = signature params
        external_url = f"{self.external_endpoint}{parsed.path}"
        if parsed.query:
            external_url += f"?{parsed.query}"

        logger.debug(f"Transformed URL: {internal_url[:50]}... -> {external_url[:50]}...")
        return external_url

    def _get_object_path(self, user_id: str, filename: str, version_id: Optional[str] = None) -> str:
        """
        Generate object path with user isolation.

        Path format: {user_id}/versions/{filename} or {user_id}/versions/{version_id}/{filename}
        """
        if version_id:
            return f"{user_id}/versions/{version_id}/{filename}"
        return f"{user_id}/versions/{filename}"

    def upload_cv(
        self,
        file_path: str,
        user_id: str,
        filename: str,
        version_id: Optional[str] = None,
        content_type: str = "application/pdf"
    ) -> str:
        """
        Upload a CV file to MinIO.

        Args:
            file_path: Local path to the file
            user_id: User identifier for path isolation
            filename: Filename to store as
            version_id: Optional version identifier
            content_type: MIME type (default: application/pdf)

        Returns:
            Object path (not a public URL - use get_download_url for access)
        """
        object_path = self._get_object_path(user_id, filename, version_id)

        try:
            # Get file size
            file_size = os.path.getsize(file_path)

            with open(file_path, "rb") as file_data:
                self.client.put_object(
                    self.bucket,
                    object_path,
                    file_data,
                    length=file_size,
                    content_type=content_type
                )

            logger.info(f"Uploaded CV to MinIO: {object_path}")
            return object_path

        except S3Error as e:
            logger.error(f"Failed to upload CV to MinIO: {e}")
            raise

    def upload_cv_bytes(
        self,
        data: bytes,
        user_id: str,
        filename: str,
        version_id: Optional[str] = None,
        content_type: str = "application/pdf"
    ) -> str:
        """
        Upload CV from bytes data.

        Args:
            data: File content as bytes
            user_id: User identifier
            filename: Filename to store as
            version_id: Optional version identifier
            content_type: MIME type

        Returns:
            Object path
        """
        from io import BytesIO

        object_path = self._get_object_path(user_id, filename, version_id)

        try:
            data_stream = BytesIO(data)
            self.client.put_object(
                self.bucket,
                object_path,
                data_stream,
                length=len(data),
                content_type=content_type
            )

            logger.info(f"Uploaded CV bytes to MinIO: {object_path}")
            return object_path

        except S3Error as e:
            logger.error(f"Failed to upload CV bytes to MinIO: {e}")
            raise

    def get_download_url(
        self,
        user_id: str,
        filename: str,
        version_id: Optional[str] = None,
        expires_hours: int = DEFAULT_URL_EXPIRY_HOURS
    ) -> str:
        """
        Get a time-limited presigned URL for downloading a CV.

        Args:
            user_id: User identifier
            filename: Filename to download
            version_id: Optional version identifier
            expires_hours: URL validity in hours (default: 1)

        Returns:
            Presigned download URL
        """
        object_path = self._get_object_path(user_id, filename, version_id)

        try:
            url = self.client.presigned_get_object(
                self.bucket,
                object_path,
                expires=timedelta(hours=expires_hours)
            )

            # Transform internal URL to external (browser-accessible) URL
            url = self._transform_url_for_external(url)

            logger.debug(f"Generated presigned URL for: {object_path}")
            return url

        except S3Error as e:
            logger.error(f"Failed to generate presigned URL: {e}")
            raise

    def get_download_url_by_path(
        self,
        object_path: str,
        expires_hours: int = DEFAULT_URL_EXPIRY_HOURS
    ) -> str:
        """
        Get presigned URL using full object path.

        Args:
            object_path: Full object path (e.g., "user123/versions/cv.pdf")
            expires_hours: URL validity in hours

        Returns:
            Presigned download URL
        """
        try:
            url = self.client.presigned_get_object(
                self.bucket,
                object_path,
                expires=timedelta(hours=expires_hours)
            )

            # Transform internal URL to external (browser-accessible) URL
            url = self._transform_url_for_external(url)

            return url

        except S3Error as e:
            logger.error(f"Failed to generate presigned URL: {e}")
            raise

    def list_user_cvs(self, user_id: str) -> list:
        """
        List all CVs for a user.

        Args:
            user_id: User identifier

        Returns:
            List of objects with name, size, last_modified
        """
        prefix = f"{user_id}/versions/"

        try:
            objects = self.client.list_objects(
                self.bucket,
                prefix=prefix,
                recursive=True
            )

            result = []
            for obj in objects:
                result.append({
                    "name": obj.object_name.replace(prefix, ""),
                    "full_path": obj.object_name,
                    "size": obj.size,
                    "last_modified": obj.last_modified,
                    "etag": obj.etag
                })

            return result

        except S3Error as e:
            logger.error(f"Failed to list user CVs: {e}")
            raise

    def delete_cv(
        self,
        user_id: str,
        filename: str,
        version_id: Optional[str] = None
    ) -> bool:
        """
        Delete a CV file.

        Args:
            user_id: User identifier
            filename: Filename to delete
            version_id: Optional version identifier

        Returns:
            True if deleted successfully
        """
        object_path = self._get_object_path(user_id, filename, version_id)

        try:
            self.client.remove_object(self.bucket, object_path)
            logger.info(f"Deleted CV from MinIO: {object_path}")
            return True

        except S3Error as e:
            logger.error(f"Failed to delete CV: {e}")
            raise

    def cv_exists(
        self,
        user_id: str,
        filename: str,
        version_id: Optional[str] = None
    ) -> bool:
        """
        Check if a CV exists.

        Args:
            user_id: User identifier
            filename: Filename to check
            version_id: Optional version identifier

        Returns:
            True if exists
        """
        object_path = self._get_object_path(user_id, filename, version_id)

        try:
            self.client.stat_object(self.bucket, object_path)
            return True
        except S3Error as e:
            if e.code == "NoSuchKey":
                return False
            raise

    def download_cv_to_local(
        self,
        user_id: str,
        filename: str,
        local_path: str,
        version_id: Optional[str] = None
    ) -> bool:
        """
        Download a CV file from MinIO to local filesystem.

        Args:
            user_id: User identifier
            filename: Filename to download
            local_path: Local path to save the file
            version_id: Optional version identifier

        Returns:
            True if downloaded successfully, False otherwise
        """
        object_path = self._get_object_path(user_id, filename, version_id)

        try:
            # Ensure parent directory exists
            os.makedirs(os.path.dirname(local_path), exist_ok=True)

            # Download file
            self.client.fget_object(self.bucket, object_path, local_path)
            logger.info(f"Downloaded CV from MinIO: {object_path} -> {local_path}")
            return True

        except S3Error as e:
            if e.code == "NoSuchKey":
                logger.warning(f"CV not found in MinIO: {object_path}")
                return False
            logger.error(f"Failed to download CV from MinIO: {e}")
            return False

    def download_cv_by_path(
        self,
        storage_path: str,
        local_path: str
    ) -> bool:
        """
        Download a CV file from MinIO using the full storage path.

        Args:
            storage_path: Full MinIO object path (e.g., "user@email.com/versions/file.docx")
            local_path: Local path to save the file

        Returns:
            True if downloaded successfully, False otherwise
        """
        try:
            # Ensure parent directory exists
            os.makedirs(os.path.dirname(local_path), exist_ok=True)

            # Download file directly using the storage path
            self.client.fget_object(self.bucket, storage_path, local_path)
            logger.info(f"Downloaded CV from MinIO: {storage_path} -> {local_path}")
            return True

        except S3Error as e:
            if e.code == "NoSuchKey":
                logger.warning(f"CV not found in MinIO: {storage_path}")
                return False
            logger.error(f"Failed to download CV from MinIO: {e}")
            return False

    def download_cv_bytes(
        self,
        user_id: str,
        filename: str,
        version_id: Optional[str] = None
    ) -> Optional[bytes]:
        """
        Download a CV file from MinIO as bytes.

        Args:
            user_id: User identifier
            filename: Filename to download
            version_id: Optional version identifier

        Returns:
            File content as bytes, or None if not found
        """
        object_path = self._get_object_path(user_id, filename, version_id)

        try:
            response = self.client.get_object(self.bucket, object_path)
            data = response.read()
            response.close()
            response.release_conn()
            logger.info(f"Downloaded CV bytes from MinIO: {object_path} ({len(data)} bytes)")
            return data

        except S3Error as e:
            if e.code == "NoSuchKey":
                logger.warning(f"CV not found in MinIO: {object_path}")
                return None
            logger.error(f"Failed to download CV bytes from MinIO: {e}")
            return None


# Global instance for convenience
_storage_instance: Optional[MinIOStorage] = None


def get_minio_storage() -> MinIOStorage:
    """Get or create global MinIO storage instance."""
    global _storage_instance
    if _storage_instance is None:
        _storage_instance = MinIOStorage()
    return _storage_instance


def upload_pdf_to_minio(
    file_path: str,
    filename: str,
    user_id: str = "default"
) -> str:
    """
    Convenience function to upload PDF to MinIO.

    Drop-in replacement for upload_pdf_to_wordpress.

    Args:
        file_path: Local path to PDF
        filename: Filename to store as
        user_id: User identifier (default: "default" for backward compatibility)

    Returns:
        Presigned download URL (valid for 24 hours)
    """
    storage = get_minio_storage()

    # Upload the file
    object_path = storage.upload_cv(
        file_path=file_path,
        user_id=user_id,
        filename=filename
    )

    # Return a presigned URL valid for 24 hours
    return storage.get_download_url_by_path(object_path, expires_hours=24)
