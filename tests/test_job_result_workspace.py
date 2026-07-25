"""Focused tests for the application workspace job-result routes."""
from contextlib import contextmanager
from datetime import datetime, timezone
from unittest.mock import Mock

from requests import HTTPError, Response

import pytest
from fastapi import HTTPException

from api.routes import jobs
from api.schemas.auth import UserInfo
from api.schemas.jobs import ApplicationStatusUpdate
from data_store.airtable_manager import AirtableManager
from data_store.postgres_manager import PostgresManager
from data_store.storage_factory import DualWriteDataManager, ShadowWriteError


def make_user(email: str = "owner@example.com") -> UserInfo:
    return UserInfo(
        auth_user_id=1,
        email=email,
        display_name="Owner",
        provider="test",
        is_verified=True,
    )


def make_record(**field_overrides):
    fields = {
        "User Email": "owner@example.com",
        "Job Title": "Platform Engineer",
        "Company": "Example Co",
        "Location": "Melbourne",
        "Matching Score": 8.7,
        "ATS Score": 92,
        "Job Link": "https://jobs.example.com/123",
        "Job Description": "Build reliable systems",
        "Application Status": "saved",
    }
    fields.update(field_overrides)
    return {"id": "job-123", "fields": fields}


@pytest.mark.asyncio
async def test_get_job_result_returns_owned_job(monkeypatch):
    manager = Mock()
    manager.get_job_result.return_value = make_record()
    history_manager = Mock()
    history_manager.get_history_by_user.return_value = []
    monkeypatch.setattr(jobs, "get_data_manager", lambda: manager)
    monkeypatch.setattr(jobs, "get_history_manager", lambda: history_manager)

    result = await jobs.get_job_result("job-123", make_user())

    assert result.id == "job-123"
    assert result.job_title == "Platform Engineer"
    assert result.application_status.value == "saved"
    assert result.score == 8.7
    assert result.score_breakdown.ats_score == 92
    manager.get_job_result.assert_called_once_with(
        job_id="job-123",
        user_email="owner@example.com",
    )


@pytest.mark.asyncio
async def test_get_job_result_hides_missing_or_foreign_job(monkeypatch):
    manager = Mock()
    manager.get_job_result.return_value = None
    monkeypatch.setattr(jobs, "get_data_manager", lambda: manager)

    with pytest.raises(HTTPException) as exc_info:
        await jobs.get_job_result("foreign-job", make_user())

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Job not found"


@pytest.mark.asyncio
async def test_update_application_status_returns_saved_job(monkeypatch):
    record = make_record()
    manager = Mock()

    def update_application_status(**kwargs):
        record["fields"]["Application Status"] = kwargs["application_status"]
        record["fields"]["Application Notes"] = kwargs["application_notes"]
        return {"id": kwargs["job_id"]}

    manager.update_application_status.side_effect = update_application_status
    manager.get_job_result.return_value = record
    history_manager = Mock()
    history_manager.get_history_by_user.return_value = []
    monkeypatch.setattr(jobs, "get_data_manager", lambda: manager)
    monkeypatch.setattr(jobs, "get_history_manager", lambda: history_manager)

    result = await jobs.update_application_status_result(
        "job-123",
        ApplicationStatusUpdate(application_status="applied", application_notes="Submitted today"),
        make_user(),
    )

    assert result.application_status.value == "applied"
    assert result.application_notes == "Submitted today"
    manager.update_application_status.assert_called_once_with(
        job_id="job-123",
        user_email="owner@example.com",
        application_status="applied",
        application_notes="Submitted today",
    )


@pytest.mark.asyncio
async def test_update_application_status_reports_unsupported_backend(monkeypatch):
    monkeypatch.setattr(jobs, "get_data_manager", lambda: object())

    with pytest.raises(HTTPException) as exc_info:
        await jobs.update_application_status_result(
            "job-123",
            ApplicationStatusUpdate(application_status="saved"),
            make_user(),
        )

    assert exc_info.value.status_code == 501


