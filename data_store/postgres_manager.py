#!/usr/bin/env python3
"""
WinningCV: PostgreSQL Data Layer
=================================
Drop-in replacement for AirtableManager and CVVersionManager.

This module provides the same API as the Airtable classes but uses PostgreSQL.
Can be used for dual-write during migration or as the final replacement.

Usage:
    # Replace imports
    # from data_store.airtable_manager import AirtableManager
    from data_store.postgres_manager import PostgresManager
    
    # Same API
    manager = PostgresManager()
    manager.create_job_record(job_data, user_email)
    manager.get_user_config(user_email)
"""

import asyncio
import json
import logging
import os
import uuid
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional

import psycopg2
from psycopg2.extras import DictCursor, Json, RealDictCursor

logger = logging.getLogger(__name__)

# Database connection - prefer settings, fallback to env
try:
    from config.settings_v2 import settings
    DATABASE_URL = os.getenv("DATABASE_URL", settings.postgres_dsn)
except ImportError:
    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        os.getenv("POSTGRES_URL", "postgresql://winningcv:winningcv_secret@postgres:5432/winningcv")
    )


class PostgresManager:
    """
    PostgreSQL-based data manager that mirrors AirtableManager's API.
    
    Designed as a drop-in replacement during migration.
    """
    
    def __init__(self, database_url: str = None):
        self.database_url = database_url or DATABASE_URL
        self.logger = logging.getLogger(self.__class__.__name__)
        self._conn = None
    
    @contextmanager
    def get_cursor(self, dict_cursor: bool = True):
        """Context manager for database cursor with auto-commit/rollback."""
        conn = psycopg2.connect(self.database_url)
        cursor_factory = RealDictCursor if dict_cursor else None
        cursor = conn.cursor(cursor_factory=cursor_factory)
        try:
            yield cursor
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
            conn.close()

    # =========================================================================
    # ASYNC METHODS (for telemetry and other async routes)
    # =========================================================================

    def _sync_execute(self, query: str, *args) -> None:
        """Synchronous execute for async wrapper."""
        with self.get_cursor() as cursor:
            cursor.execute(query, args)

    def _sync_fetch(self, query: str, *args) -> List[Dict]:
        """Synchronous fetch for async wrapper."""
        with self.get_cursor() as cursor:
            cursor.execute(query, args)
            return [dict(row) for row in cursor.fetchall()]

    async def execute(self, query: str, *args) -> None:
        """Async execute using thread pool for telemetry routes."""
        await asyncio.to_thread(self._sync_execute, query, *args)

    async def fetch(self, query: str, *args) -> List[Dict]:
        """Async fetch using thread pool for telemetry routes."""
        return await asyncio.to_thread(self._sync_fetch, query, *args)

    # =========================================================================
    # JOBS
    # =========================================================================
    
    def job_exists(self, job_link: str) -> bool:
        """Check if a job with this link already exists."""
        with self.get_cursor() as cursor:
            cursor.execute(
                "SELECT 1 FROM jobs WHERE job_link = %s LIMIT 1",
                (job_link,)
            )
            return cursor.fetchone() is not None
    
    def get_existing_job_links(self) -> set:
        """Get all existing job links to prevent duplicates."""
        try:
            with self.get_cursor() as cursor:
                cursor.execute("SELECT job_link FROM jobs WHERE job_link IS NOT NULL")
                return {row["job_link"] for row in cursor.fetchall()}
        except Exception as e:
            self.logger.error(f"Failed to fetch existing jobs: {e}")
            return set()
    
    def create_job_record(self, job_data: Dict, user_email: str = "system") -> Optional[Dict]:
        """Create new job record."""
        try:
            with self.get_cursor() as cursor:
                cursor.execute("""
                    INSERT INTO jobs (
                        user_email, job_title, job_description, job_date, job_link,
                        company, location, matching_score, cv_link, application_status
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id, created_at
                """, (
                    user_email,
                    job_data.get("Job Title"),
                    job_data.get("Job Description"),
                    self._format_date(job_data.get("Job Date")),
                    job_data.get("Job Link"),
                    job_data.get("Company"),
                    job_data.get("Location"),
                    job_data.get("score", 0),
                    job_data.get("cv_url", ""),
                    job_data.get("Application Status", "saved"),
                ))
                result = cursor.fetchone()
                self.logger.info(f"Created job: {result['id']}")
                return {"id": str(result["id"]), "fields": job_data}
        except Exception as e:
            self.logger.error(f"Create failed: {e}")
            return None
    
    def update_cv_info(
        self,
        job_link: str,
        score: int,
        cv_url: str,
        reasons: Optional[List[str]] = None,
        suggestions: Optional[List[str]] = None,
        ats_score: Optional[int] = None,
        hr_score: Optional[int] = None,
        llm_score: Optional[int] = None,
        recommendation: Optional[str] = None,
        matched_keywords: Optional[List[str]] = None,
        missing_keywords: Optional[List[str]] = None
    ) -> Optional[Dict]:
        """Update matching score and CV link for existing job."""
        try:
            with self.get_cursor() as cursor:
                cursor.execute("""
                    UPDATE jobs SET
                        matching_score = %s,
                        cv_link = %s,
                        match_reasons = %s,
                        match_suggestions = %s,
                        ats_score = %s,
                        hr_score = %s,
                        llm_score = %s,
                        hr_recommendation = %s,
                        matched_keywords = %s,
                        missing_keywords = %s,
                        application_status = CASE WHEN application_status = 'saved' THEN 'cv_generated' ELSE application_status END,
                        updated_at = NOW()
                    WHERE job_link = %s
                    RETURNING id
                """, (
                    score,
                    cv_url,
                    "\n".join(reasons) if isinstance(reasons, list) else reasons,
                    "\n".join(suggestions) if isinstance(suggestions, list) else suggestions,
                    ats_score,
                    hr_score,
                    llm_score,
                    recommendation,
                    ", ".join(matched_keywords[:15]) if isinstance(matched_keywords, list) else matched_keywords,
                    ", ".join(missing_keywords[:15]) if isinstance(missing_keywords, list) else missing_keywords,
                    job_link,
                ))
                result = cursor.fetchone()
                return {"id": str(result["id"])} if result else None
        except Exception as e:
            self.logger.error(f"Update failed: {e}")
            return None
    
    def get_unprocessed_jobs(self) -> List[Dict]:
        """Get jobs without CV links that have descriptions."""
        try:
            with self.get_cursor() as cursor:
                cursor.execute("""
                    SELECT id, job_title as "Job Title", job_description as "Job Description",
                           job_link as "Job Link", company as "Company"
                    FROM jobs
                    WHERE (cv_link IS NULL OR cv_link = '')
                      AND job_description IS NOT NULL AND job_description != ''
                    ORDER BY created_at DESC
                """)
                results = []
                for row in cursor.fetchall():
                    fields = dict(row)
                    # Convert None to empty string for required fields
                    if fields.get("cv_pdf_url") is None:
                        fields["cv_pdf_url"] = ""
                    results.append({"id": str(row["id"]), "fields": fields})
                return results
        except Exception as e:
            self.logger.error(f"Fetch unprocessed failed: {e}")
            return []
    
    # =========================================================================
    # HISTORY
    # =========================================================================
    
    def create_history_record(self, data: Dict) -> Optional[str]:
        """Create a history record and return the record ID."""
        try:
            with self.get_cursor() as cursor:
                cursor.execute("""
                    INSERT INTO cv_history (
                        user_email, job_title, job_description, instructions,
                        cv_markdown, cv_pdf_url, analysis_status
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    data.get("user_email"),
                    data.get("job_title"),
                    data.get("job_description"),
                    data.get("instructions"),
                    data.get("cv_markdown"),
                    data.get("cv_pdf_url"),
                    data.get("analysis_status", "pending"),
                ))
                result = cursor.fetchone()
                record_id = str(result["id"])
                self.logger.info(f"History record created: {record_id}")
                return record_id
        except Exception as e:
            self.logger.error(f"create_history_record error: {e}")
            return None
    
    def update_history_analysis(self, record_id: str, analysis_json: str, status: str = "ready") -> bool:
        """Update history record with CV-JD fit analysis."""
        try:
            with self.get_cursor() as cursor:
                cursor.execute("""
                    UPDATE cv_history SET
                        cv_analysis = %s::jsonb,
                        analysis_status = %s,
                        updated_at = NOW()
                    WHERE id = %s
                """, (analysis_json, status, record_id))
                self.logger.info(f"History analysis updated: {record_id} status={status}")
                return True
        except Exception as e:
            self.logger.error(f"update_history_analysis error: {e}")
            return False
    
    def get_history_record(self, record_id: str) -> Optional[Dict]:
        """Get a single history record by ID."""
        try:
            with self.get_cursor() as cursor:
                cursor.execute("""
                    SELECT id, user_email, job_title, job_description, instructions,
                           cv_markdown, cv_pdf_url, cv_analysis, analysis_status, created_at
                    FROM cv_history WHERE id = %s
                """, (record_id,))
                row = cursor.fetchone()
                if row:
                    return {"id": str(row["id"]), "fields": dict(row)}
                return None
        except Exception as e:
            self.logger.error(f"get_history_record error: {e}")
            return None
    
    def get_history_by_user(self, user_email: str) -> List[Dict]:
        """Get all history records for a user."""
        try:
            with self.get_cursor() as cursor:
                cursor.execute("""
                    SELECT id, user_email, job_title, job_description, instructions,
                           cv_markdown, cv_pdf_url, cv_analysis, analysis_status, created_at
                    FROM cv_history
                    WHERE user_email = %s
                    ORDER BY created_at DESC
                """, (user_email,))
                results = []
                for row in cursor.fetchall():
                    fields = dict(row)
                    # Convert None to empty string for required fields
                    if fields.get("cv_pdf_url") is None:
                        fields["cv_pdf_url"] = ""
                    results.append({"id": str(row["id"]), "fields": fields})
                return results
        except Exception as e:
            self.logger.error(f"get_history_by_user error: {e}")
            return []
    
    # =========================================================================
    # USER CONFIG
    # =========================================================================
    
    def get_user_config(self, user_email: str) -> Dict:
        """Retrieve user's saved configuration."""
        try:
            with self.get_cursor() as cursor:
                cursor.execute("""
                    SELECT * FROM user_configs WHERE user_email = %s
                """, (user_email,))
                row = cursor.fetchone()
                return dict(row) if row else {}
        except Exception as e:
            self.logger.error(f"Config fetch failed: {e}")
            return {}
    
    def save_user_config(self, config_data: Dict) -> bool:
        """Store/update user configuration (upsert)."""
        try:
            with self.get_cursor() as cursor:
                cursor.execute("""
                    INSERT INTO user_configs (
                        user_email, base_cv_path, base_cv_link, linkedin_job_url,
                        seek_job_url, max_jobs_to_scrape, additional_search_term,
                        google_search_term, location, hours_old, results_wanted, country
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (user_email) DO UPDATE SET
                        base_cv_path = EXCLUDED.base_cv_path,
                        base_cv_link = EXCLUDED.base_cv_link,
                        linkedin_job_url = EXCLUDED.linkedin_job_url,
                        seek_job_url = EXCLUDED.seek_job_url,
                        max_jobs_to_scrape = EXCLUDED.max_jobs_to_scrape,
                        additional_search_term = EXCLUDED.additional_search_term,
                        google_search_term = EXCLUDED.google_search_term,
                        location = EXCLUDED.location,
                        hours_old = EXCLUDED.hours_old,
                        results_wanted = EXCLUDED.results_wanted,
                        country = EXCLUDED.country,
                        updated_at = NOW()
                """, (
                    config_data["user_email"],
                    config_data.get("base_cv_path"),
                    config_data.get("base_cv_link", ""),
                    config_data.get("linkedin_job_url"),
                    config_data.get("seek_job_url"),
                    config_data.get("max_jobs_to_scrape", 50),
                    config_data.get("additional_search_term"),
                    config_data.get("google_search_term"),
                    config_data.get("location"),
                    config_data.get("hours_old", 168),
                    config_data.get("results_wanted", 10),
                    config_data.get("country", "Australia"),
                ))
                return True
        except Exception as e:
            self.logger.error(f"Config save failed: {e}")
            return False
    
    # =========================================================================
    # NOTIFICATIONS
    # =========================================================================
    
    def get_notification_preferences(self, user_email: str) -> Dict:
        """Retrieve user's notification preferences."""
        try:
            with self.get_cursor() as cursor:
                cursor.execute("""
                    SELECT email_alerts, telegram_alerts, wechat_alerts, weekly_digest,
                           telegram_chat_id, wechat_id, notification_email
                    FROM user_configs WHERE user_email = %s
                """, (user_email,))
                row = cursor.fetchone()
                if row:
                    return {
                        "email_alerts": row["email_alerts"],
                        "telegram_alerts": row["telegram_alerts"],
                        "wechat_alerts": row["wechat_alerts"],
                        "weekly_digest": row["weekly_digest"],
                        "telegram_chat_id": row["telegram_chat_id"],
                        "wechat_id": row["wechat_id"],
                        "wechat_openid": row["wechat_id"],  # Backward compatibility
                        "notification_email": row["notification_email"],
                    }
                return {}
        except Exception as e:
            self.logger.error(f"Notification prefs fetch failed: {e}")
            return {}
    
    def save_notification_preferences(self, prefs_data: Dict) -> bool:
        """Store/update notification preferences."""
        user_email = prefs_data.get("user_email")
        if not user_email:
            self.logger.error("No user_email provided for notification prefs")
            return False
        
        try:
            with self.get_cursor() as cursor:
                cursor.execute("""
                    INSERT INTO user_configs (user_email, email_alerts, telegram_alerts,
                        wechat_alerts, weekly_digest, telegram_chat_id, wechat_id, notification_email)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (user_email) DO UPDATE SET
                        email_alerts = EXCLUDED.email_alerts,
                        telegram_alerts = EXCLUDED.telegram_alerts,
                        wechat_alerts = EXCLUDED.wechat_alerts,
                        weekly_digest = EXCLUDED.weekly_digest,
                        telegram_chat_id = EXCLUDED.telegram_chat_id,
                        wechat_id = EXCLUDED.wechat_id,
                        notification_email = EXCLUDED.notification_email,
                        updated_at = NOW()
                """, (
                    user_email,
                    prefs_data.get("email_alerts", True),
                    prefs_data.get("telegram_alerts", False),
                    prefs_data.get("wechat_alerts", False),
                    prefs_data.get("weekly_digest", True),
                    prefs_data.get("telegram_chat_id") or "",
                    prefs_data.get("wechat_id") or prefs_data.get("wechat_openid") or "",
                    prefs_data.get("notification_email") or "",
                ))
                self.logger.info(f"Notification preferences saved for {user_email}")
                return True
        except Exception as e:
            self.logger.error(f"Notification prefs save failed: {e}")
            return False
    
    def get_users_with_notifications_enabled(self) -> List[Dict]:
        """Get all users with at least one notification channel enabled."""
        try:
            with self.get_cursor() as cursor:
                cursor.execute("""
                    SELECT user_email, email_alerts, telegram_alerts, wechat_alerts,
                           weekly_digest, telegram_chat_id, wechat_id, notification_email
                    FROM user_configs
                    WHERE email_alerts OR telegram_alerts OR wechat_alerts
                """)
                return [
                    {
                        "user_email": row["user_email"],
                        "email_alerts": row["email_alerts"],
                        "telegram_alerts": row["telegram_alerts"],
                        "wechat_alerts": row["wechat_alerts"],
                        "weekly_digest": row["weekly_digest"],
                        "telegram_chat_id": row["telegram_chat_id"],
                        "wechat_id": row["wechat_id"],
                        "wechat_openid": row["wechat_id"],
                        "notification_email": row["notification_email"],
                    }
                    for row in cursor.fetchall()
                ]
        except Exception as e:
            self.logger.error(f"Failed to get users with notifications: {e}")
            return []
    

    # =========================================================================
    # AIRTABLE API COMPATIBILITY LAYER
    # =========================================================================
    
    def get_records_by_filter(self, formula: str) -> List[Dict]:
        """
        Airtable API compatibility layer.
        Translates simple Airtable formulas to SQL queries.
        
        Supports:
            {User Email} = 'value'
            {field} = 'value'
        
        Returns records in Airtable format: {"id": ..., "fields": {...}}
        """
        import re
        
        # Parse simple Airtable formula: {Field Name} = 'value'
        match = re.match(r"\{([^}]+)\}\s*=\s*'([^']*)'", formula.strip())
        if not match:
            self.logger.warning(f"Unsupported formula: {formula}")
            return []
        
        field_name = match.group(1)
        field_value = match.group(2)
        
        # Map Airtable field names to Postgres columns
        field_map = {
            "User Email": "user_email",
            "Job Title": "job_title",
            "Job Link": "job_link",
            "Company": "company",
            "Location": "location",
        }
        
        column_name = field_map.get(field_name)
        if not column_name:
            self.logger.warning(f"Unsupported filter field: {field_name}")
            return []
        
        try:
            with self.get_cursor() as cursor:
                cursor.execute(f"""
                    SELECT id, user_email, job_title, job_description,
                           job_date, job_link, company, location, matching_score,
                           cv_link, match_reasons, match_suggestions,
                           ats_score, hr_score, llm_score, hr_recommendation,
                           matched_keywords, missing_keywords, application_status,
                           application_notes, applied_at, created_at, updated_at
                    FROM jobs
                    WHERE {column_name} = %s
                    ORDER BY created_at DESC
                """, (field_value,))

                rows = cursor.fetchall()

                # Convert to Airtable format
                records = []
                for row in rows:
                    record = {
                        "id": str(row["id"]),
                        "fields": {
                            "User Email": row["user_email"],
                            "Job Title": row["job_title"],
                            "Job Description": row["job_description"],
                            "Job Date": str(row["job_date"]) if row["job_date"] else None,
                            "Job Link": row["job_link"],
                            "Company": row["company"],
                            "Location": row["location"],
                            "Matching Score": row["matching_score"],
                            "CV Link": row["cv_link"],
                            "Match Reasons": row["match_reasons"],
                            "Match Suggestions": row["match_suggestions"],
                            "ATS Score": row["ats_score"],
                            "HR Score": row["hr_score"],
                            "LLM Score": row["llm_score"],
                            "HR Recommendation": row["hr_recommendation"],
                            "Matched Keywords": row["matched_keywords"],
                            "Missing Keywords": row["missing_keywords"],
                            "Application Status": row.get("application_status") or "saved",
                            "Application Notes": row.get("application_notes"),
                            "Applied At": row.get("applied_at"),
                            "Created At": row["created_at"].isoformat() if row["created_at"] else None,
                            "Updated At": row["updated_at"].isoformat() if row["updated_at"] else None,
                        }
                    }
                    records.append(record)
                
                return records
                
        except Exception as e:
            self.logger.error(f"get_records_by_filter failed: {e}")
            return []

    def update_application_status(
        self,
        job_id: str,
        user_email: str,
        application_status: str,
        application_notes: Optional[str] = None,
    ) -> Optional[Dict]:
        """Update the user-facing application tracking state for a job."""
        try:
            with self.get_cursor() as cursor:
                cursor.execute("""
                    UPDATE jobs SET
                        application_status = %s,
                        application_notes = %s,
                        applied_at = CASE
                            WHEN %s = 'applied' AND applied_at IS NULL THEN NOW()
                            ELSE applied_at
                        END,
                        updated_at = NOW()
                    WHERE id = %s AND user_email = %s
                    RETURNING id
                """, (application_status, application_notes, application_status, job_id, user_email))
                result = cursor.fetchone()
                return {"id": str(result["id"])} if result else None
        except Exception as e:
            self.logger.error(f"Application status update failed: {e}")
            return None

    # =========================================================================
    # UTILITIES
    # =========================================================================
    
    def _format_date(self, date_str: Optional[str]) -> Optional[str]:
        """Ensure PostgreSQL-compatible date format."""
        if not date_str:
            return None
        formats = [
            '%a, %d %b %Y %H:%M:%S %Z',
            '%Y-%m-%dT%H:%M:%S.%fZ',
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d'
        ]
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime('%Y-%m-%d')
            except (ValueError, TypeError):
                continue
        return datetime.now().strftime('%Y-%m-%d')


# ============================================================================
# CV VERSION MANAGER (PostgreSQL version)
# ============================================================================

class PostgresCVVersionManager:
    """
    PostgreSQL-based CV version manager.
    Mirrors CVVersionManager API but uses PostgreSQL instead of Airtable.
    """
    
    def __init__(self, database_url: str = None):
        self.database_url = database_url or DATABASE_URL
        self.logger = logging.getLogger(self.__class__.__name__)
        self._minio = None
    
    @property
    def minio(self):
        """Lazy initialization of MinIO storage."""
        if self._minio is None:
            from utils.minio_storage import get_minio_storage
            self._minio = get_minio_storage()
        return self._minio
    
    @contextmanager
    def get_cursor(self, dict_cursor: bool = True):
        """Context manager for database cursor."""
        conn = psycopg2.connect(self.database_url)
        cursor_factory = RealDictCursor if dict_cursor else None
        cursor = conn.cursor(cursor_factory=cursor_factory)
        try:
            yield cursor
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
            conn.close()
    
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
        """Create a new CV version."""
        import hashlib
        import os
        
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
        
        try:
            with self.get_cursor() as cursor:
                cursor.execute("""
                    INSERT INTO cv_versions (
                        version_id, user_email, version_name, auto_category, user_tags,
                        storage_path, file_size, content_hash, parent_version_id,
                        is_archived, usage_count, response_count,
                        source_job_link, source_job_title
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id, created_at
                """, (
                    version_id, user_email, version_name, auto_category,
                    user_tags or [], storage_path, file_size, content_hash,
                    parent_version_id, False, 0, 0, source_job_link, source_job_title
                ))
                result = cursor.fetchone()
                self.logger.info(f"Created CV version: {version_id} for {user_email}")
                
                return {
                    "id": str(result["id"]),
                    "version_id": version_id,
                    "user_email": user_email,
                    "version_name": version_name,
                    "auto_category": auto_category or "",
                    "user_tags": ",".join(user_tags) if user_tags else "",
                    "storage_path": storage_path,
                    "file_size": file_size,
                    "content_hash": content_hash,
                    "created_at": str(result["created_at"]),
                }
        except Exception as e:
            self.logger.error(f"Failed to create CV version: {e}")
            # Cleanup MinIO on failure
            try:
                self.minio.delete_cv(user_email, filename, version_id)
            except Exception:
                pass
            raise
    
    def get_version(self, version_id: str, user_email: str) -> Optional[Dict[str, Any]]:
        """Get a specific CV version by ID."""
        try:
            with self.get_cursor() as cursor:
                cursor.execute("""
                    SELECT * FROM cv_versions
                    WHERE version_id = %s AND user_email = %s
                """, (version_id, user_email))
                row = cursor.fetchone()
                return self._row_to_dict(row) if row else None
        except Exception as e:
            self.logger.error(f"Failed to get version {version_id}: {e}")
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
        """List CV versions for a user."""
        try:
            with self.get_cursor() as cursor:
                query = "SELECT * FROM cv_versions WHERE user_email = %s"
                params = [user_email]
                
                if not include_archived:
                    query += " AND NOT is_archived"
                
                if category:
                    query += " AND auto_category = %s"
                    params.append(category)
                
                if tags:
                    query += " AND user_tags && %s"
                    params.append(tags)
                
                query += " ORDER BY created_at DESC LIMIT %s OFFSET %s"
                params.extend([limit, offset])
                
                cursor.execute(query, params)
                return [self._row_to_dict(row) for row in cursor.fetchall()]
        except Exception as e:
            self.logger.error(f"Failed to list versions for {user_email}: {e}")
            return []
    
    def update_version(
        self,
        version_id: str,
        user_email: str,
        updates: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Update CV version metadata."""
        allowed = {"version_name", "user_tags", "auto_category", "is_archived"}
        filtered = {k: v for k, v in updates.items() if k in allowed}
        
        if not filtered:
            return None
        
        if "user_tags" in filtered:
            if isinstance(filtered["user_tags"], str):
                filtered["user_tags"] = [t.strip() for t in filtered["user_tags"].split(",") if t.strip()]
        
        try:
            with self.get_cursor() as cursor:
                set_clause = ", ".join(f"{k} = %s" for k in filtered.keys())
                query = f"""
                    UPDATE cv_versions SET {set_clause}, updated_at = NOW()
                    WHERE version_id = %s AND user_email = %s
                    RETURNING *
                """
                params = list(filtered.values()) + [version_id, user_email]
                cursor.execute(query, params)
                row = cursor.fetchone()
                return self._row_to_dict(row) if row else None
        except Exception as e:
            self.logger.error(f"Failed to update version {version_id}: {e}")
            return None
    
    def archive_version(self, version_id: str, user_email: str) -> bool:
        """Archive a CV version."""
        return self.update_version(version_id, user_email, {"is_archived": True}) is not None
    
    def restore_version(self, version_id: str, user_email: str) -> bool:
        """Restore an archived CV version."""
        return self.update_version(version_id, user_email, {"is_archived": False}) is not None
    
    def delete_version(self, version_id: str, user_email: str) -> bool:
        """Permanently delete a CV version."""
        try:
            with self.get_cursor() as cursor:
                cursor.execute("""
                    DELETE FROM cv_versions
                    WHERE version_id = %s AND user_email = %s
                    RETURNING storage_path
                """, (version_id, user_email))
                row = cursor.fetchone()
                
                if row and row["storage_path"]:
                    try:
                        filename = f"{version_id}.pdf"
                        self.minio.delete_cv(user_email, filename, version_id)
                    except Exception as e:
                        self.logger.warning(f"Failed to delete MinIO file: {e}")
                
                return row is not None
        except Exception as e:
            self.logger.error(f"Failed to delete version {version_id}: {e}")
            return False
    
    def increment_usage(self, version_id: str, user_email: str) -> bool:
        """Increment usage count."""
        try:
            with self.get_cursor() as cursor:
                cursor.execute("""
                    UPDATE cv_versions SET usage_count = usage_count + 1
                    WHERE version_id = %s AND user_email = %s
                """, (version_id, user_email))
                return True
        except Exception as e:
            self.logger.error(f"Failed to increment usage: {e}")
            return False
    
    def increment_response(self, version_id: str, user_email: str) -> bool:
        """Increment response count."""
        try:
            with self.get_cursor() as cursor:
                cursor.execute("""
                    UPDATE cv_versions SET response_count = response_count + 1
                    WHERE version_id = %s AND user_email = %s
                """, (version_id, user_email))
                return True
        except Exception as e:
            self.logger.error(f"Failed to increment response: {e}")
            return False
    
    def get_analytics(self, user_email: str) -> Dict[str, Any]:
        """Get analytics summary for user's CV versions."""
        try:
            with self.get_cursor() as cursor:
                cursor.execute("SELECT * FROM get_cv_analytics(%s)", (user_email,))
                row = cursor.fetchone()
                
                # Get categories and tags
                cursor.execute("""
                    SELECT DISTINCT auto_category FROM cv_versions
                    WHERE user_email = %s AND auto_category IS NOT NULL
                """, (user_email,))
                categories = [r["auto_category"] for r in cursor.fetchall()]
                
                cursor.execute("""
                    SELECT DISTINCT unnest(user_tags) as tag FROM cv_versions
                    WHERE user_email = %s
                """, (user_email,))
                tags = sorted([r["tag"] for r in cursor.fetchall()])
                
                return {
                    "total_versions": row["total_versions"],
                    "active_versions": row["active_versions"],
                    "archived_versions": row["archived_versions"],
                    "total_usage": row["total_usage"],
                    "total_responses": row["total_responses"],
                    "overall_response_rate": float(row["overall_response_rate"]),
                    "categories": sorted(categories),
                    "tags": tags,
                    "top_performing": [],  # Would need additional query
                }
        except Exception as e:
            self.logger.error(f"Failed to get analytics: {e}")
            return {}
    
    def _row_to_dict(self, row: Dict) -> Dict[str, Any]:
        """Convert database row to API format."""
        return {
            "id": str(row["id"]),
            "version_id": row["version_id"],
            "user_email": row["user_email"],
            "version_name": row["version_name"],
            "auto_category": row["auto_category"] or "",
            "user_tags": ",".join(row["user_tags"]) if row["user_tags"] else "",
            "storage_path": row["storage_path"] or "",
            "parent_version_id": row["parent_version_id"] or "",
            "is_archived": row["is_archived"],
            "usage_count": row["usage_count"],
            "response_count": row["response_count"],
            "source_job_link": row["source_job_link"] or "",
            "source_job_title": row["source_job_title"] or "",
            "file_size": row["file_size"],
            "content_hash": row["content_hash"] or "",
            "created_at": str(row["created_at"]) if row["created_at"] else "",
        }
    
    def _parse_tags(self, tags_value) -> Optional[List[str]]:
        """Parse tags from various formats to list."""
        if not tags_value:
            return None
        if isinstance(tags_value, list):
            return [t.strip() for t in tags_value if t and str(t).strip()]
        if isinstance(tags_value, str):
            return [t.strip() for t in tags_value.split(',') if t.strip()]
        return None
    
    # =========================================================================
    # MISSING METHODS (Added for API compatibility)
    # =========================================================================
    
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
            self.logger.error(f"Failed to get download URL for {version_id}: {e}")
            return None
    
    def get_categories(self, user_email: str) -> List[str]:
        """Get all unique categories for a user's CVs."""
        try:
            with self.get_cursor() as cursor:
                cursor.execute("""
                    SELECT DISTINCT auto_category FROM cv_versions
                    WHERE user_email = %s AND auto_category IS NOT NULL AND auto_category != ''
                """, (user_email,))
                return sorted([r["auto_category"] for r in cursor.fetchall()])
        except Exception as e:
            self.logger.error(f"Failed to get categories for {user_email}: {e}")
            return []
    
    def get_all_tags(self, user_email: str) -> List[str]:
        """Get all unique tags used by a user."""
        try:
            with self.get_cursor() as cursor:
                cursor.execute("""
                    SELECT DISTINCT unnest(user_tags) as tag FROM cv_versions
                    WHERE user_email = %s
                """, (user_email,))
                return sorted([r["tag"] for r in cursor.fetchall()])
        except Exception as e:
            self.logger.error(f"Failed to get tags for {user_email}: {e}")
            return []
    
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
            import os
            import tempfile
            import requests
            
            # Get download URL and fetch file
            download_url = self.get_download_url(source_version_id, user_email)
            if not download_url:
                return None
            
            # Download to temp file
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
                auto_category=source.get('auto_category') or None,
                user_tags=self._parse_tags(source.get('user_tags')),
                parent_version_id=source_version_id
            )
            return new_version
        finally:
            # Cleanup temp file if we created one
            if new_file_path and new_file_path.startswith('/tmp'):
                try:
                    import os
                    os.unlink(new_file_path)
                except Exception:
                    pass
    
    def create_version_from_history(
        self,
        user_email: str,
        history_record: Dict[str, Any],
        version_name: Optional[str] = None,
        auto_category: Optional[str] = None,
        user_tags: Optional[List[str]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Create a CV version from a history record (generated CV).
        
        Downloads the PDF from history and creates a new version in the library.
        """
        import os
        import tempfile
        import requests
        
        fields = history_record.get('fields', history_record)
        pdf_url = fields.get('cv_pdf_url')
        
        if not pdf_url:
            self.logger.error("No PDF URL in history record")
            return None
        
        # Generate version name if not provided
        if not version_name:
            job_title = fields.get('job_title', 'Unknown Job')
            from datetime import datetime
            date_str = datetime.now().strftime('%b %Y')
            version_name = f"{job_title} ({date_str})"
        
        # Download PDF to temp file
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
                resp = requests.get(pdf_url, timeout=30)
                resp.raise_for_status()
                tmp.write(resp.content)
                temp_path = tmp.name
            
            # Create version
            new_version = self.create_version(
                user_email=user_email,
                file_path=temp_path,
                version_name=version_name,
                auto_category=auto_category,
                user_tags=user_tags,
                source_job_link=fields.get('source_job_link'),
                source_job_title=fields.get('job_title'),
            )
            return new_version
        except Exception as e:
            self.logger.error(f"Failed to create version from history: {e}")
            return None
        finally:
            # Cleanup
            if 'temp_path' in locals():
                try:
                    os.unlink(temp_path)
                except Exception:
                    pass


# ============================================================================
# SEARCH TASK MANAGER (PostgreSQL version)
# ============================================================================

class PostgresTaskManager:
    """
    Durable task tracking using PostgreSQL.
    Replaces file-based /tmp/winningcv_search_tasks.json storage.
    Tasks survive API restarts and can be queried after refresh.
    """

    def __init__(self, database_url: str = None):
        self.database_url = database_url or DATABASE_URL
        self.logger = logging.getLogger(self.__class__.__name__)

    @contextmanager
    def get_cursor(self, dict_cursor: bool = True):
        """Context manager for database cursor."""
        conn = psycopg2.connect(self.database_url)
        cursor_factory = RealDictCursor if dict_cursor else None
        cursor = conn.cursor(cursor_factory=cursor_factory)
        try:
            yield cursor
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
            conn.close()

    def create_task(
        self,
        task_id: str,
        user_email: str,
        status: str = "pending",
        message: str = "Task created"
    ) -> Dict[str, Any]:
        """Create a new search task."""
        try:
            with self.get_cursor() as cursor:
                cursor.execute("""
                    INSERT INTO search_tasks (task_id, user_email, status, progress, message)
                    VALUES (%s, %s, %s, 0, %s)
                    RETURNING id, created_at
                """, (task_id, user_email, status, message))
                result = cursor.fetchone()
                self.logger.info(f"Created task: {task_id} for {user_email}")
                return {
                    "task_id": task_id,
                    "status": status,
                    "progress": 0,
                    "message": message,
                    "results_count": None,
                    "created_at": result["created_at"].isoformat(),
                }
        except Exception as e:
            self.logger.error(f"Failed to create task {task_id}: {e}")
            raise

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task by ID."""
        try:
            with self.get_cursor() as cursor:
                cursor.execute("""
                    SELECT task_id, user_email, status, progress, message,
                           results_count, error_details, created_at, updated_at, completed_at
                    FROM search_tasks WHERE task_id = %s
                """, (task_id,))
                row = cursor.fetchone()
                if row:
                    return {
                        "task_id": row["task_id"],
                        "user_email": row["user_email"],
                        "status": row["status"],
                        "progress": row["progress"],
                        "message": row["message"],
                        "results_count": row["results_count"],
                        "error_details": row["error_details"],
                        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                        "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
                        "completed_at": row["completed_at"].isoformat() if row["completed_at"] else None,
                    }
                return None
        except Exception as e:
            self.logger.error(f"Failed to get task {task_id}: {e}")
            return None

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
        updates = []
        params = []

        if status is not None:
            updates.append("status = %s")
            params.append(status)
            if status in ("completed", "failed"):
                updates.append("completed_at = NOW()")

        if progress is not None:
            updates.append("progress = %s")
            params.append(progress)

        if message is not None:
            updates.append("message = %s")
            params.append(message)

        if results_count is not None:
            updates.append("results_count = %s")
            params.append(results_count)

        if error_details is not None:
            updates.append("error_details = %s")
            params.append(error_details)

        if not updates:
            return True

        params.append(task_id)

        try:
            with self.get_cursor() as cursor:
                cursor.execute(f"""
                    UPDATE search_tasks SET {", ".join(updates)}
                    WHERE task_id = %s
                """, params)
                return True
        except Exception as e:
            self.logger.error(f"Failed to update task {task_id}: {e}")
            return False

    def get_user_tasks(
        self,
        user_email: str,
        limit: int = 10,
        include_completed: bool = False
    ) -> List[Dict[str, Any]]:
        """Get recent tasks for a user."""
        try:
            with self.get_cursor() as cursor:
                query = """
                    SELECT task_id, status, progress, message, results_count, created_at
                    FROM search_tasks
                    WHERE user_email = %s
                """
                if not include_completed:
                    query += " AND status NOT IN ('completed', 'failed')"
                query += " ORDER BY created_at DESC LIMIT %s"

                cursor.execute(query, (user_email, limit))
                return [
                    {
                        "task_id": row["task_id"],
                        "status": row["status"],
                        "progress": row["progress"],
                        "message": row["message"],
                        "results_count": row["results_count"],
                        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                    }
                    for row in cursor.fetchall()
                ]
        except Exception as e:
            self.logger.error(f"Failed to get tasks for {user_email}: {e}")
            return []

    def cleanup_old_tasks(self, max_age_hours: int = 24) -> int:
        """Remove completed/failed tasks older than max_age_hours."""
        try:
            with self.get_cursor() as cursor:
                cursor.execute("""
                    DELETE FROM search_tasks
                    WHERE status IN ('completed', 'failed')
                      AND created_at < NOW() - INTERVAL '%s hours'
                """, (max_age_hours,))
                deleted = cursor.rowcount
                if deleted > 0:
                    self.logger.info(f"Cleaned up {deleted} old tasks")
                return deleted
        except Exception as e:
            self.logger.error(f"Failed to cleanup old tasks: {e}")
            return 0


class PostgresTaskQueue:
    """
    Postgres-backed distributed task queue.

    Uses FOR UPDATE SKIP LOCKED for safe concurrent task claiming.
    Supports priority-based processing, retries with backoff, and worker locking.

    This complements PostgresTaskManager (which tracks search_tasks for frontend display)
    by providing a proper worker queue with atomic operations.
    """

    def __init__(self, database_url: str = None):
        self.database_url = database_url or DATABASE_URL
        self.logger = logging.getLogger(self.__class__.__name__)

    @contextmanager
    def get_cursor(self, dict_cursor: bool = True):
        """Context manager for database cursor."""
        conn = psycopg2.connect(self.database_url)
        cursor_factory = RealDictCursor if dict_cursor else None
        cursor = conn.cursor(cursor_factory=cursor_factory)
        try:
            yield cursor
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
            conn.close()

    def enqueue(
        self,
        task_id: str,
        task_type: str,
        payload: Dict[str, Any] = None,
        priority: int = 0,
        max_attempts: int = 3,
        run_after: datetime = None,
        user_email: str = None,
        correlation_id: str = None,
    ) -> Dict[str, Any]:
        """
        Add a new task to the queue.

        Args:
            task_id: Unique task identifier
            task_type: Type of task (e.g., 'job_search', 'cv_analysis')
            payload: Task-specific data (stored as JSONB)
            priority: Higher values = processed first (default 0)
            max_attempts: Maximum retry attempts (default 3)
            run_after: Delay execution until this time
            user_email: Associated user
            correlation_id: Links to external tracking (e.g., search_tasks.task_id)

        Returns:
            Created task record
        """
        try:
            with self.get_cursor() as cursor:
                cursor.execute("""
                    INSERT INTO task_queue
                        (task_id, task_type, payload, priority, max_attempts,
                         run_after, user_email, correlation_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id, task_id, task_type, state, priority,
                              attempts, max_attempts, created_at
                """, (
                    task_id,
                    task_type,
                    Json(payload or {}),
                    priority,
                    max_attempts,
                    run_after,
                    user_email,
                    correlation_id,
                ))
                row = cursor.fetchone()
                self.logger.info(f"Enqueued task {task_id} (type={task_type}, priority={priority})")
                return dict(row)
        except Exception as e:
            self.logger.error(f"Failed to enqueue task {task_id}: {e}")
            raise

    def claim_task(
        self,
        worker_id: str,
        task_types: List[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Atomically claim the next available task.

        Uses FOR UPDATE SKIP LOCKED for safe concurrent access.

        Args:
            worker_id: Identifier of the claiming worker
            task_types: Optional list of task types to claim (None = any)

        Returns:
            Claimed task data or None if no tasks available
        """
        try:
            with self.get_cursor() as cursor:
                # Use the database function for atomic claim
                cursor.execute("""
                    SELECT * FROM claim_next_task(%s, %s)
                """, (worker_id, task_types))
                row = cursor.fetchone()

                if row and row.get("task_id"):
                    self.logger.debug(f"Worker {worker_id} claimed task {row['task_id']}")
                    return dict(row)
                return None
        except Exception as e:
            self.logger.error(f"Failed to claim task for worker {worker_id}: {e}")
            return None

    def complete_task(
        self,
        task_id: str,
        worker_id: str,
        result: Dict[str, Any] = None
    ) -> bool:
        """
        Mark a task as completed.

        Args:
            task_id: Task identifier
            worker_id: Worker that processed the task
            result: Task result data

        Returns:
            True if task was completed, False otherwise
        """
        try:
            with self.get_cursor(dict_cursor=False) as cursor:
                cursor.execute("""
                    SELECT complete_task(%s, %s, %s)
                """, (task_id, worker_id, Json(result) if result else None))
                success = cursor.fetchone()[0]
                if success:
                    self.logger.info(f"Task {task_id} completed by {worker_id}")
                return success
        except Exception as e:
            self.logger.error(f"Failed to complete task {task_id}: {e}")
            return False

    def fail_task(
        self,
        task_id: str,
        worker_id: str,
        error: str,
        retry_after: datetime = None
    ) -> bool:
        """
        Mark a task as failed, optionally scheduling retry.

        Args:
            task_id: Task identifier
            worker_id: Worker that processed the task
            error: Error message
            retry_after: Schedule retry at this time (None = no retry)

        Returns:
            True if task was updated, False otherwise
        """
        try:
            with self.get_cursor(dict_cursor=False) as cursor:
                cursor.execute("""
                    SELECT fail_task(%s, %s, %s, %s)
                """, (task_id, worker_id, error, retry_after))
                success = cursor.fetchone()[0]
                if success:
                    if retry_after:
                        self.logger.warning(f"Task {task_id} failed, retry at {retry_after}: {error}")
                    else:
                        self.logger.error(f"Task {task_id} permanently failed: {error}")
                return success
        except Exception as e:
            self.logger.error(f"Failed to fail task {task_id}: {e}")
            return False

    def heartbeat(self, task_id: str, worker_id: str) -> bool:
        """
        Refresh the lock on a running task.

        Call periodically during long-running tasks to prevent timeout.

        Args:
            task_id: Task identifier
            worker_id: Worker holding the lock

        Returns:
            True if heartbeat was successful
        """
        try:
            with self.get_cursor(dict_cursor=False) as cursor:
                cursor.execute("""
                    SELECT heartbeat_task(%s, %s)
                """, (task_id, worker_id))
                return cursor.fetchone()[0]
        except Exception as e:
            self.logger.error(f"Failed to heartbeat task {task_id}: {e}")
            return False

    def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a pending task.

        Can only cancel tasks that are not yet running.

        Args:
            task_id: Task identifier

        Returns:
            True if task was cancelled
        """
        try:
            with self.get_cursor() as cursor:
                cursor.execute("""
                    UPDATE task_queue
                    SET state = 'cancelled', completed_at = NOW(), updated_at = NOW()
                    WHERE task_id = %s AND state = 'pending'
                """, (task_id,))
                cancelled = cursor.rowcount > 0
                if cancelled:
                    self.logger.info(f"Task {task_id} cancelled")
                return cancelled
        except Exception as e:
            self.logger.error(f"Failed to cancel task {task_id}: {e}")
            return False

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get task details by ID.

        Args:
            task_id: Task identifier

        Returns:
            Task data or None if not found
        """
        try:
            with self.get_cursor() as cursor:
                cursor.execute("""
                    SELECT task_id, task_type, state, priority, payload, result, error,
                           attempts, max_attempts, run_after, locked_by, locked_at,
                           user_email, correlation_id, created_at, updated_at, completed_at
                    FROM task_queue
                    WHERE task_id = %s
                """, (task_id,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            self.logger.error(f"Failed to get task {task_id}: {e}")
            return None

    def get_queue_stats(self) -> Dict[str, Any]:
        """
        Get queue statistics.

        Returns:
            Dict with pending, running, completed, failed counts
        """
        try:
            with self.get_cursor() as cursor:
                cursor.execute("""
                    SELECT
                        COUNT(*) FILTER (WHERE state = 'pending') as pending,
                        COUNT(*) FILTER (WHERE state = 'running') as running,
                        COUNT(*) FILTER (WHERE state = 'completed') as completed,
                        COUNT(*) FILTER (WHERE state = 'failed') as failed,
                        COUNT(*) FILTER (WHERE state = 'cancelled') as cancelled
                    FROM task_queue
                """)
                row = cursor.fetchone()
                return dict(row)
        except Exception as e:
            self.logger.error(f"Failed to get queue stats: {e}")
            return {"pending": 0, "running": 0, "completed": 0, "failed": 0, "cancelled": 0}

    def release_stale_locks(self, timeout_minutes: int = 30) -> int:
        """
        Release locks held by crashed/hung workers.

        Args:
            timeout_minutes: Consider locks stale after this many minutes

        Returns:
            Number of tasks released
        """
        try:
            with self.get_cursor(dict_cursor=False) as cursor:
                cursor.execute("""
                    SELECT release_stale_locks(%s)
                """, (timeout_minutes,))
                released = cursor.fetchone()[0]
                if released > 0:
                    self.logger.warning(f"Released {released} stale task locks")
                return released
        except Exception as e:
            self.logger.error(f"Failed to release stale locks: {e}")
            return 0

    def cleanup_old_tasks(self, max_age_hours: int = 168) -> int:
        """
        Remove old completed/failed/cancelled tasks.

        Args:
            max_age_hours: Remove tasks completed more than this many hours ago

        Returns:
            Number of tasks deleted
        """
        try:
            with self.get_cursor(dict_cursor=False) as cursor:
                cursor.execute("""
                    SELECT cleanup_old_queue_tasks(%s)
                """, (max_age_hours,))
                deleted = cursor.fetchone()[0]
                if deleted > 0:
                    self.logger.info(f"Cleaned up {deleted} old queue tasks")
                return deleted
        except Exception as e:
            self.logger.error(f"Failed to cleanup old queue tasks: {e}")
            return 0


# Global singleton for task manager
_postgres_task_manager: Optional[PostgresTaskManager] = None


def get_postgres_task_manager() -> PostgresTaskManager:
    """Get or create global PostgreSQL task manager instance."""
    global _postgres_task_manager
    if _postgres_task_manager is None:
        _postgres_task_manager = PostgresTaskManager()
    return _postgres_task_manager


# Global singletons
_postgres_manager: Optional[PostgresManager] = None
_postgres_cv_version_manager: Optional[PostgresCVVersionManager] = None
_postgres_task_queue: Optional[PostgresTaskQueue] = None


def get_postgres_manager() -> PostgresManager:
    """Get or create global PostgreSQL manager instance."""
    global _postgres_manager
    if _postgres_manager is None:
        _postgres_manager = PostgresManager()
    return _postgres_manager


def get_postgres_cv_version_manager() -> PostgresCVVersionManager:
    """Get or create global PostgreSQL CV version manager instance."""
    global _postgres_cv_version_manager
    if _postgres_cv_version_manager is None:
        _postgres_cv_version_manager = PostgresCVVersionManager()
    return _postgres_cv_version_manager


def get_postgres_task_queue() -> PostgresTaskQueue:
    """Get or create global PostgreSQL task queue instance."""
    global _postgres_task_queue
    if _postgres_task_queue is None:
        _postgres_task_queue = PostgresTaskQueue()
    return _postgres_task_queue