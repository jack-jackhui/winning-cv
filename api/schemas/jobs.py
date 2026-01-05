from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List
from datetime import datetime
from enum import Enum


class SearchStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class JobConfigRequest(BaseModel):
    """Job search configuration"""
    search_keywords: str = Field(..., min_length=2, description="Keywords for job search")
    seek_category: str = Field(default="information communication technology")
    seek_salaryrange: Optional[str] = None
    seek_salarytype: str = Field(default="annual")
    search_term: str = Field(..., description="Indeed/Glassdoor search terms")
    google_term: str = Field(..., description="Google custom search terms")
    location: str = Field(..., description="Job location")
    max_jobs: int = Field(default=10, ge=1, le=50)
    hours_old: int = Field(default=168, ge=24, le=720)
    results_wanted: int = Field(default=10, ge=1, le=50)
    country: str = Field(default="Australia")


class JobConfigResponse(BaseModel):
    """Saved job search configuration"""
    user_email: str
    base_cv_path: Optional[str] = None
    base_cv_link: Optional[str] = None
    linkedin_job_url: Optional[str] = None
    seek_job_url: Optional[str] = None
    max_jobs_to_scrape: int = 10
    additional_search_term: Optional[str] = None
    google_search_term: Optional[str] = None
    location: str = "Melbourne, VIC"
    hours_old: int = 168
    results_wanted: int = 10
    country: str = "Australia"


class SearchTaskResponse(BaseModel):
    """Response when starting a job search"""
    task_id: str
    status: SearchStatus = SearchStatus.PENDING
    message: str = "Search task created"


class SearchStatusResponse(BaseModel):
    """Status of a running search task"""
    task_id: str
    status: SearchStatus
    progress: int = Field(default=0, ge=0, le=100)
    message: str
    results_count: Optional[int] = None


class JobResult(BaseModel):
    """Single job search result"""
    id: str
    job_title: str
    company: str
    location: Optional[str] = None
    score: float = Field(ge=0, le=10)
    cv_link: Optional[str] = None
    job_link: str
    posted_date: Optional[str] = None
    description: Optional[str] = None
    match_reasons: Optional[List[str]] = None
    suggestions: Optional[List[str]] = None


class JobResultsResponse(BaseModel):
    """List of job search results"""
    items: List[JobResult]
    total: int
