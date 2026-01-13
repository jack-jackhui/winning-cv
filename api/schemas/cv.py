from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class CVGenerateRequest(BaseModel):
    """Request to generate a tailored CV"""
    job_description: str = Field(..., min_length=50, description="Job description text")
    instructions: Optional[str] = Field(None, description="Special instructions for CV generation")


class CVGenerateResponse(BaseModel):
    """Response from CV generation"""
    cv_markdown: str
    cv_pdf_url: str  # Presigned MinIO URL for PDF download
    cv_docx_url: Optional[str] = None  # Presigned MinIO URL for DOCX download
    job_title: str
    preview_html: Optional[str] = None
    version_id: Optional[str] = None  # New: reference to saved version
    history_id: Optional[str] = None  # Airtable record ID for analysis lookup


class CVUploadResponse(BaseModel):
    """Response from CV file upload"""
    path: str
    url: Optional[str] = None
    filename: str
    version_id: Optional[str] = None  # New: reference to saved version


class CVHistoryItem(BaseModel):
    """Single item in CV generation history"""
    id: str
    job_title: str
    created_at: datetime
    cv_pdf_url: str
    job_description: Optional[str] = None
    instructions: Optional[str] = None


class CVHistoryResponse(BaseModel):
    """List of CV history items"""
    items: List[CVHistoryItem]
    total: int


# ──────────────────────────────────────────────────────────
# CV VERSION MANAGEMENT SCHEMAS
# ──────────────────────────────────────────────────────────

class CVVersionBase(BaseModel):
    """Base schema for CV version data"""
    version_name: str = Field(..., min_length=1, max_length=100, description="Human-readable version name")
    auto_category: Optional[str] = Field(None, max_length=50, description="Auto-detected role category")
    user_tags: Optional[List[str]] = Field(default_factory=list, description="User-defined tags")


class CVVersionCreate(CVVersionBase):
    """Request to create a new CV version (file uploaded separately)"""
    source_job_link: Optional[str] = Field(None, description="Job this CV was generated for")
    source_job_title: Optional[str] = Field(None, description="Title of the source job")
    parent_version_id: Optional[str] = Field(None, description="Parent version if forked")


class CVVersionUpdate(BaseModel):
    """Request to update CV version metadata"""
    version_name: Optional[str] = Field(None, min_length=1, max_length=100)
    auto_category: Optional[str] = Field(None, max_length=50)
    user_tags: Optional[List[str]] = None
    is_archived: Optional[bool] = None


class CVVersionResponse(CVVersionBase):
    """Response containing CV version details"""
    id: str
    version_id: str
    user_email: str
    storage_path: str
    parent_version_id: Optional[str] = None
    is_archived: bool = False
    usage_count: int = 0
    response_count: int = 0
    source_job_link: Optional[str] = None
    source_job_title: Optional[str] = None
    file_size: int = 0
    content_hash: Optional[str] = None
    created_at: datetime
    download_url: Optional[str] = None  # Presigned URL, populated on request


class CVVersionListResponse(BaseModel):
    """Paginated list of CV versions"""
    items: List[CVVersionResponse]
    total: int
    categories: List[str] = []
    tags: List[str] = []


class CVVersionForkRequest(BaseModel):
    """Request to fork an existing CV version"""
    new_name: str = Field(..., min_length=1, max_length=100, description="Name for the forked version")


class CVVersionMatchRequest(BaseModel):
    """Request to find matching CV versions for a job"""
    job_description: str = Field(..., min_length=50, description="Job description to match against")
    job_title: Optional[str] = Field(None, description="Job title for better matching")
    company_name: Optional[str] = Field(None, description="Company name for industry matching")
    limit: int = Field(default=3, ge=1, le=10, description="Max suggestions to return")