def test_postgres_job_lookup_parameterizes_apostrophe_email():
    row = {
        "id": "d5b0fbe6-1e2b-4e65-90b0-2bb092f66d14",
        "user_email": "o'connor@example.com",
        "job_title": "Platform Engineer",
        "job_description": "Build reliable systems",
        "job_date": None,
        "job_link": "https://jobs.example.com/123",
        "company": "Example Co",
        "location": "Melbourne",
        "matching_score": 8.7,
        "cv_link": None,
        "match_reasons": None,
        "match_suggestions": None,
        "ats_score": None,
        "hr_score": None,
        "llm_score": None,
        "hr_recommendation": None,
        "matched_keywords": None,
        "missing_keywords": None,
        "application_status": "saved",
        "application_notes": None,
        "applied_at": None,
        "created_at": None,
        "updated_at": None,
    }
    cursor = Mock()
    cursor.fetchone.return_value = row
    manager = PostgresManager("postgresql://unused")

    @contextmanager
    def fake_cursor():
        yield cursor

    manager.get_cursor = fake_cursor
    result = manager.get_job_result(row["id"], row["user_email"])

    assert result["id"] == row["id"]
    query, params = cursor.execute.call_args.args
    assert "WHERE id::text = %s AND user_email = %s" in query
    assert params == (row["id"], "o'connor@example.com")


def test_postgres_list_jobs_parameterizes_apostrophe_email():
    cursor = Mock()
    cursor.fetchall.return_value = []
    manager = PostgresManager("postgresql://unused")

    @contextmanager
    def fake_cursor():
        yield cursor

    manager.get_cursor = fake_cursor
    assert manager.get_jobs_by_user("o'connor@example.com") == []
    query, params = cursor.execute.call_args.args
    assert "WHERE user_email = %s" in query
    assert params == ("o'connor@example.com",)

def test_airtable_job_lookup_checks_exact_owner_without_formula():
    manager = AirtableManager.__new__(AirtableManager)
    manager.table = Mock()
    manager.logger = Mock()
    manager.table.get.return_value = make_record(**{"User Email": "o'connor@example.com"})

    assert manager.get_job_result("job-123", "o'connor@example.com")["id"] == "job-123"
    assert manager.get_job_result("job-123", "foreign@example.com") is None
    manager.table.get.assert_called_with("job-123")


@pytest.mark.parametrize(
    "created_at",
    [
        datetime(2026, 7, 25, 1, 30, tzinfo=timezone.utc),
        datetime(2026, 7, 25, 1, 30),
    ],
)
def test_job_result_accepts_postgres_datetime_for_cv_history(created_at):
    record = make_record(**{"CV Link": "https://example.com/cv.pdf"})

    result = jobs._job_result_from_record(
        record,
        {"https://example.com/cv.pdf": created_at},
    )

    assert result.cv_generated_at == created_at


def test_postgres_application_update_is_owner_scoped_and_persists():
    cursor = Mock()
    cursor.fetchone.return_value = {"id": "d5b0fbe6-1e2b-4e65-90b0-2bb092f66d14"}
    manager = PostgresManager("postgresql://unused")

    @contextmanager
    def fake_cursor():
        yield cursor

    manager.get_cursor = fake_cursor
    result = manager.update_application_status(
        "d5b0fbe6-1e2b-4e65-90b0-2bb092f66d14",
        "owner@example.com",
        "applied",
        "Submitted today",
    )

    assert result == {"id": "d5b0fbe6-1e2b-4e65-90b0-2bb092f66d14"}
    query, params = cursor.execute.call_args.args
    assert "WHERE id::text = %s AND user_email = %s" in query
    assert params == (
        "applied",
        "Submitted today",
        "applied",
        "d5b0fbe6-1e2b-4e65-90b0-2bb092f66d14",
        "owner@example.com",
    )


