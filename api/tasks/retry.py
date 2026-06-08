"""
Retry and backoff logic for task processing.

Implements exponential backoff with jitter for failed tasks,
ensuring graceful degradation under load.
"""

import random
from datetime import datetime, timedelta, timezone
from typing import Optional


class RetryableError(Exception):
    """
    Exception indicating a task should be retried.

    Use this for transient failures (network issues, rate limits, etc.)
    where retrying with backoff may succeed.

    Args:
        message: Error description
        retry_after: Optional specific delay before retry
    """

    def __init__(self, message: str, retry_after: Optional[timedelta] = None):
        super().__init__(message)
        self.retry_after = retry_after


class PermanentError(Exception):
    """
    Exception indicating a task should not be retried.

    Use this for permanent failures (invalid input, authorization errors, etc.)
    where retrying would not help.
    """

    pass


# Retry configuration
DEFAULT_BASE_DELAY_SECONDS = 30
DEFAULT_MAX_DELAY_SECONDS = 3600  # 1 hour cap
DEFAULT_JITTER_FACTOR = 0.1  # 10% jitter


def calculate_retry_delay(
    attempts: int,
    base_delay: int = DEFAULT_BASE_DELAY_SECONDS,
    max_delay: int = DEFAULT_MAX_DELAY_SECONDS,
    jitter_factor: float = DEFAULT_JITTER_FACTOR,
) -> timedelta:
    """
    Calculate the delay before retrying a failed task.

    Uses exponential backoff with jitter to prevent thundering herd.

    Args:
        attempts: Number of attempts so far (1 = first retry)
        base_delay: Base delay in seconds (default: 30)
        max_delay: Maximum delay cap in seconds (default: 3600)
        jitter_factor: Random jitter as fraction of delay (default: 0.1)

    Returns:
        timedelta representing the delay before retry

    Examples:
        >>> calculate_retry_delay(1)  # ~30s
        >>> calculate_retry_delay(2)  # ~60s
        >>> calculate_retry_delay(3)  # ~120s
        >>> calculate_retry_delay(4)  # ~240s
        >>> calculate_retry_delay(7)  # ~3600s (capped)
    """
    # Exponential backoff: base * 2^attempts
    delay = min(base_delay * (2 ** attempts), max_delay)

    # Add jitter to prevent synchronized retries
    jitter = random.uniform(0, delay * jitter_factor)

    return timedelta(seconds=delay + jitter)


def calculate_retry_timestamp(
    attempts: int,
    base_delay: int = DEFAULT_BASE_DELAY_SECONDS,
    max_delay: int = DEFAULT_MAX_DELAY_SECONDS,
) -> datetime:
    """
    Calculate the timestamp when a task should be retried.

    Args:
        attempts: Number of attempts so far
        base_delay: Base delay in seconds
        max_delay: Maximum delay cap in seconds

    Returns:
        UTC datetime when the task should be retried
    """
    delay = calculate_retry_delay(attempts, base_delay, max_delay)
    return datetime.now(timezone.utc) + delay


def should_retry_exception(exc: Exception) -> bool:
    """
    Determine if an exception should trigger a retry.

    Args:
        exc: The exception that occurred

    Returns:
        True if the task should be retried
    """
    # Never retry permanent errors
    if isinstance(exc, PermanentError):
        return False

    # Always retry retryable errors
    if isinstance(exc, RetryableError):
        return True

    # Retry common transient errors
    transient_indicators = [
        "timeout",
        "connection",
        "rate limit",
        "too many requests",
        "503",
        "502",
        "504",
        "temporarily unavailable",
    ]

    error_str = str(exc).lower()
    return any(indicator in error_str for indicator in transient_indicators)


def get_retry_delay_for_exception(exc: Exception, attempts: int) -> timedelta:
    """
    Get the retry delay for a specific exception.

    Handles special cases like rate limit headers.

    Args:
        exc: The exception that occurred
        attempts: Number of attempts so far

    Returns:
        timedelta representing the delay before retry
    """
    # Check for explicit retry_after on RetryableError
    if isinstance(exc, RetryableError) and exc.retry_after:
        return exc.retry_after

    # Default exponential backoff
    return calculate_retry_delay(attempts)
