#!/usr/bin/env python3
"""
WinningCV: Storage Backend Factory
===================================
Provides a unified interface to Airtable or PostgreSQL storage backends.

Configuration via environment variable:
  STORAGE_BACKEND=airtable|postgres|dual

In 'dual' mode, writes go to both backends (Airtable primary, Postgres shadow).
Reads come from Airtable only. This enables safe migration validation.

Usage:
    from data_store.storage_factory import get_data_manager, get_cv_version_manager
    
    manager = get_data_manager()  # Returns appropriate backend
    cv_manager = get_cv_version_manager()  # Returns appropriate backend
"""

import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Configuration - prefer settings, fallback to env
try:
    from config.settings_v2 import settings
    STORAGE_BACKEND = settings.storage_backend.lower()
except ImportError:
    STORAGE_BACKEND = os.getenv("STORAGE_BACKEND", "airtable").lower()

# Validate backend choice
if STORAGE_BACKEND not in ("airtable", "postgres", "dual"):
    logger.warning(f"Invalid STORAGE_BACKEND '{STORAGE_BACKEND}', defaulting to 'airtable'")
    STORAGE_BACKEND = "airtable"


# =============================================================================
# DATA MANAGER (Jobs, History, User Config, Notifications)
# =============================================================================

class DualWriteDataManager:
    """
    Dual-write manager that writes to both Airtable and PostgreSQL.
    Reads come from Airtable (primary) only.
    
    Use this during migration validation to ensure Postgres receives
    all writes without affecting production reads.
    """
    
    def __init__(self, airtable_manager, postgres_manager):
        self.airtable = airtable_manager
        self.postgres = postgres_manager
        self.logger = logging.getLogger(self.__class__.__name__)
    
    # =========================================================================
    # READ OPERATIONS (Airtable primary)
    # =========================================================================
    
    def job_exists(self, job_link: str) -> bool:
        return self.airtable.job_exists(job_link)
    
    def get_existing_job_links(self) -> set:
        return self.airtable.get_existing_job_links()
    
    def get_unprocessed_jobs(self) -> List[Dict]:
        return self.airtable.get_unprocessed_jobs()
    
    def get_job_result(self, job_id: str, user_email: str) -> Optional[Dict]:
        return self.airtable.get_job_result(job_id, user_email)

    def get_history_record(self, record_id: str) -> Optional[Dict]:
        return self.airtable.get_history_record(record_id)
    
    def get_history_by_user(self, user_email: str) -> List[Dict]:
        return self.airtable.get_history_by_user(user_email)
    
    def get_user_config(self, user_email: str) -> Dict:
        return self.airtable.get_user_config(user_email)
    
    def get_notification_preferences(self, user_email: str) -> Dict:
        return self.airtable.get_notification_preferences(user_email)
    
    def get_users_with_notifications_enabled(self) -> List[Dict]:
        return self.airtable.get_users_with_notifications_enabled()
    
    # =========================================================================
    # WRITE OPERATIONS (Dual-write)
    # =========================================================================
    
    def create_job_record(self, job_data: Dict, user_email: str = "system") -> Optional[Dict]:
        # Primary: Airtable
        result = self.airtable.create_job_record(job_data, user_email)
        
        # Shadow: PostgreSQL (fire and forget, log errors)
        try:
            self.postgres.create_job_record(job_data, user_email)
        except Exception as e:
            self.logger.warning(f"Postgres shadow write failed (create_job): {e}")
        
        return result
    
    def update_cv_info(self, job_link: str, score: int, cv_url: str, **kwargs) -> Optional[Dict]:
        result = self.airtable.update_cv_info(job_link, score, cv_url, **kwargs)
        
        try:
            self.postgres.update_cv_info(job_link, score, cv_url, **kwargs)
        except Exception as e:
            self.logger.warning(f"Postgres shadow write failed (update_cv_info): {e}")
        
        return result
    
    def create_history_record(self, data: Dict) -> Optional[str]:
        result = self.airtable.create_history_record(data)
        
        try:
            self.postgres.create_history_record(data)
        except Exception as e:
            self.logger.warning(f"Postgres shadow write failed (create_history): {e}")
        
        return result
    
    def update_history_analysis(self, record_id: str, analysis_json: str, status: str = "ready") -> bool:
        result = self.airtable.update_history_analysis(record_id, analysis_json, status)
        
        try:
            # For Postgres, we need to find the record by Airtable ID mapping
            # This requires the migrated_airtable_id field in history table
            self.postgres.update_history_analysis(record_id, analysis_json, status)
        except Exception as e:
            self.logger.warning(f"Postgres shadow write failed (update_history_analysis): {e}")
        
        return result
    
    def save_user_config(self, config_data: Dict) -> bool:
        result = self.airtable.save_user_config(config_data)
        
        try:
            self.postgres.save_user_config(config_data)
        except Exception as e:
            self.logger.warning(f"Postgres shadow write failed (save_user_config): {e}")
        
        return result
    
    def save_notification_preferences(self, prefs_data: Dict) -> bool:
        result = self.airtable.save_notification_preferences(prefs_data)
        
        try:
            self.postgres.save_notification_preferences(prefs_data)
        except Exception as e:
            self.logger.warning(f"Postgres shadow write failed (save_notification_prefs): {e}")
        
        return result


