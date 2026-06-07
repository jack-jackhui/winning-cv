"""
Health check utilities for WinningCV API.

Provides comprehensive health checks for all external dependencies:
- PostgreSQL database
- MinIO object storage
- Azure OpenAI service
- LinkedIn cookie status
"""
import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def check_postgres_health() -> Dict[str, Any]:
    """Check PostgreSQL database connectivity and basic operations."""
    try:
        from data_store.postgres_manager import get_postgres_manager
        mgr = get_postgres_manager()

        # Test connection with a simple query
        with mgr.get_cursor() as cursor:
            cursor.execute("SELECT 1 as health_check, NOW() as server_time")
            row = cursor.fetchone()

        return {
            "status": "healthy",
            "connected": True,
            "server_time": row["server_time"].isoformat() if row else None,
        }
    except ImportError:
        return {
            "status": "unavailable",
            "connected": False,
            "error": "PostgreSQL manager not available",
        }
    except Exception as e:
        logger.warning(f"PostgreSQL health check failed: {e}")
        return {
            "status": "unhealthy",
            "connected": False,
            "error": str(e),
        }


def check_minio_health() -> Dict[str, Any]:
    """Check MinIO object storage connectivity."""
    try:
        from utils.minio_storage import get_minio_storage
        storage = get_minio_storage()

        # Check if bucket exists (lightweight operation)
        bucket_exists = storage.client.bucket_exists(storage.bucket_name)

        return {
            "status": "healthy" if bucket_exists else "degraded",
            "connected": True,
            "bucket": storage.bucket_name,
            "bucket_exists": bucket_exists,
        }
    except ImportError:
        return {
            "status": "unavailable",
            "connected": False,
            "error": "MinIO storage not available",
        }
    except Exception as e:
        logger.warning(f"MinIO health check failed: {e}")
        return {
            "status": "unhealthy",
            "connected": False,
            "error": str(e),
        }


def check_azure_openai_health() -> Dict[str, Any]:
    """Check Azure OpenAI service configuration and basic connectivity."""
    try:
        from config.settings import Config

        # Check configuration exists
        endpoint = getattr(Config, 'AZURE_AI_ENDPOINT', None) or os.getenv('AZURE_AI_ENDPOINT')
        api_key = getattr(Config, 'AZURE_AI_API_KEY', None) or os.getenv('AZURE_AI_API_KEY')
        deployment = getattr(Config, 'AZURE_DEPLOYMENT', None) or os.getenv('AZURE_DEPLOYMENT')

        if not all([endpoint, api_key, deployment]):
            missing = []
            if not endpoint:
                missing.append("AZURE_AI_ENDPOINT")
            if not api_key:
                missing.append("AZURE_AI_API_KEY")
            if not deployment:
                missing.append("AZURE_DEPLOYMENT")

            return {
                "status": "misconfigured",
                "configured": False,
                "missing": missing,
            }

        # Configuration exists - we don't actually call the API to avoid costs
        return {
            "status": "configured",
            "configured": True,
            "endpoint": endpoint[:30] + "..." if len(endpoint) > 30 else endpoint,
            "deployment": deployment,
        }
    except Exception as e:
        logger.warning(f"Azure OpenAI health check failed: {e}")
        return {
            "status": "error",
            "configured": False,
            "error": str(e),
        }


def check_linkedin_cookie_health() -> Dict[str, Any]:
    """Check LinkedIn cookie/session status."""
    try:
        from job_sources.linkedin_cookie_health import check_cookie_health

        health = check_cookie_health()

        return {
            "status": health["status"].value,
            "age_days": health["age_days"],
            "needs_refresh": health["needs_refresh"],
            "session_valid": health.get("session_valid"),
            "message": health["message"],
        }
    except ImportError:
        return {
            "status": "unavailable",
            "message": "LinkedIn cookie health module not available",
        }
    except Exception as e:
        logger.warning(f"LinkedIn cookie health check failed: {e}")
        return {
            "status": "error",
            "error": str(e),
        }


def check_auth_service_health() -> Dict[str, Any]:
    """Check auth service configuration."""
    try:
        from config.settings import Config

        oauth_provider = getattr(Config, 'OAUTH_PROVIDER', None) or os.getenv('OAUTH_PROVIDER', 'keycloak')
        auth_url = None

        if oauth_provider == 'keycloak':
            auth_url = getattr(Config, 'KEYCLOAK_URL', None) or os.getenv('KEYCLOAK_URL')
        elif oauth_provider == 'auth0':
            auth_url = getattr(Config, 'AUTH0_DOMAIN', None) or os.getenv('AUTH0_DOMAIN')

        if not auth_url:
            return {
                "status": "misconfigured",
                "provider": oauth_provider,
                "configured": False,
                "error": f"No auth URL configured for {oauth_provider}",
            }

        return {
            "status": "configured",
            "provider": oauth_provider,
            "configured": True,
        }
    except Exception as e:
        logger.warning(f"Auth service health check failed: {e}")
        return {
            "status": "error",
            "configured": False,
            "error": str(e),
        }


def get_comprehensive_health() -> Dict[str, Any]:
    """
    Get comprehensive health status of all services.

    Returns a summary with individual component statuses.
    """
    checks = {
        "postgres": check_postgres_health(),
        "minio": check_minio_health(),
        "azure_openai": check_azure_openai_health(),
        "linkedin": check_linkedin_cookie_health(),
        "auth": check_auth_service_health(),
    }

    # Determine overall status
    statuses = [c.get("status", "unknown") for c in checks.values()]

    if all(s in ("healthy", "configured") for s in statuses):
        overall = "healthy"
    elif any(s == "unhealthy" for s in statuses):
        overall = "unhealthy"
    elif any(s in ("degraded", "misconfigured", "error") for s in statuses):
        overall = "degraded"
    else:
        overall = "unknown"

    return {
        "status": overall,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "service": "winningcv-api",
        "version": "1.0.0",
        "components": checks,
    }
