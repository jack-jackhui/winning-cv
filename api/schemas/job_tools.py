"""
Pydantic schemas for job tools API endpoints.
"""
from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List, Literal
from enum import Enum


# ============== Enums ==============

class JobSource(str, Enum):
    LINKEDIN = "linkedin"
    SEEK = "seek"


class MatchRecommendation(str, Enum):
    STRONG_MATCH = "STRONG_MATCH"
    GOOD_MATCH = "GOOD_MATCH"
    WEAK_MATCH = "WEAK_MATCH"
    NO_MATCH = "NO_MATCH"


class AnalysisRecommendation(str, Enum):
    APPLY = "APPLY"
    CONSIDER = "CONSIDER"
    SKIP = "SKIP"


class CVFormat(str, Enum):
    MARKDOWN = "markdown"
    TEXT = "text"
    JSON = "json"


class CVTone(str, Enum):
    PROFESSIONAL = "professional"
    CREATIVE = "creative"
    TECHNICAL = "technical"


# ============== Job Search ==============

class JobSearchRequest(BaseModel):
    """Request schema for job search endpoint"""
    keywords: List[str] = Field(
        ...,
        min_length=1,
        description="Keywords for job search (e.g., ['AI', 'Digital Transformation'])"
    )
    location: str = Field(
        ...,
        min_length=2,
        description="Job location (e.g., 'Melbourne')"
    )
    sources: Optional[List[JobSource]] = Field(
        default=None,
        description="Job sources to search (default: both linkedin and seek)"
    )
    limit: Optional[int] = Field(
        default=20,
        ge=1,
        le=100,
        description="Maximum number of jobs to return"
    )


class JobItem(BaseModel):
    """Individual job item from search results"""
    id: str
    title: str
    company: str
    location: Optional[str] = None
    url: str
    source: JobSource
    posted_date: Optional[str] = None
    salary: Optional[str] = None
    description: Optional[str] = None


class JobSearchResponse(BaseModel):
    """Response schema for job search endpoint"""
    jobs: List[JobItem]
    total: int


# ============== Job Matching ==============

class JobMatchRequest(BaseModel):
    """Request schema for job matching endpoint"""
    jobs: List[JobItem] = Field(
        ...,
        min_length=1,
        description="Array of job objects to match against CV"
    )
    cv_id: Optional[str] = Field(
        default=None,
        description="ID of the user's CV to use for matching"
    )
    cv_text: Optional[str] = Field(
        default=None,
        description="Raw CV text (alternative to cv_id)"
    )


class JobMatchResult(BaseModel):
    """Individual job match result"""
    job: JobItem
    score: float = Field(ge=0, le=10)
    strengths: List[str]
    gaps: List[str]
    recommendation: MatchRecommendation


class JobMatchResponse(BaseModel):
    """Response schema for job matching endpoint"""
    matches: List[JobMatchResult]


# ============== Job Analysis ==============

class JobAnalyzeRequest(BaseModel):
    """Request schema for job analysis endpoint"""
    job_url: Optional[str] = Field(
        default=None,
        description="URL of job posting to analyze"
    )
    job_description: Optional[str] = Field(
        default=None,
        description="Job description text (alternative to job_url)"
    )
    cv_id: Optional[str] = Field(
        default=None,
        description="ID of user's CV for analysis"
    )
    cv_text: Optional[str] = Field(
        default=None,
        description="Raw CV text (alternative to cv_id)"
    )


class StrengthDetail(BaseModel):
    """Detailed strength assessment"""
    area: str
    evidence: str
    relevance: Literal["high", "medium", "low"]


class GapDetail(BaseModel):
    """Detailed gap assessment"""
    area: str
    severity: Literal["critical", "moderate", "minor"]
    mitigation: str


class CoverLetterAngle(BaseModel):
    """Cover letter angle suggestion"""
    angle: str
    key_points: List[str]


class InterviewPrep(BaseModel):
    """Interview preparation suggestions"""
    likely_questions: List[str]
    talking_points: List[str]


class JobAnalyzeResponse(BaseModel):
    """Response schema for job analysis endpoint"""
    score: float = Field(ge=0, le=10)
    recommendation: AnalysisRecommendation
    fit_assessment: str
    strengths: List[StrengthDetail]
    gaps: List[GapDetail]
    red_flags: List[str]
    cover_letter_angles: List[CoverLetterAngle]
    interview_prep: InterviewPrep


# ============== CV Generation ==============

class CVGenerateRequest(BaseModel):
    """Request schema for CV generation endpoint"""
    job_url: Optional[str] = Field(
        default=None,
        description="URL of job posting to tailor CV for"
    )
    job_description: Optional[str] = Field(
        default=None,
        description="Job description text (alternative to job_url)"
    )
    cv_id: Optional[str] = Field(
        default=None,
        description="ID of source CV to tailor"
    )
    format: Optional[CVFormat] = Field(
        default=CVFormat.MARKDOWN,
        description="Output format (markdown, text, or json)"
    )
    tone: Optional[CVTone] = Field(
        default=CVTone.PROFESSIONAL,
        description="CV tone (professional, creative, or technical)"
    )


class CVGenerateResponse(BaseModel):
    """Response schema for CV generation endpoint"""
    cv: str = Field(description="Generated CV content")
    format: CVFormat
    keywords_emphasized: List[str]
    changes_made: List[str]