class DualWriteCVVersionManager:
    """
    Dual-write CV version manager.
    Reads from Airtable, writes to both.
    """
    
    def __init__(self, airtable_manager, postgres_manager):
        self.airtable = airtable_manager
        self.postgres = postgres_manager
        self.logger = logging.getLogger(self.__class__.__name__)
    
    # =========================================================================
    # READ OPERATIONS (Airtable primary)
    # =========================================================================
    
    def get_version(self, version_id: str, user_email: str) -> Optional[Dict]:
        return self.airtable.get_version(version_id, user_email)
    
    def list_versions(self, user_email: str, **kwargs) -> List[Dict]:
        return self.airtable.list_versions(user_email, **kwargs)
    
    def get_download_url(self, version_id: str, user_email: str, **kwargs) -> Optional[str]:
        return self.airtable.get_download_url(version_id, user_email, **kwargs)
    
    def get_categories(self, user_email: str) -> List[str]:
        return self.airtable.get_categories(user_email)
    
    def get_all_tags(self, user_email: str) -> List[str]:
        return self.airtable.get_all_tags(user_email)
    
    def get_analytics(self, user_email: str) -> Dict:
        return self.airtable.get_analytics(user_email)
    
    # =========================================================================
    # WRITE OPERATIONS (Dual-write)
    # =========================================================================
    
    def create_version(self, user_email: str, file_path: str, version_name: str, **kwargs) -> Dict:
        result = self.airtable.create_version(user_email, file_path, version_name, **kwargs)
        
        try:
            self.postgres.create_version(user_email, file_path, version_name, **kwargs)
        except Exception as e:
            self.logger.warning(f"Postgres shadow write failed (create_version): {e}")
        
        return result
    
    def update_version(self, version_id: str, user_email: str, updates: Dict) -> Optional[Dict]:
        result = self.airtable.update_version(version_id, user_email, updates)
        
        try:
            self.postgres.update_version(version_id, user_email, updates)
        except Exception as e:
            self.logger.warning(f"Postgres shadow write failed (update_version): {e}")
        
        return result
    
    def archive_version(self, version_id: str, user_email: str) -> bool:
        result = self.airtable.archive_version(version_id, user_email)
        
        try:
            self.postgres.archive_version(version_id, user_email)
        except Exception as e:
            self.logger.warning(f"Postgres shadow write failed (archive_version): {e}")
        
        return result
    
    def restore_version(self, version_id: str, user_email: str) -> bool:
        result = self.airtable.restore_version(version_id, user_email)
        
        try:
            self.postgres.restore_version(version_id, user_email)
        except Exception as e:
            self.logger.warning(f"Postgres shadow write failed (restore_version): {e}")
        
        return result
    
    def delete_version(self, version_id: str, user_email: str) -> bool:
        result = self.airtable.delete_version(version_id, user_email)
        
        try:
            self.postgres.delete_version(version_id, user_email)
        except Exception as e:
            self.logger.warning(f"Postgres shadow write failed (delete_version): {e}")
        
        return result
    
    def increment_usage(self, version_id: str, user_email: str) -> bool:
        result = self.airtable.increment_usage(version_id, user_email)
        
        try:
            self.postgres.increment_usage(version_id, user_email)
        except Exception as e:
            self.logger.warning(f"Postgres shadow write failed (increment_usage): {e}")
        
        return result
    
    def increment_response(self, version_id: str, user_email: str) -> bool:
        result = self.airtable.increment_response(version_id, user_email)
        
        try:
            self.postgres.increment_response(version_id, user_email)
        except Exception as e:
            self.logger.warning(f"Postgres shadow write failed (increment_response): {e}")
        
        return result
    
    def fork_version(self, source_version_id: str, user_email: str, new_name: str, 
                     new_file_path: Optional[str] = None) -> Optional[Dict]:
        result = self.airtable.fork_version(source_version_id, user_email, new_name, new_file_path)
        
        try:
            self.postgres.fork_version(source_version_id, user_email, new_name, new_file_path)
        except Exception as e:
            self.logger.warning(f"Postgres shadow write failed (fork_version): {e}")
        
        return result

    def create_version_from_history(
        self,
        user_email: str,
        history_record: Dict[str, Any],
        version_name: Optional[str] = None,
        auto_category: Optional[str] = None,
        user_tags: Optional[List[str]] = None,
    ) -> Optional[Dict]:
        result = self.airtable.create_version_from_history(
            user_email, history_record, version_name, auto_category, user_tags
        )

        try:
            self.postgres.create_version_from_history(
                user_email, history_record, version_name, auto_category, user_tags
            )
        except Exception as e:
            self.logger.warning(f"Postgres shadow write failed (create_version_from_history): {e}")

        return result


