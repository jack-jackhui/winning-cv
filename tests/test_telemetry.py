"""
Tests for product telemetry API endpoints.
"""
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from api.schemas.telemetry import (
    ActivitySummary,
    FunnelStepMetrics,
    TelemetryBatch,
    TelemetryEvent,
    TelemetryResponse,
)


class TestTelemetrySchemas:
    """Test Pydantic schemas for telemetry."""

    def test_telemetry_event_minimal(self):
        """Test TelemetryEvent with minimal required fields."""
        event = TelemetryEvent(event_name="test_event")
        assert event.event_name == "test_event"
        assert event.funnel_step is None
        assert event.metadata == {}

    def test_telemetry_event_full(self):
        """Test TelemetryEvent with all fields."""
        event = TelemetryEvent(
            event_name="cv_upload",
            funnel_step=2,
            entity_type="cv",
            entity_id="cv_123",
            metadata={"source": "upload"},
            path="/generate",
            referrer="/dashboard",
            client_timestamp=datetime.now(timezone.utc),
            session_id="session_abc123",
        )
        assert event.event_name == "cv_upload"
        assert event.funnel_step == 2
        assert event.entity_type == "cv"
        assert event.entity_id == "cv_123"
        assert event.metadata == {"source": "upload"}

    def test_telemetry_event_funnel_step_validation(self):
        """Test funnel_step must be between 1 and 20."""
        # Valid steps
        event = TelemetryEvent(event_name="test", funnel_step=1)
        assert event.funnel_step == 1

        event = TelemetryEvent(event_name="test", funnel_step=20)
        assert event.funnel_step == 20

        # Invalid steps
        with pytest.raises(ValueError):
            TelemetryEvent(event_name="test", funnel_step=0)

        with pytest.raises(ValueError):
            TelemetryEvent(event_name="test", funnel_step=21)

    def test_telemetry_batch(self):
        """Test TelemetryBatch with multiple events."""
        events = [
            TelemetryEvent(event_name="event1"),
            TelemetryEvent(event_name="event2", funnel_step=3),
        ]
        batch = TelemetryBatch(events=events)
        assert len(batch.events) == 2

    def test_telemetry_batch_max_length(self):
        """Test TelemetryBatch enforces max 50 events."""
        events = [TelemetryEvent(event_name=f"event_{i}") for i in range(50)]
        batch = TelemetryBatch(events=events)
        assert len(batch.events) == 50

        # Over limit
        events = [TelemetryEvent(event_name=f"event_{i}") for i in range(51)]
        with pytest.raises(ValueError):
            TelemetryBatch(events=events)

    def test_telemetry_response(self):
        """Test TelemetryResponse schema."""
        response = TelemetryResponse(recorded=5, errors=1)
        assert response.recorded == 5
        assert response.errors == 1

    def test_funnel_step_metrics(self):
        """Test FunnelStepMetrics schema."""
        metrics = FunnelStepMetrics(
            funnel_step=1,
            event_name="session_start",
            event_count=100,
            unique_users=80,
            conversion_rate=80.0,
        )
        assert metrics.funnel_step == 1
        assert metrics.unique_users == 80
        assert metrics.conversion_rate == 80.0

    def test_activity_summary(self):
        """Test ActivitySummary schema."""
        summary = ActivitySummary(
            period_start=datetime.now(timezone.utc),
            period_end=datetime.now(timezone.utc),
            total_events=1000,
            unique_users=50,
            unique_sessions=75,
            cvs_generated=20,
            cvs_downloaded=15,
            jobs_searched=30,
            download_rate=75.0,
        )
        assert summary.total_events == 1000
        assert summary.download_rate == 75.0


