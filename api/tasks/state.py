"""
Task state definitions and helper functions.

Provides consistent task state management across the application,
supporting the transition from file-based to Postgres-based task storage.
"""

from enum import Enum
from typing import Optional


class TaskState(str, Enum):
    """
    Task lifecycle states.

    State transitions:
        pending -> running -> completed
            |         |
            v         v
        cancelled   failed -> pending (retry)
    """

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskType(str, Enum):
    """
    Supported task types with their configuration.

    Each type maps to a specific handler with its own timeout and retry limits.
    """

    JOB_SEARCH = "job_search"
    CV_ANALYSIS = "cv_analysis"
    CV_GENERATION = "cv_generation"
    NOTIFICATION = "notification"
    CV_INDEX = "cv_index"


# Task type configuration
TASK_CONFIG = {
    TaskType.JOB_SEARCH: {
        "timeout_seconds": 600,  # 10 minutes
        "max_retries": 2,
    },
    TaskType.CV_ANALYSIS: {
        "timeout_seconds": 300,  # 5 minutes
        "max_retries": 3,
    },
    TaskType.CV_GENERATION: {
        "timeout_seconds": 300,  # 5 minutes
        "max_retries": 3,
    },
    TaskType.NOTIFICATION: {
        "timeout_seconds": 60,  # 1 minute
        "max_retries": 5,
    },
    TaskType.CV_INDEX: {
        "timeout_seconds": 180,  # 3 minutes
        "max_retries": 3,
    },
}


def is_terminal_state(state: TaskState) -> bool:
    """
    Check if a task state is terminal (no further transitions allowed).

    Args:
        state: The task state to check

    Returns:
        True if the state is terminal (completed, failed, or cancelled)
    """
    return state in (TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELLED)


def can_retry(state: TaskState, attempts: int, max_attempts: int) -> bool:
    """
    Determine if a task can be retried.

    Args:
        state: Current task state
        attempts: Number of attempts so far
        max_attempts: Maximum allowed attempts

    Returns:
        True if the task can be retried
    """
    # Only failed tasks or running tasks (stuck/timed out) can be retried
    if state not in (TaskState.FAILED, TaskState.RUNNING):
        return False

    return attempts < max_attempts


def get_task_config(task_type: TaskType) -> dict:
    """
    Get configuration for a task type.

    Args:
        task_type: The task type

    Returns:
        Configuration dict with timeout_seconds and max_retries
    """
    return TASK_CONFIG.get(task_type, {
        "timeout_seconds": 300,
        "max_retries": 3,
    })


def validate_state_transition(current: TaskState, target: TaskState) -> bool:
    """
    Validate if a state transition is allowed.

    Args:
        current: Current task state
        target: Target task state

    Returns:
        True if the transition is valid

    Valid transitions:
    - pending -> running, cancelled
    - running -> completed, failed, cancelled
    - failed -> pending (retry)
    - completed, cancelled -> (none - terminal)
    """
    valid_transitions = {
        TaskState.PENDING: {TaskState.RUNNING, TaskState.CANCELLED},
        TaskState.RUNNING: {TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELLED},
        TaskState.FAILED: {TaskState.PENDING},  # retry
        TaskState.COMPLETED: set(),  # terminal
        TaskState.CANCELLED: set(),  # terminal
    }

    return target in valid_transitions.get(current, set())
