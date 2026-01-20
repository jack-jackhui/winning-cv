"""
CV Version Manager - Handles CV version persistence and queries.

Uses Airtable for metadata storage and MinIO for file storage.
"""
import logging
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from pyairtable import Api
from pyairtable.formulas import AND, OR, Field, EQ, NE, FIND

from config.settings import Config
from utils.minio_storage import get_minio_storage, MinIOStorage
from utils.airtable_client import get_airtable_api

logger = logging.getLogger(__name__)


class CVVersionManager:
    """
    Manages CV versions with metadata in Airtable and files in MinIO.

    Airtable Table Schema (cv_versions):
    - version_id (Single line text, Primary)
    - user_email (Single line text)
    - version_name (Single line text)
    - auto_category (Single line text) - detected role type
    - user_tags (multipleSelects) - Array of tag options
    - storage_path (Single line text) - MinIO path
    - created_at (Created time)
    - updated_at (Last modified time)
    - parent_version_id (Single line text) - for fork tracking
    - is_archived (Checkbox)
    - usage_count (Number)
    - response_count (Number)
    - source_job_link (URL) - job this was generated for
    - source_job_title (Single line text)
    """

    # Field mapping for Airtable
    FIELD_MAP = {
        "version_id": "version_id",
        "user_email": "user_email",
        "version_name": "version_name",
        "auto_category": "auto_category",
        "user_tags": "user_tags",
        "storage_path": "storage_path",
        "parent_version_id": "parent_version_id",
        "is_archived": "is_archived",
        "usage_count": "usage_count",
        "response_count": "response_count",
        "source_job_link": "source_job_link",
        "source_job_title": "source_job_title",
        "file_size": "file_size",
        "content_hash": "content_hash",
    }

    def __init__(self):
        # Use robust API client with timeouts and retries
        self.api = get_airtable_api()
        self.table = self.api.table(
            Config.AIRTABLE_BASE_ID,
            Config.AIRTABLE_TABLE_ID_CV_VERSIONS
        )
        self._minio: Optional[MinIOStorage] = None

    @property
    def minio(self) -> MinIOStorage:
        """Lazy initialization of MinIO storage."""
        if self._minio is None:
            self._minio = get_minio_storage()
        return self._minio

    def create_version(
        self,
        user_email: str,
        file_path: str,
        version_name: str,
        auto_category: Optional[str] = None,
        user_tags: Optional[List[str]] = None,
        parent_version_id: Optional[str] = None,
        source_job_link: Optional[str] = None,
        source_job_title: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a new CV version.

        Args:
            user_email: User's email
            file_path: Local path to the CV file
            version_name: Human-readable name for this version
            auto_category: Auto-detected role category
            user_tags: User-defined tags
            parent_version_id: ID of parent version if forked
            source_job_link: Job this CV was generated for
            source_job_title: Title of the source job

        Returns:
            Created version record
        """
        import os
        import hashlib

        # Generate unique version ID
        version_id = f"cv_{uuid.uuid4().hex[:12]}"

        # Get file info
        file_size = os.path.getsize(file_path)
        with open(file_path, "rb") as f:
            content_hash = hashlib.md5(f.read()).hexdigest()

        # Upload to MinIO
        filename = f"{version_id}.pdf"
        storage_path = self.minio.upload_cv(
            file_path=file_path,
            user_id=user_email,
            filename=filename,
            version_id=version_id
        )

        # Create Airtable record
        # Note: Omit empty string values - Airtable may reject them for certain field types
        record_data = {
            "version_id": version_id,
            "user_email": user_email,
            "version_name": version_name,
            "storage_path": storage_path,
            "is_archived": False,
            "usage_count": 0,
            "response_count": 0,
            "file_size": file_size,
            "content_hash": content_hash,
        }
        # Only add optional fields if they have values
        if auto_category:
            record_data["auto_category"] = auto_category
        if user_tags:
            # user_tags is a multipleSelects field in Airtable - needs array of option names
            record_data["user_tags"] = user_tags if isinstance(user_tags, list) else [user_tags]
        if parent_version_id:
            record_data["parent_version_id"] = parent_version_id
        if source_job_link:
            record_data["source_job_link"] = source_job_link
        if source_job_title:
            record_data["source_job_title"] = source_job_title

        try:
            record = self.table.create(record_data)
            logger.info(f"Created CV version: {version_id} for {user_email}")
            return self._record_to_dict(record)
        except Exception as e:
            error_str = str(e)
            # Handle Airtable select field errors - retry without problematic fields
            if "INVALID_MULTIPLE_CHOICE_OPTIONS" in error_str or "INVALID_VALUE_FOR_COLUMN" in error_str:
                logger.warning(f"Airtable select field error, retrying without select fields: {e}")
                # Remove select fields that may have invalid options
                record_data.pop("auto_category", None)
                record_data.pop("user_tags", None)
                try:
                    record = self.table.create(record_data)
                    logger.info(f"Created CV version (without select fields): {version_id} for {user_email}")
                    return self._record_to_dict(record)
                except Exception as retry_error:
                    logger.error(f"Retry also failed: {retry_error}")
                    # Fall through to cleanup

            logger.error(f"Failed to create CV version: {e}")
            # Cleanup MinIO on failure
            try:
                self.minio.delete_cv(user_email, filename, version_id)
            except Exception:
                pass
            raise

    def get_version(self, version_id: str, user_email: str) -> Optional[Dict[str, Any]]:
        """Get a specific CV version by ID."""
        try:
            formula = AND(
                EQ(Field("version_id"), version_id),
                EQ(Field("user_email"), user_email)
            )
            records = self.table.all(formula=str(formula), max_records=1)
            if records:
                return self._record_to_dict(records[0])
            return None
        except Exception as e:
            logger.error(f"Failed to get version {version_id}: {e}")
            return None

    def list_versions(
        self,
        user_email: str,
        include_archived: bool = False,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        List CV versions for a user with optional filtering.

        Args:
            user_email: User's email
            include_archived: Include archived versions
            category: Filter by auto_category
            tags: Filter by user tags (any match)
            limit: Max records to return
            offset: Pagination offset

        Returns:
            List of version records
        """
        try:
            conditions = [EQ(Field("user_email"), user_email)]

            if not include_archived:
                conditions.append(EQ(Field("is_archived"), False))

            if category:
                conditions.append(EQ(Field("auto_category"), category))

            formula = AND(*conditions) if len(conditions) > 1 else conditions[0]
            records = self.table.all(formula=str(formula))

            # Filter by tags in Python (Airtable doesn't support array contains)
            if tags:
                filtered = []
                for r in records:
                    # user_tags is multipleSelects - returns as array
                    record_tags = r['fields'].get('user_tags', [])
                    if isinstance(record_tags, str):
                        record_tags = [t.strip() for t in record_tags.split(',') if t.strip()]
                    if any(tag in record_tags for tag in tags):
                        filtered.append(r)
                records = filtered

            # Sort by created_at descending (newest first)
            records.sort(
                key=lambda x: x.get('createdTime', ''),
                reverse=True
            )

            # Apply pagination
            paginated = records[offset:offset + limit]

            return [self._record_to_dict(r) for r in paginated]
        except Exception as e:
            logger.error(f"Failed to list versions for {user_email}: {e}")
            return []

    def update_version(
        self,
        version_id: str,
        user_email: str,
        updates: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Update CV version metadata.

        Allowed updates: version_name, user_tags, auto_category, is_archived
        """
        allowed_fields = {'version_name', 'user_tags', 'auto_category', 'is_archived'}
        filtered_updates = {k: v for k, v in updates.items() if k in allowed_fields}

        if not filtered_updates:
            return None

        # user_tags is a multipleSelects field - keep as array
        if 'user_tags' in filtered_updates:
            if isinstance(filtered_updates['user_tags'], str):
                # Convert comma-separated string to array
                filtered_updates['user_tags'] = [t.strip() for t in filtered_updates['user_tags'].split(',') if t.strip()]
            elif not isinstance(filtered_updates['user_tags'], list):
                filtered_updates['user_tags'] = [filtered_updates['user_tags']] if filtered_updates['user_tags'] else []

        try:
            formula = AND(
                EQ(Field("version_id"), version_id),
                EQ(Field("user_email"), user_email)
            )
            record = self.table.first(formula=str(formula))

            if not record:
                return None

            updated = self.table.update(record['id'], filtered_updates)
            logger.info(f"Updated CV version: {version_id}")
            return self._record_to_dict(updated)
        except Exception as e:
            logger.error(f"Failed to update version {version_id}: {e}")
            return None

    def archive_version(self, version_id: str, user_email: str) -> bool:
        """Archive a CV version (soft delete)."""
        result = self.update_version(version_id, user_email, {"is_archived": True})
        return result is not None

    def restore_version(self, version_id: str, user_email: str) -> bool:
        """Restore an archived CV version."""
        result = self.update_version(version_id, user_email, {"is_archived": False})
        return result is not None

    def delete_version(self, version_id: str, user_email: str) -> bool:
        """
        Permanently delete a CV version (hard delete).

        Warning: This removes both metadata and file storage.
        """
        try:
            formula = AND(
                EQ(Field("version_id"), version_id),
                EQ(Field("user_email"), user_email)
            )
            record = self.table.first(formula=str(formula))

            if not record:
                return False

            # Delete from MinIO
            storage_path = record['fields'].get('storage_path', '')
            if storage_path:
                try:
                    filename = f"{version_id}.pdf"
                    self.minio.delete_cv(user_email, filename, version_id)
                except Exception as e:
                    logger.warning(f"Failed to delete MinIO file: {e}")

            # Delete from Airtable
            self.table.delete(record['id'])
            logger.info(f"Deleted CV version: {version_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete version {version_id}: {e}")
            return False

    def fork_version(
        self,
        source_version_id: str,
        user_email: str,
        new_name: str,
        new_file_path: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Fork an existing version to create a new one.

        If new_file_path is provided, uses that file.
        Otherwise, downloads the source and re-uploads.
        """
        source = self.get_version(source_version_id, user_email)
        if not source:
            return None

        # If no new file, we need to copy the existing one
        if not new_file_path:
            import tempfile
            import os

            # Get download URL and fetch file
            download_url = self.get_download_url(source_version_id, user_email)
            if not download_url:
                return None

            # Download to temp file
            import requests
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
                resp = requests.get(download_url, timeout=30)
                resp.raise_for_status()
                tmp.write(resp.content)
                new_file_path = tmp.name

        try:
            # Create new version with parent reference
            new_version = self.create_version(
                user_email=user_email,
                file_path=new_file_path,
                version_name=new_name,
                auto_category=source.get('auto_category'),
                user_tags=self._parse_tags(source.get('user_tags')),
                parent_version_id=source_version_id
            )
            return new_version
        finally:
            # Cleanup temp file if we created one
            if new_file_path and new_file_path.startswith('/tmp'):
                try:
                    os.unlink(new_file_path)
                except Exception:
                    pass

    def get_download_url(
        self,
        version_id: str,
        user_email: str,
        expires_hours: int = 1
    ) -> Optional[str]:
        """Get a presigned download URL for a CV version."""
        version = self.get_version(version_id, user_email)
        if not version:
            return None

        storage_path = version.get('storage_path')
        if not storage_path:
            return None

        try:
            return self.minio.get_download_url_by_path(storage_path, expires_hours)
        except Exception as e:
            logger.error(f"Failed to get download URL for {version_id}: {e}")
            return None

    def increment_usage(self, version_id: str, user_email: str) -> bool:
        """Increment usage count when CV is used for an application."""
        try:
            formula = AND(
                EQ(Field("version_id"), version_id),
                EQ(Field("user_email"), user_email)
            )
            record = self.table.first(formula=str(formula))

            if not record:
                return False

            current_count = record['fields'].get('usage_count', 0)
            self.table.update(record['id'], {'usage_count': current_count + 1})
            return True
        except Exception as e:
            logger.error(f"Failed to increment usage for {version_id}: {e}")
            return False

    def increment_response(self, version_id: str, user_email: str) -> bool:
        """Increment response count when user gets a callback/interview."""
        try:
            formula = AND(
                EQ(Field("version_id"), version_id),
                EQ(Field("user_email"), user_email)
            )
            record = self.table.first(formula=str(formula))

            if not record:
                return False

            current_count = record['fields'].get('response_count', 0)
            self.table.update(record['id'], {'response_count': current_count + 1})
            return True
        except Exception as e:
            logger.error(f"Failed to increment response for {version_id}: {e}")
            return False

    def get_categories(self, user_email: str) -> List[str]:
        """Get all unique categories for a user's CVs."""
        try:
            formula = EQ(Field("user_email"), user_email)
            records = self.table.all(formula=str(formula), fields=["auto_category"])

            categories = set()
            for r in records:
                cat = r['fields'].get('auto_category', '').strip()
                if cat:
                    categories.add(cat)

            return sorted(list(categories))
        except Exception as e:
            logger.error(f"Failed to get categories for {user_email}: {e}")
            return []

    def get_all_tags(self, user_email: str) -> List[str]:
        """Get all unique tags used by a user."""
        try:
            formula = EQ(Field("user_email"), user_email)
            records = self.table.all(formula=str(formula), fields=["user_tags"])

            tags = set()
            for r in records:
                # user_tags is multipleSelects - returns as array
                tag_list = r['fields'].get('user_tags', [])
                if isinstance(tag_list, str):
                    tag_list = [t.strip() for t in tag_list.split(',') if t.strip()]
                for tag in tag_list:
                    if tag:
                        tags.add(tag)

            return sorted(list(tags))
        except Exception as e:
            logger.error(f"Failed to get tags for {user_email}: {e}")
            return []

    def _parse_tags(self, tags_value) -> Optional[List[str]]:
        """Parse tags from various formats to list."""
        if not tags_value:
            return None
        if isinstance(tags_value, list):
            return [t.strip() for t in tags_value if t and str(t).strip()]
        if isinstance(tags_value, str):
            return [t.strip() for t in tags_value.split(',') if t.strip()]
        return None

    def get_analytics(self, user_email: str) -> Dict[str, Any]:
        """Get analytics summary for user's CV versions.

        Optimized to use a single Airtable query and extract categories/tags
        from the fetched data rather than making separate API calls.
        """
        try:
            versions = self.list_versions(user_email, include_archived=True, limit=1000)

            total = len(versions)
            archived = sum(1 for v in versions if v.get('is_archived'))
            active = total - archived

            total_usage = sum(v.get('usage_count', 0) for v in versions)
            total_responses = sum(v.get('response_count', 0) for v in versions)

            # Calculate response rate
            response_rate = (total_responses / total_usage * 100) if total_usage > 0 else 0

            # Top performing versions (by response rate)
            performing = []
            # Extract categories and tags from fetched versions (avoid extra API calls)
            categories_set = set()
            tags_set = set()

            for v in versions:
                usage = v.get('usage_count', 0)
                responses = v.get('response_count', 0)

                # Collect categories
                cat = v.get('auto_category', '').strip() if v.get('auto_category') else ''
                if cat:
                    categories_set.add(cat)

                # Collect tags
                tags_raw = v.get('user_tags', '')
                if tags_raw:
                    if isinstance(tags_raw, str):
                        for tag in tags_raw.split(','):
                            tag = tag.strip()
                            if tag:
                                tags_set.add(tag)
                    elif isinstance(tags_raw, list):
                        for tag in tags_raw:
                            if tag and str(tag).strip():
                                tags_set.add(str(tag).strip())

                if usage >= 3:  # Minimum usage threshold
                    rate = responses / usage * 100
                    performing.append({
                        'version_id': v['version_id'],
                        'version_name': v['version_name'],
                        'usage_count': usage,
                        'response_count': responses,
                        'response_rate': round(rate, 1)
                    })

            performing.sort(key=lambda x: x['response_rate'], reverse=True)

            return {
                'total_versions': total,
                'active_versions': active,
                'archived_versions': archived,
                'total_usage': total_usage,
                'total_responses': total_responses,
                'overall_response_rate': round(response_rate, 1),
                'top_performing': performing[:5],
                'categories': sorted(list(categories_set)),
                'tags': sorted(list(tags_set))
            }
        except Exception as e:
            logger.error(f"Failed to get analytics for {user_email}: {e}")
            return {}

    def create_version_from_history(
        self,
        user_email: str,
        history_record: Dict[str, Any],
        version_name: Optional[str] = None,
        auto_category: Optional[str] = None,
        user_tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Create a CV version from a history record (generated CV).

        Downloads the PDF from history and creates a new version in the library.

        Args:
            user_email: User's email
            history_record: The history record from Airtable
            version_name: Optional custom name (auto-generated if not provided)
            auto_category: Optional category
            user_tags: Optional tags

        Returns:
            Created version record
        """
        import tempfile
        import requests
        import os
        from datetime import datetime

        fields = history_record.get('fields', {})
        job_title = fields.get('job_title', 'Generated CV')
        cv_pdf_url = fields.get('cv_pdf_url', '')
        history_id = history_record.get('id', '')

        if not cv_pdf_url:
            raise ValueError("History record has no PDF URL")

        # Auto-generate version name if not provided
        if not version_name:
            today = datetime.now().strftime("%b %Y")
            version_name = f"{job_title} ({today})"

        # Download the PDF to a temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
            resp = requests.get(cv_pdf_url, timeout=60)
            resp.raise_for_status()
            tmp.write(resp.content)
            tmp_path = tmp.name

        try:
            # Create the version
            new_version = self.create_version(
                user_email=user_email,
                file_path=tmp_path,
                version_name=version_name,
                auto_category=auto_category or "Generated",
                user_tags=user_tags or ["generated", "auto-saved"],
                source_job_title=job_title,
            )

            logger.info(f"Created CV version from history {history_id}: {new_version.get('version_id')}")
            return new_version

        finally:
            # Cleanup temp file
            try:
                os.unlink(tmp_path)
            except Exception:
                pass

    def _record_to_dict(self, record: Dict) -> Dict[str, Any]:
        """Convert Airtable record to clean dictionary."""
        fields = record.get('fields', {})
        # user_tags is a multipleSelects field - Airtable returns array, convert to comma-separated
        user_tags_raw = fields.get('user_tags', [])
        user_tags = ','.join(user_tags_raw) if isinstance(user_tags_raw, list) else user_tags_raw
        return {
            'id': record.get('id'),
            'version_id': fields.get('version_id', ''),
            'user_email': fields.get('user_email', ''),
            'version_name': fields.get('version_name', ''),
            'auto_category': fields.get('auto_category', ''),
            'user_tags': user_tags,
            'storage_path': fields.get('storage_path', ''),
            'parent_version_id': fields.get('parent_version_id', ''),
            'is_archived': fields.get('is_archived', False),
            'usage_count': fields.get('usage_count', 0),
            'response_count': fields.get('response_count', 0),
            'source_job_link': fields.get('source_job_link', ''),
            'source_job_title': fields.get('source_job_title', ''),
            'file_size': fields.get('file_size', 0),
            'content_hash': fields.get('content_hash', ''),
            'created_at': record.get('createdTime', ''),
        }


# Global instance
_cv_version_manager: Optional[CVVersionManager] = None


def get_cv_version_manager() -> CVVersionManager:
    """Get or create global CV version manager instance."""
    global _cv_version_manager
    if _cv_version_manager is None:
        _cv_version_manager = CVVersionManager()
    return _cv_version_manager
