"""
Pydantic schemas for product telemetry API.
"""
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class TelemetryEvent(BaseModel):
    """Single telemetry event from frontend."""
    event_name: str = Field(..., max_length=100, description="Event name (e.g. 'cv_upload')")
    funnel_step: Optional[int] = Field(None, ge=1, le=20, description="Funnel step number")
    entity_type: Optional[str] = Field(None, max_length=50, description="Entity type (e.g. 'cv', 'job')")
    entity_id: Optional[str] = Field(None, max_length=100, description="Entity identifier")
    metadata: Optional[dict[str, Any]] = Field(default_factory=dict, description="Additional event data")
    path: Optional[str] = Field(None, max_length=500, description="URL path")
    referrer: Optional[str] = Field(None, max_length=500, description="Referrer URL")
    client_timestamp: Optional[datetime] = Field(None, description="Client-side timestamp")
    session_id: Optional[str] = Field(None, max_length=64, description="Browser session ID")


class TelemetryBatch(BaseModel):
    """Batch of telemetry events."""
    events: list[TelemetryEvent] = Field(..., max_length=50, description="List of events (max 50)")


class TelemetryResponse(BaseModel):
    """Response after recording events."""
    recorded: int = Field(..., description="Number of events recorded")
    errors: int = Field(default=0, description="Number of events that failed")


class FunnelStepMetrics(BaseModel):
    """Metrics for a single funnel step."""
    funnel_step: int
    event_name: str
    event_count: int
    unique_users: int
    conversion_rate: Optional[float] = None  # Calculated: (this step users / previous step users)


class FunnelAnalytics(BaseModel):
    """Complete funnel analytics response."""
    period_start: datetime
    period_end: datetime
    steps: list[FunnelStepMetrics]
    overall_conversion: Optional[float] = None  # First to last step


class TopEvent(BaseModel):
    """Aggregated event metrics."""
    event_name: str
    event_count: int
    unique_users: int
    unique_sessions: int


class ErrorEvent(BaseModel):
    """Error event summary."""
    event_name: str
    error_count: int
    affected_users: int
    latest_occurrence: datetime
    sample_metadata: Optional[dict[str, Any]] = None


class ActivitySummary(BaseModel):
    """Activity summary for a period."""
    period_start: datetime
    period_end: datetime
    total_events: int
    unique_users: int
    unique_sessions: int
    cvs_generated: int
    cvs_downloaded: int
    jobs_searched: int
    download_rate: Optional[float] = None  # downloaded / generated


class AnalyticsDashboard(BaseModel):
    """Complete analytics dashboard response."""
    summary: ActivitySummary
    funnel: list[FunnelStepMetrics]
    top_events: list[TopEvent]
    error_events: list[ErrorEvent]
