"""
Tests for the task queue module.

Tests cover:
- Task state transitions and validation
- Retry delay calculations
- Worker task claiming and processing logic
"""

import pytest
from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from api.tasks.state import (
    TaskState,
    TaskType,
    is_terminal_state,
    can_retry,
    get_task_config,
    validate_state_transition,
    TASK_CONFIG,
)
from api.tasks.retry import (
    RetryableError,
    PermanentError,
    calculate_retry_delay,
    calculate_retry_timestamp,
    should_retry_exception,
    get_retry_delay_for_exception,
)


class TestTaskState:
    """Tests for task state enum and helpers."""

    def test_task_states_are_strings(self):
        """Task states should be string enums for JSON serialization."""
        assert TaskState.PENDING.value == "pending"
        assert TaskState.RUNNING.value == "running"
        assert TaskState.COMPLETED.value == "completed"
        assert TaskState.FAILED.value == "failed"
        assert TaskState.CANCELLED.value == "cancelled"

    def test_is_terminal_state(self):
        """Terminal states should not allow further transitions."""
        # Terminal states
        assert is_terminal_state(TaskState.COMPLETED) is True
        assert is_terminal_state(TaskState.FAILED) is True
        assert is_terminal_state(TaskState.CANCELLED) is True

        # Non-terminal states
        assert is_terminal_state(TaskState.PENDING) is False
        assert is_terminal_state(TaskState.RUNNING) is False

    def test_can_retry_failed_task(self):
        """Failed tasks can be retried if under max attempts."""
        assert can_retry(TaskState.FAILED, attempts=1, max_attempts=3) is True
        assert can_retry(TaskState.FAILED, attempts=2, max_attempts=3) is True
        assert can_retry(TaskState.FAILED, attempts=3, max_attempts=3) is False

    def test_can_retry_running_task(self):
        """Running tasks (stuck/timed out) can be retried."""
        assert can_retry(TaskState.RUNNING, attempts=1, max_attempts=3) is True
        assert can_retry(TaskState.RUNNING, attempts=3, max_attempts=3) is False

    def test_cannot_retry_terminal_states(self):
        """Completed and cancelled tasks cannot be retried."""
        assert can_retry(TaskState.COMPLETED, attempts=1, max_attempts=3) is False
        assert can_retry(TaskState.CANCELLED, attempts=1, max_attempts=3) is False

    def test_cannot_retry_pending(self):
        """Pending tasks don't need retry (they haven't run yet)."""
        assert can_retry(TaskState.PENDING, attempts=1, max_attempts=3) is False


class TestTaskType:
    """Tests for task type configuration."""

    def test_task_types_are_strings(self):
        """Task types should be string enums."""
        assert TaskType.JOB_SEARCH.value == "job_search"
        assert TaskType.CV_ANALYSIS.value == "cv_analysis"
        assert TaskType.CV_GENERATION.value == "cv_generation"
        assert TaskType.NOTIFICATION.value == "notification"
        assert TaskType.CV_INDEX.value == "cv_index"

    def test_all_task_types_have_config(self):
        """All task types should have configuration."""
        for task_type in TaskType:
            config = get_task_config(task_type)
            assert "timeout_seconds" in config
            assert "max_retries" in config
            assert config["timeout_seconds"] > 0
            assert config["max_retries"] >= 0

    def test_job_search_has_longer_timeout(self):
        """Job search should have a longer timeout due to scraping."""
        config = get_task_config(TaskType.JOB_SEARCH)
        assert config["timeout_seconds"] >= 600  # 10+ minutes

    def test_notification_has_more_retries(self):
        """Notifications should have more retries for reliability."""
        config = get_task_config(TaskType.NOTIFICATION)
        assert config["max_retries"] >= 5


class TestStateTransitions:
    """Tests for state transition validation."""

    def test_pending_can_become_running(self):
        """Pending tasks can transition to running."""
        assert validate_state_transition(TaskState.PENDING, TaskState.RUNNING) is True

    def test_pending_can_be_cancelled(self):
        """Pending tasks can be cancelled."""
        assert validate_state_transition(TaskState.PENDING, TaskState.CANCELLED) is True

    def test_pending_cannot_skip_to_completed(self):
        """Pending tasks cannot skip directly to completed."""
        assert validate_state_transition(TaskState.PENDING, TaskState.COMPLETED) is False

    def test_running_can_complete(self):
        """Running tasks can complete successfully."""
        assert validate_state_transition(TaskState.RUNNING, TaskState.COMPLETED) is True

    def test_running_can_fail(self):
        """Running tasks can fail."""
        assert validate_state_transition(TaskState.RUNNING, TaskState.FAILED) is True

    def test_running_can_be_cancelled(self):
        """Running tasks can be cancelled."""
        assert validate_state_transition(TaskState.RUNNING, TaskState.CANCELLED) is True

    def test_failed_can_be_retried(self):
        """Failed tasks can transition back to pending for retry."""
        assert validate_state_transition(TaskState.FAILED, TaskState.PENDING) is True

    def test_completed_is_terminal(self):
        """Completed tasks cannot transition to any state."""
        for target in TaskState:
            assert validate_state_transition(TaskState.COMPLETED, target) is False

    def test_cancelled_is_terminal(self):
        """Cancelled tasks cannot transition to any state."""
        for target in TaskState:
            assert validate_state_transition(TaskState.CANCELLED, target) is False


