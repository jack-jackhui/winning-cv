"""
Task Worker implementation.

Provides the base worker class for processing background tasks.
Workers can run as separate processes or threads.

This is a scaffold for future implementation. The actual worker
execution is still handled by ThreadPoolExecutor in the API process.
"""

import asyncio
import logging
import os
import signal
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from api.tasks.retry import (
    RetryableError,
    PermanentError,
    calculate_retry_timestamp,
    should_retry_exception,
    get_retry_delay_for_exception,
)
from api.tasks.state import (
    TaskState,
    TaskType,
    get_task_config,
    is_terminal_state,
    can_retry,
)

logger = logging.getLogger(__name__)

# Default polling interval when no tasks are available
DEFAULT_POLL_INTERVAL = 5.0  # seconds


class TaskHandler(ABC):
    """
    Base class for task handlers.

    Each task type should have a corresponding handler that knows
    how to execute the task and report progress.
    """

    @property
    @abstractmethod
    def task_type(self) -> TaskType:
        """The task type this handler processes."""
        pass

    @abstractmethod
    async def execute(
        self,
        payload: Dict[str, Any],
        progress_callback: Callable[[int, str], None],
    ) -> Dict[str, Any]:
        """
        Execute the task.

        Args:
            payload: Task-specific input data
            progress_callback: Function to report progress (0-100, message)

        Returns:
            Task result data

        Raises:
            RetryableError: For transient failures that should be retried
            PermanentError: For failures that should not be retried
        """
        pass


