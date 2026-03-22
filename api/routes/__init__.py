# API Routes
from .auth import router as auth_router
from .cv import router as cv_router
from .cv_versions import router as cv_versions_router
from .jobs import router as jobs_router
from .knowledge_base import router as knowledge_base_router
from .profile import router as profile_router
from .webhooks import router as webhooks_router

__all__ = [
    "auth_router",
    "cv_router",
    "cv_versions_router",
    "jobs_router",
    "knowledge_base_router",
    "profile_router",
    "webhooks_router",
]
