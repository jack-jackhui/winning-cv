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
from datetime import date
from typing import Dict, Optional

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


class ShadowWriteError(RuntimeError):
    """Raised when a required PostgreSQL shadow write is not persisted."""


class _DualWriteProxy:
    """
    Shared base for dual-write managers.

    Reads are delegated to the Airtable primary only. Writes fan out to
    PostgreSQL as a shadow, with a configurable strictness policy.
    """

    # Shadow-write calls that must persist or raise (vs. lenient log-only)
    _STRICT = frozenset()

    def __init__(self, airtable_manager, postgres_manager):
        self.airtable = airtable_manager
        self.postgres = postgres_manager
        self.logger = logging.getLogger(self.__class__.__name__)

    def _lenient_shadow(self, method: str, *args, **kwargs):
        """Fire a shadow write, logging (not raising) on failure."""
        try:
            getattr(self.postgres, method)(*args, **kwargs)
        except Exception as e:  # pragma: no cover - defensive
            self.logger.warning(f"Postgres shadow write failed ({method}): {e}")

    def _strict_shadow(self, method: str, primary_result, *args, **kwargs):
        """
        Fire a shadow write that must persist or raise ``ShadowWriteError``.
        Returns the primary result; raises if the shadow is unpersisted.
        """
        if primary_result is None:
            return None
        try:
            shadow_result = getattr(self.postgres, method)(*args, **kwargs)
        except Exception as e:
            self.logger.warning(f"Postgres shadow write failed ({method}): {e}")
            raise ShadowWriteError(f"Postgres shadow {method} failed") from e
        if shadow_result is None:
            self.logger.warning(f"Postgres shadow write missed ({method})")
            raise ShadowWriteError(f"Postgres shadow {method} did not persist")
        return primary_result

    def _shadow(self, method: str, primary_result, *args, **kwargs):
        """Dispatch shadow write according to strictness policy."""
        if method in self._STRICT:
            return self._strict_shadow(method, primary_result, *args, **kwargs)
        self._lenient_shadow(method, *args, **kwargs)
        return primary_result

    def __getattr__(self, name: str):
        """
        Fallback delegation: forward any read/write to the Airtable primary,
        fanning writes out to PostgreSQL shadow.
        """
        if name.startswith("_") or name in ("airtable", "postgres", "logger"):
            raise AttributeError(name)
        primary = getattr(self.airtable, name)

        def wrapped(*args, **kwargs):
            result = primary(*args, **kwargs)
            if _is_write(name):
                return self._shadow(name, result, *args, **kwargs)
            return result

        return wrapped


def _is_write(name: str) -> bool:
    """Heuristic: treat mutation-style method names as writes."""
    return name.startswith(("create_", "update_", "save_", "archive_", "restore_", "delete_", "increment_", "fork_"))


class DualWriteDataManager(_DualWriteProxy):
    """Dual-write for jobs/history/notifications. Reads from Airtable (primary)."""

    _STRICT = frozenset(["create_job_record", "update_cv_info", "update_application_status"])

    def update_application_status(
        self,
        job_id: str,
        user_email: str,
        application_status: str,
        application_notes: Optional[str] = None,
        next_action_at: Optional[date] = None,
        update_next_action: bool = False,
    ) -> Optional[Dict]:
        result = self.airtable.update_application_status(
            job_id,
            user_email,
            application_status,
            application_notes,
            next_action_at,
            update_next_action,
        )
        if result is None:
            return None
        return self._strict_shadow(
            "update_application_status",
            result,
            job_id,
            user_email,
            application_status,
            application_notes,
            next_action_at,
            update_next_action,
            job_link=result.get("fields", {}).get("Job Link"),
        )


class DualWriteCVVersionManager(_DualWriteProxy):
    """
    Dual-write CV version manager.

    Reads from Airtable (primary); all writes fan out to PostgreSQL shadow
    with a lenient log-on-failure policy. Handled by ``_DualWriteProxy``.
    """


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
        from config.settings_v2 import Config
        from data_store.airtable_manager import AirtableManager
        from data_store.postgres_manager import get_postgres_manager

        airtable = AirtableManager(Config.AIRTABLE_API_KEY, Config.AIRTABLE_BASE_ID, Config.AIRTABLE_TABLE_ID)
        postgres = get_postgres_manager()
        _data_manager = DualWriteDataManager(airtable, postgres)
        logger.info("Storage backend: Dual-write (Airtable primary, Postgres shadow)")

    else:  # "airtable" or default
        from config.settings_v2 import Config
        from data_store.airtable_manager import AirtableManager

        _data_manager = AirtableManager(Config.AIRTABLE_API_KEY, Config.AIRTABLE_BASE_ID, Config.AIRTABLE_TABLE_ID)
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
        from config.settings_v2 import Config
        from data_store.airtable_manager import AirtableManager

        return AirtableManager(Config.AIRTABLE_API_KEY, Config.AIRTABLE_BASE_ID, Config.AIRTABLE_TABLE_ID_HISTORY)
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
    "STORAGE_BACKEND",
    "get_data_manager",
    "get_cv_version_manager",
    "get_history_manager",
    "get_task_manager",
    "DualWriteDataManager",
    "DualWriteCVVersionManager",
]