def test_postgres_application_update_denies_cross_user():
    cursor = Mock()
    cursor.fetchone.return_value = None
    manager = PostgresManager("postgresql://unused")

    @contextmanager
    def fake_cursor():
        yield cursor

    manager.get_cursor = fake_cursor
    result = manager.update_application_status(
        "d5b0fbe6-1e2b-4e65-90b0-2bb092f66d14",
        "foreign@example.com",
        "applied",
        None,
    )

    assert result is None
    _, params = cursor.execute.call_args.args
    assert params[-2:] == (
        "d5b0fbe6-1e2b-4e65-90b0-2bb092f66d14",
        "foreign@example.com",
    )


def test_postgres_lookup_propagates_backend_failure():
    manager = PostgresManager("postgresql://unused")

    @contextmanager
    def failing_cursor():
        raise RuntimeError("database unavailable")
        yield

    manager.get_cursor = failing_cursor

    with pytest.raises(RuntimeError, match="database unavailable"):
        manager.get_job_result("job-123", "owner@example.com")


def test_airtable_application_update_persists_for_exact_owner():
    manager = AirtableManager.__new__(AirtableManager)
    manager.table = Mock()
    manager.logger = Mock()
    manager.table.get.return_value = make_record()
    manager.table.update.return_value = make_record(
        **{
            "Application Status": "applied",
            "Application Notes": "Submitted today",
        }
    )

    result = manager.update_application_status(
        "job-123", "owner@example.com", "applied", "Submitted today"
    )

    assert result["fields"]["Application Status"] == "applied"
    updated_id, fields = manager.table.update.call_args.args
    assert updated_id == "job-123"
    assert fields["Application Status"] == "applied"
    assert fields["Application Notes"] == "Submitted today"
    assert datetime.fromisoformat(fields["Applied At"]).tzinfo is not None


def test_airtable_application_update_denies_cross_user():
    manager = AirtableManager.__new__(AirtableManager)
    manager.table = Mock()
    manager.logger = Mock()
    manager.table.get.return_value = make_record()

    assert manager.update_application_status(
        "job-123", "foreign@example.com", "applied", "Should not save"
    ) is None
    manager.table.update.assert_not_called()


def test_airtable_lookup_returns_none_for_real_not_found_response():
    manager = AirtableManager.__new__(AirtableManager)
    manager.table = Mock()
    manager.logger = Mock()
    response = Response()
    response.status_code = 404
    manager.table.get.side_effect = HTTPError(response=response)

    assert manager.get_job_result("missing-job", "owner@example.com") is None


def test_airtable_lookup_propagates_backend_failure():
    manager = AirtableManager.__new__(AirtableManager)
    manager.table = Mock()
    manager.logger = Mock()
    manager.table.get.side_effect = RuntimeError("airtable unavailable")

    with pytest.raises(RuntimeError, match="airtable unavailable"):
        manager.get_job_result("job-123", "owner@example.com")


def test_dual_write_application_update_uses_airtable_primary_and_postgres_shadow():
    airtable = Mock()
    postgres = Mock()
    airtable.update_application_status.return_value = make_record()
    manager = DualWriteDataManager(airtable, postgres)

    result = manager.update_application_status(
        "job-123", "owner@example.com", "interviewing", "Phone screen"
    )

    assert result["id"] == "job-123"
    airtable.update_application_status.assert_called_once_with(
        "job-123", "owner@example.com", "interviewing", "Phone screen"
    )
    postgres.update_application_status.assert_called_once_with(
        "job-123",
        "owner@example.com",
        "interviewing",
        "Phone screen",
        job_link="https://jobs.example.com/123",
    )


@pytest.mark.parametrize("shadow_result", [None, RuntimeError("postgres unavailable")])
def test_dual_write_application_update_reports_shadow_failure(shadow_result, caplog):
    airtable = Mock()
    postgres = Mock()
    airtable.update_application_status.return_value = make_record()
    if isinstance(shadow_result, Exception):
        postgres.update_application_status.side_effect = shadow_result
    else:
        postgres.update_application_status.return_value = shadow_result
    manager = DualWriteDataManager(airtable, postgres)

    with pytest.raises(ShadowWriteError):
        manager.update_application_status(
            "job-123", "owner@example.com", "saved", None
        )

    assert "Postgres shadow write" in caplog.text