# =============================================================================
# FACTORY FUNCTIONS
# =============================================================================

# Cached instances
_data_manager = None
_cv_version_manager = None


def get_data_manager():
    """
    Get the appropriate data manager based on STORAGE_BACKEND.
    
    Returns:
        AirtableManager, PostgresManager, or DualWriteDataManager
    """
    global _data_manager
    
    if _data_manager is not None:
        return _data_manager
    
    if STORAGE_BACKEND == "postgres":
        from data_store.postgres_manager import get_postgres_manager
        _data_manager = get_postgres_manager()
        logger.info("Storage backend: PostgreSQL (direct)")
        
    elif STORAGE_BACKEND == "dual":
        from config.settings import Config
        from data_store.airtable_manager import AirtableManager
        from data_store.postgres_manager import get_postgres_manager
        
        airtable = AirtableManager(
            Config.AIRTABLE_API_KEY,
            Config.AIRTABLE_BASE_ID,
            Config.AIRTABLE_TABLE_ID
        )
        postgres = get_postgres_manager()
        _data_manager = DualWriteDataManager(airtable, postgres)
        logger.info("Storage backend: Dual-write (Airtable primary, Postgres shadow)")
        
    else:  # "airtable" or default
        from config.settings import Config
        from data_store.airtable_manager import AirtableManager
        
        _data_manager = AirtableManager(
            Config.AIRTABLE_API_KEY,
            Config.AIRTABLE_BASE_ID,
            Config.AIRTABLE_TABLE_ID
        )
        logger.info("Storage backend: Airtable (default)")
    
    return _data_manager


def get_cv_version_manager():
    """
    Get the appropriate CV version manager based on STORAGE_BACKEND.
    
    Returns:
        CVVersionManager, PostgresCVVersionManager, or DualWriteCVVersionManager
    """
    global _cv_version_manager
    
    if _cv_version_manager is not None:
        return _cv_version_manager
    
    if STORAGE_BACKEND == "postgres":
        from data_store.postgres_manager import get_postgres_cv_version_manager
        _cv_version_manager = get_postgres_cv_version_manager()
        logger.info("CV Version backend: PostgreSQL (direct)")
        
    elif STORAGE_BACKEND == "dual":
        from data_store.cv_version_manager import get_cv_version_manager as get_airtable_cv_manager
        from data_store.postgres_manager import get_postgres_cv_version_manager
        
        airtable = get_airtable_cv_manager()
        postgres = get_postgres_cv_version_manager()
        _cv_version_manager = DualWriteCVVersionManager(airtable, postgres)
        logger.info("CV Version backend: Dual-write (Airtable primary, Postgres shadow)")
        
    else:  # "airtable" or default
        from data_store.cv_version_manager import get_cv_version_manager as get_airtable_cv_manager
        _cv_version_manager = get_airtable_cv_manager()
        logger.info("CV Version backend: Airtable (default)")
    
    return _cv_version_manager


def get_history_manager():
    """
    Get the history table manager (same as data manager for now).
    
    In Airtable, history is accessed via the same AirtableManager
    pointed at the history table. For Postgres, it's integrated.
    """
    if STORAGE_BACKEND == "airtable":
        from config.settings import Config
        from data_store.airtable_manager import AirtableManager
        return AirtableManager(
            Config.AIRTABLE_API_KEY,
            Config.AIRTABLE_BASE_ID,
            Config.AIRTABLE_TABLE_ID_HISTORY
        )
    else:
        # Postgres and dual modes use the unified manager
        return get_data_manager()


# =============================================================================
# TASK MANAGER (always uses Postgres for durability)
# =============================================================================

_task_manager = None


def get_task_manager():
    """
    Get the task manager for durable job task tracking.

    Always uses PostgreSQL for durability, regardless of STORAGE_BACKEND.
    Tasks need to survive API restarts and be queryable after page refresh.

    Falls back to file-based storage if Postgres is unavailable.
    """
    global _task_manager

    if _task_manager is not None:
        return _task_manager

    try:
        from data_store.postgres_manager import get_postgres_task_manager
        _task_manager = get_postgres_task_manager()
        logger.info("Task manager: PostgreSQL (durable)")
    except Exception as e:
        logger.warning(f"PostgreSQL task manager unavailable: {e}")
        # Fallback to file-based (for development without Postgres)
        from api.routes.jobs import FileBasedTaskManager
        _task_manager = FileBasedTaskManager()
        logger.info("Task manager: File-based (fallback)")

    return _task_manager


# =============================================================================
# CONVENIENCE EXPORTS
# =============================================================================

__all__ = [
    'STORAGE_BACKEND',
    'get_data_manager',
    'get_cv_version_manager',
    'get_history_manager',
    'get_task_manager',
    'DualWriteDataManager',
    'DualWriteCVVersionManager',
]
