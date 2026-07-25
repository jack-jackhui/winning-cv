"""Regression tests for observable job-search shadow-write failures."""
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from api.routes import jobs
from data_store.storage_factory import ShadowWriteError
from job_processing.core import JobProcessor


def _processor():
    processor = JobProcessor.__new__(JobProcessor)
    processor.config = SimpleNamespace(user_email="owner@example.com")
    processor.airtable = Mock()
    processor.airtable.get_existing_job_links.return_value = set()
    processor.airtable.job_exists.return_value = False
    processor.airtable.create_job_record.side_effect = ShadowWriteError("shadow diverged")
    processor.content_cleaner = Mock()
    processor.content_cleaner.clean_html.side_effect = lambda value: value
    processor.linkedin_scraper = Mock()
    processor.linkedin_scraper.scrape_job_page.return_value = [
        {"title": "Engineer", "job_url": "https://jobs.example.com/linkedin", "description": "Build"}
    ]
    processor.seek_scraper = Mock()
    processor.seek_scraper.scrape_jobs.return_value = [
        {"title": "Engineer", "job_url": "https://jobs.example.com/seek", "description": "Build"}
    ]
    processor.additional_processor = Mock()
    processor.additional_processor.scrape_and_process_jobs.return_value = [
        {"Job Title": "Engineer", "Job Link": "https://jobs.example.com/additional", "Job Description": "Build"}
    ]
    processor.get_target_urls = Mock(return_value=["https://linkedin.example/search"])
    processor._progress_callback = None
    return processor


@pytest.mark.parametrize(
    "method_name",
    ["_process_linkedin_jobs", "_process_seek_jobs", "_process_additional_sources"],
)
def test_scraper_boundaries_reraise_shadow_write_error(method_name):
    processor = _processor()

    with pytest.raises(ShadowWriteError, match="shadow diverged"):
        getattr(processor, method_name)()


def test_scraper_boundary_still_handles_ordinary_errors():
    processor = _processor()
    processor.seek_scraper.scrape_jobs.side_effect = RuntimeError("board unavailable")

    assert processor._process_seek_jobs() == 0


def test_process_jobs_does_not_report_no_jobs_after_shadow_write_failure():
    processor = _processor()
    progress = []
    processor._progress_callback = lambda percent, message: progress.append((percent, message))
    processor._process_linkedin_jobs = Mock(side_effect=ShadowWriteError("shadow diverged"))
    processor._process_seek_jobs = Mock(return_value=0)
    processor._process_additional_sources = Mock(return_value=0)

    with pytest.raises(ShadowWriteError, match="shadow diverged"):
        processor.process_jobs()

    assert all(message != "No new jobs found" for _, message in progress)


def test_background_search_marks_shadow_write_failure_failed(monkeypatch):
    task_manager = Mock()
    processor = Mock()
    processor.process_jobs.side_effect = ShadowWriteError("shadow diverged")
    processor_factory = Mock(return_value=processor)
    monkeypatch.setattr(jobs, "_get_task_manager", lambda: task_manager)
    monkeypatch.setattr(jobs, "get_data_manager", Mock(return_value=Mock()))
    monkeypatch.setattr(jobs, "JobProcessor", processor_factory)

    jobs._run_job_search("task-123", "owner@example.com", {})

    failed_calls = [
        call for call in task_manager.update_task.call_args_list
        if call.kwargs.get("status") == jobs.SearchStatus.FAILED.value
    ]
    completed_calls = [
        call for call in task_manager.update_task.call_args_list
        if call.kwargs.get("status") == jobs.SearchStatus.COMPLETED.value
    ]
    assert len(failed_calls) == 1
    assert failed_calls[0].kwargs["message"] == "shadow diverged"
    assert failed_calls[0].kwargs["error_details"] == "shadow diverged"
    assert completed_calls == []