def test_postgres_dual_write_update_uses_owner_scoped_job_link():
    cursor = Mock()
    cursor.fetchone.return_value = {"id": 42}
    manager = PostgresManager("postgresql://unused")

    @contextmanager
    def fake_cursor():
        yield cursor

    manager.get_cursor = fake_cursor
    result = manager.update_application_status(
        "recAirtable",
        "owner@example.com",
        "applied",
        "Submitted",
        job_link="https://jobs.example.com/123",
    )

    assert result == {"id": "42"}
    query, params = cursor.execute.call_args.args
    assert "WHERE job_link = %s AND user_email = %s" in query
    assert params[-2:] == ("https://jobs.example.com/123", "owner@example.com")


@pytest.mark.asyncio
@pytest.mark.parametrize("operation", ["lookup", "update"])
async def test_routes_report_storage_failure_as_service_unavailable(monkeypatch, operation):
    manager = Mock()
    manager.get_job_result.side_effect = RuntimeError("backend unavailable")
    manager.update_application_status.side_effect = RuntimeError("backend unavailable")
    monkeypatch.setattr(jobs, "get_data_manager", lambda: manager)

    with pytest.raises(HTTPException) as exc_info:
        if operation == "lookup":
            await jobs.get_job_result("job-123", make_user())
        else:
            await jobs.update_application_status_result(
                "job-123",
                ApplicationStatusUpdate(application_status="saved"),
                make_user(),
            )

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == "Job storage unavailable"


@pytest.mark.asyncio
async def test_list_results_uses_typed_user_lookup(monkeypatch):
    manager = Mock()
    manager.get_jobs_by_user.return_value = [make_record()]
    history_manager = Mock()
    history_manager.get_history_by_user.return_value = []
    monkeypatch.setattr(jobs, "get_data_manager", lambda: manager)
    monkeypatch.setattr(jobs, "get_history_manager", lambda: history_manager)

    result = await jobs.get_job_results(make_user("o'connor@example.com"))

    assert result.total == 1
    manager.get_jobs_by_user.assert_called_once_with("o'connor@example.com")
    manager.get_records_by_filter.assert_not_called()


@pytest.mark.parametrize("shadow_result", [None, RuntimeError("postgres unavailable")])
def test_dual_write_create_reports_shadow_failure(shadow_result, caplog):
    airtable = Mock()
    postgres = Mock()
    airtable.create_job_record.return_value = make_record()
    if isinstance(shadow_result, Exception):
        postgres.create_job_record.side_effect = shadow_result
    else:
        postgres.create_job_record.return_value = shadow_result
    manager = DualWriteDataManager(airtable, postgres)

    with pytest.raises(ShadowWriteError):
        manager.create_job_record({"Job Link": "https://jobs.example.com/123"}, "owner@example.com")

    assert "Postgres shadow write" in caplog.text


@pytest.mark.parametrize("shadow_result", [None, RuntimeError("postgres unavailable")])
def test_dual_write_cv_update_reports_shadow_failure(shadow_result, caplog):
    airtable = Mock()
    postgres = Mock()
    airtable.update_cv_info.return_value = make_record()
    if isinstance(shadow_result, Exception):
        postgres.update_cv_info.side_effect = shadow_result
    else:
        postgres.update_cv_info.return_value = shadow_result
    manager = DualWriteDataManager(airtable, postgres)

    with pytest.raises(ShadowWriteError):
        manager.update_cv_info(
            "https://jobs.example.com/123",
            9,
            "https://files.example.com/cv.pdf",
            user_email="owner@example.com",
        )

    assert "Postgres shadow write" in caplog.text
