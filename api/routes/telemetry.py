"""
Telemetry routes for product analytics.
Records user events for funnel analysis and provides admin dashboards.
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request

from api.middleware.auth_middleware import get_current_user, get_optional_user
from api.schemas.auth import UserInfo
from api.schemas.telemetry import (
    ActivitySummary,
    AnalyticsDashboard,
    ErrorEvent,
    FunnelAnalytics,
    FunnelStepMetrics,
    TelemetryBatch,
    TelemetryEvent,
    TelemetryResponse,
    TopEvent,
)
from data_store.postgres_manager import get_postgres_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/telemetry", tags=["Telemetry"])


async def _record_events_async(
    events: list[TelemetryEvent],
    user_id: Optional[int],
    user_email: Optional[str],
):
    """
    Record events to database asynchronously.
    Failures are logged but never propagated to avoid breaking user flows.
    """
    pg = get_postgres_manager()
    recorded = 0
    errors = 0

    for event in events:
        try:
            query = """
                INSERT INTO product_events (
                    user_id, user_email, session_id, event_name, funnel_step,
                    entity_type, entity_id, metadata, path, referrer,
                    client_timestamp, server_timestamp
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, NOW()
                )
            """
            await pg.execute(
                query,
                user_id,
                user_email,
                event.session_id,
                event.event_name,
                event.funnel_step,
                event.entity_type,
                event.entity_id,
                event.metadata or {},
                event.path,
                event.referrer,
                event.client_timestamp,
            )
            recorded += 1
        except Exception as e:
            logger.warning(f"Failed to record telemetry event '{event.event_name}': {e}")
            errors += 1

    if recorded > 0:
        logger.debug(f"Recorded {recorded} telemetry events for user {user_id or 'anonymous'}")
    if errors > 0:
        logger.warning(f"Failed to record {errors} telemetry events")

    return recorded, errors


@router.post("/events", response_model=TelemetryResponse)
async def record_events(
    request: Request,
    batch: TelemetryBatch,
    background_tasks: BackgroundTasks,
    user: Optional[UserInfo] = Depends(get_optional_user),
):
    """
    Record telemetry events (single or batch).

    Events are recorded asynchronously to avoid blocking the user.
    Failures are logged but never returned as errors.
    """
    user_id = user.auth_user_id if user else None
    user_email = user.email if user else None

    # Schedule async recording
    background_tasks.add_task(
        _record_events_async,
        batch.events,
        user_id,
        user_email,
    )

    return TelemetryResponse(recorded=len(batch.events), errors=0)


@router.post("/event", response_model=TelemetryResponse)
async def record_single_event(
    request: Request,
    event: TelemetryEvent,
    background_tasks: BackgroundTasks,
    user: Optional[UserInfo] = Depends(get_optional_user),
):
    """
    Record a single telemetry event.
    Convenience endpoint that wraps the batch endpoint.
    """
    batch = TelemetryBatch(events=[event])
    return await record_events(request, batch, background_tasks, user)


# =============================================================================
# Admin Analytics Endpoints (require staff/superuser)
# =============================================================================

def _require_admin(user: UserInfo):
    """Check if user has admin access."""
    if not user.is_staff and not user.is_superuser:
        raise HTTPException(status_code=403, detail="Admin access required")


@router.get("/analytics/funnel", response_model=FunnelAnalytics)
async def get_funnel_analytics(
    days: int = Query(default=7, ge=1, le=90, description="Number of days to analyze"),
    user: UserInfo = Depends(get_current_user),
):
    """
    Get funnel conversion analytics for admin dashboard.
    Requires admin access.
    """
    _require_admin(user)

    pg = get_postgres_manager()
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=days)

    try:
        rows = await pg.fetch(
            "SELECT * FROM get_funnel_metrics($1, $2)",
            start_date,
            end_date,
        )

        steps = []
        prev_users = None
        for row in rows:
            conversion_rate = None
            if prev_users and prev_users > 0:
                conversion_rate = round(row["unique_users"] / prev_users * 100, 1)

            steps.append(FunnelStepMetrics(
                funnel_step=row["funnel_step"],
                event_name=row["event_name"],
                event_count=row["event_count"],
                unique_users=row["unique_users"],
                conversion_rate=conversion_rate,
            ))
            prev_users = row["unique_users"]

        # Calculate overall conversion (first to last step)
        overall_conversion = None
        if len(steps) >= 2 and steps[0].unique_users > 0:
            overall_conversion = round(steps[-1].unique_users / steps[0].unique_users * 100, 1)

        return FunnelAnalytics(
            period_start=start_date,
            period_end=end_date,
            steps=steps,
            overall_conversion=overall_conversion,
        )
    except Exception as e:
        logger.error(f"Failed to get funnel analytics: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve analytics")


@router.get("/analytics/summary", response_model=ActivitySummary)
async def get_activity_summary(
    days: int = Query(default=7, ge=1, le=90, description="Number of days to analyze"),
    user: UserInfo = Depends(get_current_user),
):
    """
    Get activity summary for admin dashboard.
    Requires admin access.
    """
    _require_admin(user)

    pg = get_postgres_manager()
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=days)

    try:
        rows = await pg.fetch(
            "SELECT * FROM get_activity_summary($1, $2)",
            start_date,
            end_date,
        )

        if not rows:
            return ActivitySummary(
                period_start=start_date,
                period_end=end_date,
                total_events=0,
                unique_users=0,
                unique_sessions=0,
                cvs_generated=0,
                cvs_downloaded=0,
                jobs_searched=0,
            )

        row = rows[0]
        download_rate = None
        if row["cvs_generated"] > 0:
            download_rate = round(row["cvs_downloaded"] / row["cvs_generated"] * 100, 1)

        return ActivitySummary(
            period_start=row["period_start"],
            period_end=row["period_end"],
            total_events=row["total_events"],
            unique_users=row["unique_users"],
            unique_sessions=row["unique_sessions"],
            cvs_generated=row["cvs_generated"],
            cvs_downloaded=row["cvs_downloaded"],
            jobs_searched=row["jobs_searched"],
            download_rate=download_rate,
        )
    except Exception as e:
        logger.error(f"Failed to get activity summary: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve analytics")


@router.get("/analytics/top-events", response_model=list[TopEvent])
async def get_top_events(
    days: int = Query(default=7, ge=1, le=90, description="Number of days to analyze"),
    limit: int = Query(default=20, ge=1, le=100, description="Max events to return"),
    user: UserInfo = Depends(get_current_user),
):
    """
    Get top events by volume for admin dashboard.
    Requires admin access.
    """
    _require_admin(user)

    pg = get_postgres_manager()
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=days)

    try:
        rows = await pg.fetch(
            "SELECT * FROM get_top_events($1, $2, $3)",
            start_date,
            end_date,
            limit,
        )

        return [
            TopEvent(
                event_name=row["event_name"],
                event_count=row["event_count"],
                unique_users=row["unique_users"],
                unique_sessions=row["unique_sessions"],
            )
            for row in rows
        ]
    except Exception as e:
        logger.error(f"Failed to get top events: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve analytics")


@router.get("/analytics/errors", response_model=list[ErrorEvent])
async def get_error_events(
    days: int = Query(default=7, ge=1, le=90, description="Number of days to analyze"),
    limit: int = Query(default=20, ge=1, le=100, description="Max errors to return"),
    user: UserInfo = Depends(get_current_user),
):
    """
    Get error events breakdown for admin dashboard.
    Requires admin access.
    """
    _require_admin(user)

    pg = get_postgres_manager()
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=days)

    try:
        rows = await pg.fetch(
            "SELECT * FROM get_error_events($1, $2, $3)",
            start_date,
            end_date,
            limit,
        )

        return [
            ErrorEvent(
                event_name=row["event_name"],
                error_count=row["error_count"],
                affected_users=row["affected_users"],
                latest_occurrence=row["latest_occurrence"],
                sample_metadata=row["sample_metadata"],
            )
            for row in rows
        ]
    except Exception as e:
        logger.error(f"Failed to get error events: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve analytics")


@router.get("/analytics/dashboard", response_model=AnalyticsDashboard)
async def get_analytics_dashboard(
    days: int = Query(default=7, ge=1, le=90, description="Number of days to analyze"),
    user: UserInfo = Depends(get_current_user),
):
    """
    Get complete analytics dashboard for admins.
    Combines summary, funnel, top events, and errors in one call.
    Requires admin access.
    """
    _require_admin(user)

    pg = get_postgres_manager()
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=days)

    try:
        # Fetch all data in parallel using multiple queries
        summary_rows = await pg.fetch("SELECT * FROM get_activity_summary($1, $2)", start_date, end_date)
        funnel_rows = await pg.fetch("SELECT * FROM get_funnel_metrics($1, $2)", start_date, end_date)
        top_rows = await pg.fetch("SELECT * FROM get_top_events($1, $2, $3)", start_date, end_date, 20)
        error_rows = await pg.fetch("SELECT * FROM get_error_events($1, $2, $3)", start_date, end_date, 10)

        # Build summary
        if summary_rows:
            row = summary_rows[0]
            download_rate = None
            if row["cvs_generated"] > 0:
                download_rate = round(row["cvs_downloaded"] / row["cvs_generated"] * 100, 1)
            summary = ActivitySummary(
                period_start=row["period_start"],
                period_end=row["period_end"],
                total_events=row["total_events"],
                unique_users=row["unique_users"],
                unique_sessions=row["unique_sessions"],
                cvs_generated=row["cvs_generated"],
                cvs_downloaded=row["cvs_downloaded"],
                jobs_searched=row["jobs_searched"],
                download_rate=download_rate,
            )
        else:
            summary = ActivitySummary(
                period_start=start_date,
                period_end=end_date,
                total_events=0,
                unique_users=0,
                unique_sessions=0,
                cvs_generated=0,
                cvs_downloaded=0,
                jobs_searched=0,
            )

        # Build funnel
        funnel = []
        prev_users = None
        for row in funnel_rows:
            conversion_rate = None
            if prev_users and prev_users > 0:
                conversion_rate = round(row["unique_users"] / prev_users * 100, 1)
            funnel.append(FunnelStepMetrics(
                funnel_step=row["funnel_step"],
                event_name=row["event_name"],
                event_count=row["event_count"],
                unique_users=row["unique_users"],
                conversion_rate=conversion_rate,
            ))
            prev_users = row["unique_users"]

        # Build top events
        top_events = [
            TopEvent(
                event_name=row["event_name"],
                event_count=row["event_count"],
                unique_users=row["unique_users"],
                unique_sessions=row["unique_sessions"],
            )
            for row in top_rows
        ]

        # Build error events
        error_events = [
            ErrorEvent(
                event_name=row["event_name"],
                error_count=row["error_count"],
                affected_users=row["affected_users"],
                latest_occurrence=row["latest_occurrence"],
                sample_metadata=row["sample_metadata"],
            )
            for row in error_rows
        ]

        return AnalyticsDashboard(
            summary=summary,
            funnel=funnel,
            top_events=top_events,
            error_events=error_events,
        )
    except Exception as e:
        logger.error(f"Failed to get analytics dashboard: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve analytics")