class TestRetryDelay:
    """Tests for retry delay calculation."""

    def test_first_retry_uses_base_delay(self):
        """First retry should be close to base delay."""
        delay = calculate_retry_delay(attempts=1, base_delay=30)
        # With jitter, should be between 30-60 seconds
        assert 30 <= delay.total_seconds() <= 90

    def test_exponential_backoff(self):
        """Delays should increase exponentially."""
        delay1 = calculate_retry_delay(attempts=1, base_delay=30, jitter_factor=0)
        delay2 = calculate_retry_delay(attempts=2, base_delay=30, jitter_factor=0)
        delay3 = calculate_retry_delay(attempts=3, base_delay=30, jitter_factor=0)

        assert delay2.total_seconds() > delay1.total_seconds()
        assert delay3.total_seconds() > delay2.total_seconds()

    def test_max_delay_cap(self):
        """Delay should be capped at max_delay."""
        delay = calculate_retry_delay(
            attempts=10,
            base_delay=30,
            max_delay=100,
            jitter_factor=0
        )
        # Should be capped at 100s + up to 10% jitter
        assert delay.total_seconds() <= 110

    def test_jitter_adds_randomness(self):
        """Jitter should add some randomness to delays."""
        delays = [
            calculate_retry_delay(attempts=2, jitter_factor=0.1)
            for _ in range(10)
        ]
        # With jitter, not all delays should be identical
        unique_delays = set(d.total_seconds() for d in delays)
        # Very unlikely to have all 10 be identical with jitter
        assert len(unique_delays) > 1

    def test_calculate_retry_timestamp(self):
        """Retry timestamp should be in the future."""
        from datetime import datetime, timezone

        retry_at = calculate_retry_timestamp(attempts=1)
        assert retry_at > datetime.now(timezone.utc)


class TestRetryableErrors:
    """Tests for retryable error handling."""

    def test_retryable_error_should_retry(self):
        """RetryableError should trigger retry."""
        error = RetryableError("Temporary failure")
        assert should_retry_exception(error) is True

    def test_permanent_error_should_not_retry(self):
        """PermanentError should not trigger retry."""
        error = PermanentError("Invalid input")
        assert should_retry_exception(error) is False

    def test_timeout_error_should_retry(self):
        """Timeout errors should trigger retry."""
        error = Exception("Connection timeout")
        assert should_retry_exception(error) is True

    def test_rate_limit_should_retry(self):
        """Rate limit errors should trigger retry."""
        error = Exception("Rate limit exceeded (429)")
        assert should_retry_exception(error) is True

    def test_503_should_retry(self):
        """503 errors should trigger retry."""
        error = Exception("Service unavailable (503)")
        assert should_retry_exception(error) is True

    def test_generic_error_does_not_retry(self):
        """Generic errors without transient indicators should not retry."""
        error = Exception("Some unexpected error occurred")
        assert should_retry_exception(error) is False

    def test_retryable_error_with_explicit_delay(self):
        """RetryableError can specify explicit retry delay."""
        explicit_delay = timedelta(minutes=5)
        error = RetryableError("Rate limited", retry_after=explicit_delay)

        delay = get_retry_delay_for_exception(error, attempts=1)
        assert delay == explicit_delay


class TestRetryDelayForException:
    """Tests for exception-specific retry delays."""

    def test_retryable_error_uses_explicit_delay(self):
        """RetryableError with retry_after uses that delay."""
        delay = timedelta(seconds=120)
        error = RetryableError("Rate limited", retry_after=delay)

        result = get_retry_delay_for_exception(error, attempts=2)
        assert result == delay

    def test_regular_exception_uses_backoff(self):
        """Regular exceptions use exponential backoff."""
        error = Exception("Timeout")

        delay1 = get_retry_delay_for_exception(error, attempts=1)
        delay2 = get_retry_delay_for_exception(error, attempts=3)

        # Later attempt should have longer delay
        assert delay2.total_seconds() > delay1.total_seconds()


# Prevent test discovery from importing worker module which has signal handlers
# that don't work well in pytest context
class TestWorkerUnit:
    """Unit tests for worker components (without actually starting worker)."""

    def test_worker_initializes_with_id(self):
        """Worker should have a unique ID."""
        from api.tasks.worker import TaskWorker

        worker = TaskWorker()
        assert worker.worker_id.startswith("worker-")
        assert len(worker.worker_id) > 10

    def test_worker_accepts_custom_id(self):
        """Worker should accept custom ID."""
        from api.tasks.worker import TaskWorker

        worker = TaskWorker(worker_id="test-worker-1")
        assert worker.worker_id == "test-worker-1"

    def test_worker_filters_task_types(self):
        """Worker should filter task types it handles."""
        from api.tasks.worker import TaskWorker

        worker = TaskWorker(task_types=[TaskType.JOB_SEARCH])
        assert TaskType.JOB_SEARCH in worker.task_types
        assert TaskType.NOTIFICATION not in worker.task_types

    def test_worker_handles_all_types_by_default(self):
        """Worker handles all task types by default."""
        from api.tasks.worker import TaskWorker

        worker = TaskWorker()
        assert len(worker.task_types) == len(TaskType)
