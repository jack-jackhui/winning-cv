"""Focused tests for the application workspace job-result routes."""
from unittest.mock import Mock

import pytest
from fastapi import HTTPException

from api.routes import jobs
from api.schemas.auth import UserInfo
from api.schemas.jobs import ApplicationStatusUpdate


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
        "Job Link": "https://jobs.example.com/123",
        "Job Description": "Build reliable systems",
        "Application Status": "saved",
    }
    fields.update(field_overrides)
    return {"id": "job-123", "fields": fields}


@pytest.mark.asyncio
async def test_get_job_result_returns_owned_job(monkeypatch):
    manager = Mock()
    manager.get_records_by_filter.return_value = [make_record()]
    history_manager = Mock()
    history_manager.get_history_by_user.return_value = []
    monkeypatch.setattr(jobs, "get_data_manager", lambda: manager)
    monkeypatch.setattr(jobs, "get_history_manager", lambda: history_manager)

    result = await jobs.get_job_result("job-123", make_user())

    assert result.id == "job-123"
    assert result.job_title == "Platform Engineer"
    assert result.application_status.value == "saved"
    manager.get_records_by_filter.assert_called_once_with("{User Email} = 'owner@example.com'")


@pytest.mark.asyncio
async def test_get_job_result_hides_missing_or_foreign_job(monkeypatch):
    manager = Mock()
    manager.get_records_by_filter.return_value = []
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
    manager.get_records_by_filter.return_value = [record]
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
