"""
WinningCV FastAPI Application
REST API backend for the React frontend.
"""
import os
import logging
from contextlib import asynccontextmanager
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.routes import auth_router, cv_router, cv_versions_router, jobs_router, profile_router
from api.middleware.auth_middleware import auth_middleware
from utils.logger import setup_logger

# Configure logging
setup_logger(log_file="logs/api.log", level=logging.DEBUG)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    logger.info("Starting WinningCV API server")
    yield
    # Cleanup
    await auth_middleware.close()
    logger.info("Shutting down WinningCV API server")


# Create FastAPI app
app = FastAPI(
    title="WinningCV API",
    description="REST API for AI-powered CV tailoring and job matching",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan
)

# CORS configuration
# Allow requests from frontend origins
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",  # Vite dev server
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
    "https://winningcv.jackhui.com.au",
    "https://cv.jackhui.com.au",
]

# Add additional origins from environment
extra_origins = os.getenv("CORS_ORIGINS", "").split(",")
ALLOWED_ORIGINS.extend([o.strip() for o in extra_origins if o.strip()])

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,  # Important for cookies
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal error occurred"}
    )


# Include routers with /api/v1 prefix
app.include_router(auth_router, prefix="/api/v1")
app.include_router(cv_router, prefix="/api/v1")
app.include_router(cv_versions_router, prefix="/api/v1")
app.include_router(jobs_router, prefix="/api/v1")
app.include_router(profile_router, prefix="/api/v1")


# Health check endpoint
@app.get("/api/health")
async def health_check():
    """Health check endpoint for monitoring"""
    return {
        "status": "healthy",
        "service": "winningcv-api",
        "version": "1.0.0"
    }


@app.get("/api/v1")
async def api_root():
    """API root - returns available endpoints"""
    return {
        "message": "WinningCV API",
        "version": "1.0.0",
        "endpoints": {
            "auth": "/api/v1/auth",
            "cv": "/api/v1/cv",
            "cv_versions": "/api/v1/cv/versions",
            "jobs": "/api/v1/jobs",
            "profile": "/api/v1/profile",
            "docs": "/api/docs"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