class TaskWorker:
    """
    Background task worker that processes tasks from the queue.

    The worker polls for pending tasks, claims them atomically,
    and executes them using the appropriate handler.

    This is a scaffold - actual database operations and the full
    run loop will be implemented when Postgres task queue is ready.
    """

    def __init__(
        self,
        worker_id: Optional[str] = None,
        task_types: Optional[List[TaskType]] = None,
        poll_interval: float = DEFAULT_POLL_INTERVAL,
    ):
        """
        Initialize the worker.

        Args:
            worker_id: Unique identifier for this worker instance
            task_types: List of task types this worker handles (None = all)
            poll_interval: Seconds to wait between polling when queue is empty
        """
        self.worker_id = worker_id or f"worker-{uuid.uuid4().hex[:8]}"
        self.task_types = task_types or list(TaskType)
        self.poll_interval = poll_interval
        self.running = False
        self.current_task_id: Optional[str] = None

        # Registry of handlers by task type
        self._handlers: Dict[TaskType, TaskHandler] = {}

        logger.info(
            f"Worker {self.worker_id} initialized for task types: "
            f"{[t.value for t in self.task_types]}"
        )

    def register_handler(self, handler: TaskHandler) -> None:
        """
        Register a handler for a task type.

        Args:
            handler: TaskHandler instance
        """
        self._handlers[handler.task_type] = handler
        logger.info(f"Registered handler for {handler.task_type.value}")

    def get_handler(self, task_type: TaskType) -> Optional[TaskHandler]:
        """
        Get the handler for a task type.

        Args:
            task_type: The task type

        Returns:
            TaskHandler or None if not registered
        """
        return self._handlers.get(task_type)

    async def start(self) -> None:
        """
        Start the worker.

        This method blocks until stop() is called or a signal is received.
        """
        self.running = True
        logger.info(f"Worker {self.worker_id} starting")

        # Set up signal handlers for graceful shutdown
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, self._handle_shutdown)

        try:
            await self._run_loop()
        finally:
            self.running = False
            logger.info(f"Worker {self.worker_id} stopped")

    async def stop(self) -> None:
        """
        Signal the worker to stop gracefully.

        The worker will finish processing its current task before stopping.
        """
        logger.info(f"Worker {self.worker_id} stopping gracefully")
        self.running = False

    def _handle_shutdown(self) -> None:
        """Handle shutdown signals."""
        logger.info(f"Worker {self.worker_id} received shutdown signal")
        self.running = False

    async def _run_loop(self) -> None:
        """
        Main worker loop.

        Polls for tasks, claims them, and processes them.
        """
        while self.running:
            try:
                task = await self._claim_task()
                if task:
                    await self._process_task(task)
                else:
                    # No tasks available, wait before polling again
                    await asyncio.sleep(self.poll_interval)
            except Exception as e:
                logger.error(f"Worker loop error: {e}", exc_info=True)
                await asyncio.sleep(self.poll_interval)

    async def _claim_task(self) -> Optional[Dict[str, Any]]:
        """
        Atomically claim a pending task from the queue.

        Returns:
            Task data dict or None if no tasks available

        Note: This is a stub. Actual implementation requires the Postgres
        task queue with FOR UPDATE SKIP LOCKED for safe concurrent claiming.
        """
        # TODO: Implement Postgres-based task claiming
        # The SQL would look like:
        #
        # UPDATE task_queue
        # SET status = 'running',
        #     worker_id = :worker_id,
        #     started_at = NOW(),
        #     attempts = attempts + 1
        # WHERE id = (
        #     SELECT id FROM task_queue
        #     WHERE status = 'pending'
        #       AND task_type = ANY(:task_types)
        #       AND (retry_after IS NULL OR retry_after <= NOW())
        #     ORDER BY priority DESC, created_at
        #     FOR UPDATE SKIP LOCKED
        #     LIMIT 1
        # )
        # RETURNING *
        return None

    async def _process_task(self, task: Dict[str, Any]) -> None:
        """
        Process a claimed task.

        Args:
            task: Task data dict with id, task_type, payload, etc.
        """
        task_id = task["id"]
        task_type = TaskType(task["task_type"])
        payload = task.get("payload", {})
        attempts = task.get("attempts", 1)
        max_attempts = task.get("max_attempts", 3)

        self.current_task_id = task_id
        logger.info(
            f"Processing task {task_id} (type={task_type.value}, "
            f"attempt={attempts}/{max_attempts})"
        )

        handler = self.get_handler(task_type)
        if not handler:
            logger.error(f"No handler registered for task type: {task_type.value}")
            await self._fail_task(task_id, "No handler registered")
            return

        try:
            # Execute the handler
            result = await handler.execute(payload, self._make_progress_callback(task_id))
            await self._complete_task(task_id, result)

        except RetryableError as e:
            if can_retry(TaskState.FAILED, attempts, max_attempts):
                await self._schedule_retry(task_id, attempts, e)
            else:
                await self._fail_task(task_id, str(e))

        except PermanentError as e:
            await self._fail_task(task_id, str(e))

        except Exception as e:
            if should_retry_exception(e) and can_retry(TaskState.FAILED, attempts, max_attempts):
                await self._schedule_retry(task_id, attempts, e)
            else:
                await self._fail_task(task_id, str(e))

        finally:
            self.current_task_id = None

    def _make_progress_callback(
        self, task_id: str
    ) -> Callable[[int, str], None]:
        """
        Create a progress callback for a task.

        Args:
            task_id: The task ID

        Returns:
            Callback function that updates task progress
        """
        def callback(progress: int, message: str) -> None:
            # TODO: Update task progress in database
            logger.debug(f"Task {task_id}: {progress}% - {message}")

        return callback

    async def _complete_task(self, task_id: str, result: Dict[str, Any]) -> None:
        """
        Mark a task as completed.

        Args:
            task_id: The task ID
            result: Task result data
        """
        logger.info(f"Task {task_id} completed successfully")
        # TODO: Update task in database
        # SET status = 'completed', result = :result, completed_at = NOW()

    async def _fail_task(self, task_id: str, error: str) -> None:
        """
        Mark a task as permanently failed.

        Args:
            task_id: The task ID
            error: Error message
        """
        logger.error(f"Task {task_id} failed permanently: {error}")
        # TODO: Update task in database
        # SET status = 'failed', result = :error, completed_at = NOW()

    async def _schedule_retry(
        self, task_id: str, attempts: int, error: Exception
    ) -> None:
        """
        Schedule a task for retry with backoff.

        Args:
            task_id: The task ID
            attempts: Number of attempts so far
            error: The error that triggered the retry
        """
        delay = get_retry_delay_for_exception(error, attempts)
        retry_at = datetime.now(timezone.utc) + delay

        logger.warning(
            f"Task {task_id} scheduled for retry at {retry_at.isoformat()}: {error}"
        )
        # TODO: Update task in database
        # SET status = 'pending', retry_after = :retry_at


# Worker instance for module-level access
_worker: Optional[TaskWorker] = None


def get_worker() -> TaskWorker:
    """Get or create the singleton worker instance."""
    global _worker
    if _worker is None:
        _worker = TaskWorker()
    return _worker