class TestTelemetryEventNames:
    """Test that event names are consistent."""

    EXPECTED_FUNNEL_EVENTS = [
        "session_start",
        "cv_upload",
        "preferences_configure",
        "job_search_start",
        "job_search_complete",
        "jobs_view",
        "job_details_open",
        "cv_generate_start",
        "cv_generate_complete",
        "cv_preview",
        "cv_refine",
        "cv_download",
        "cv_save_library",
        "application_status_update",
    ]

    EXPECTED_ERROR_EVENTS = [
        "search_empty_results",
        "cv_generation_failed",
        "validation_error",
        "api_error",
    ]

    def test_funnel_event_names_are_valid(self):
        """Test that all expected funnel events can be created."""
        for i, event_name in enumerate(self.EXPECTED_FUNNEL_EVENTS, start=1):
            event = TelemetryEvent(
                event_name=event_name,
                funnel_step=i,
            )
            assert event.event_name == event_name
            assert event.funnel_step == i

    def test_error_event_names_are_valid(self):
        """Test that all expected error events can be created."""
        for event_name in self.EXPECTED_ERROR_EVENTS:
            event = TelemetryEvent(event_name=event_name)
            assert event.event_name == event_name


class TestTelemetryRoutesMocked:
    """Test telemetry routes with mocked database."""

    @pytest.fixture
    def mock_postgres(self):
        """Create a mocked postgres manager."""
        with patch("api.routes.telemetry.get_postgres_manager") as mock:
            pg = MagicMock()
            pg.execute = AsyncMock()
            pg.fetch = AsyncMock(return_value=[])
            mock.return_value = pg
            yield pg

    @pytest.fixture
    def mock_user(self):
        """Create a mock authenticated user."""
        from api.schemas.auth import UserInfo
        return UserInfo(
            auth_user_id=1,
            email="test@example.com",
            display_name="Test User",
            provider="google",
            is_verified=True,
            is_staff=False,
            is_superuser=False,
        )

    @pytest.fixture
    def mock_admin_user(self):
        """Create a mock admin user."""
        from api.schemas.auth import UserInfo
        return UserInfo(
            auth_user_id=1,
            email="admin@example.com",
            display_name="Admin User",
            provider="google",
            is_verified=True,
            is_staff=True,
            is_superuser=True,
        )

    @pytest.mark.asyncio
    async def test_record_events_succeeds(self, mock_postgres):
        """Test that events can be recorded."""
        from api.routes.telemetry import _record_events_async

        events = [
            TelemetryEvent(event_name="test_event"),
            TelemetryEvent(event_name="another_event", funnel_step=1),
        ]

        recorded, errors = await _record_events_async(events, 1, "test@example.com")

        assert recorded == 2
        assert errors == 0
        assert mock_postgres.execute.call_count == 2

    @pytest.mark.asyncio
    async def test_record_events_handles_db_error(self, mock_postgres):
        """Test that database errors are handled gracefully."""
        from api.routes.telemetry import _record_events_async

        # First call succeeds, second fails
        mock_postgres.execute.side_effect = [None, Exception("DB error")]

        events = [
            TelemetryEvent(event_name="event1"),
            TelemetryEvent(event_name="event2"),
        ]

        recorded, errors = await _record_events_async(events, 1, "test@example.com")

        assert recorded == 1
        assert errors == 1

    @pytest.mark.asyncio
    async def test_admin_required_for_analytics(self, mock_user):
        """Test that non-admin users cannot access analytics."""
        from fastapi import HTTPException

        from api.routes.telemetry import _require_admin

        with pytest.raises(HTTPException) as exc_info:
            _require_admin(mock_user)

        assert exc_info.value.status_code == 403
        assert "Admin access required" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_admin_can_access_analytics(self, mock_admin_user):
        """Test that admin users can access analytics."""
        from api.routes.telemetry import _require_admin

        # Should not raise
        _require_admin(mock_admin_user)


class TestTelemetryIntegration:
    """Integration tests for telemetry (require test database)."""

    @pytest.mark.skip(reason="Requires test database with product_events table")
    @pytest.mark.asyncio
    async def test_full_event_recording_flow(self):
        """Test complete flow of recording and retrieving events."""
        # This would test against a real test database
        pass

    @pytest.mark.skip(reason="Requires test database with product_events table")
    @pytest.mark.asyncio
    async def test_funnel_analytics_calculation(self):
        """Test that funnel conversion rates are calculated correctly."""
        pass