class CVVersionMatchScore(BaseModel):
    """Match score for a CV version against a job"""
    version_id: str
    version_name: str
    auto_category: Optional[str]
    overall_score: float = Field(..., ge=0, le=100, description="Overall match percentage")
    role_similarity: float = Field(..., ge=0, le=100, description="Role title similarity")
    skills_overlap: float = Field(..., ge=0, le=100, description="Skills overlap percentage")
    usage_count: int
    response_rate: float = Field(default=0, ge=0, le=100, description="Historical response rate")
    download_url: Optional[str] = None
    reasons: List[str] = Field(default_factory=list, description="Why this version matches")


class CVVersionMatchResponse(BaseModel):
    """Response containing CV version suggestions for a job"""
    suggestions: List[CVVersionMatchScore]
    job_analysis: dict = Field(default_factory=dict, description="Analysis of job requirements")


class CVVersionAnalyticsResponse(BaseModel):
    """Analytics summary for user's CV versions"""
    total_versions: int
    active_versions: int
    archived_versions: int
    total_usage: int
    total_responses: int
    overall_response_rate: float
    top_performing: List[dict]
    categories: List[str]
    tags: List[str]


class CVVersionBulkActionRequest(BaseModel):
    """Request for bulk operations on CV versions"""
    version_ids: List[str] = Field(..., min_items=1, max_items=50)
    action: str = Field(..., description="Action: archive, restore, delete")


class CVVersionBulkActionResponse(BaseModel):
    """Response from bulk operation"""
    success_count: int
    failed_count: int
    failed_ids: List[str] = []


# ──────────────────────────────────────────────────────────
# CV-JD FIT ANALYSIS SCHEMAS
# ──────────────────────────────────────────────────────────

class KeywordMatchSchema(BaseModel):
    """Keyword match analysis"""
    score: int = Field(..., ge=0, le=100)
    matched: List[str] = []
    missing: List[str] = []
    density_assessment: str = "Good"


class TechnicalSkillsSchema(BaseModel):
    """Technical skills breakdown"""
    matched: List[str] = []
    partial: List[str] = []
    missing: List[str] = []


class SoftSkillsSchema(BaseModel):
    """Soft skills analysis"""
    matched: List[str] = []
    demonstrated: List[str] = []


class SkillsCoverageSchema(BaseModel):
    """Skills coverage analysis"""
    score: int = Field(..., ge=0, le=100)
    technical_skills: TechnicalSkillsSchema
    soft_skills: SoftSkillsSchema


class ExperienceRelevanceSchema(BaseModel):
    """Experience relevance analysis"""
    score: int = Field(..., ge=0, le=100)
    aligned_roles: List[str] = []
    relevant_achievements: List[str] = []
    years_alignment: str = ""


class ATSOptimizationSchema(BaseModel):
    """ATS optimization analysis"""
    score: int = Field(..., ge=0, le=100)
    format_check: bool = True
    keyword_density: str = "Good"
    section_structure: str = "Clear"
    recommendations: List[str] = []


class GapAnalysisSchema(BaseModel):
    """Gap analysis"""
    critical_gaps: List[str] = []
    minor_gaps: List[str] = []
    mitigation_suggestions: List[str] = []


class TalkingPointsSchema(BaseModel):
    """Interview talking points"""
    strengths_to_highlight: List[str] = []
    questions_to_prepare: List[str] = []
    stories_to_ready: List[str] = []


class CVAnalysisResponse(BaseModel):
    """Complete CV-JD fit analysis response"""
    status: str = Field(..., description="pending | ready | failed")
    overall_score: Optional[int] = Field(None, ge=0, le=100)
    summary: Optional[str] = None
    keyword_match: Optional[KeywordMatchSchema] = None
    skills_coverage: Optional[SkillsCoverageSchema] = None
    experience_relevance: Optional[ExperienceRelevanceSchema] = None
    ats_optimization: Optional[ATSOptimizationSchema] = None
    gap_analysis: Optional[GapAnalysisSchema] = None
    talking_points: Optional[TalkingPointsSchema] = None
    error: Optional[str] = None
