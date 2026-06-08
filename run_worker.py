#!/usr/bin/env python3
"""
WinningCV Background Worker
===========================

Standalone worker process that processes tasks from the Postgres task queue.
Can run as a daemon alongside the API server or as a one-shot processor.

Usage:
    # Run worker in loop mode (default)
    python run_worker.py

    # Process one task and exit
    python run_worker.py --once

    # Custom worker ID and poll interval
    python run_worker.py --worker-id worker-1 --poll-interval 10

    # Process only specific task types
    python run_worker.py --task-types job_search cv_analysis

    # Dry run mode (no actual processing)
    python run_worker.py --dry-run
"""

import argparse
import asyncio
import logging
import os
import signal
import sys
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api.tasks.state import TaskState, TaskType, get_task_config
from api.tasks.retry import (
    RetryableError,
    PermanentError,
    calculate_retry_delay,
    should_retry_exception,
)
from data_store.postgres_manager import get_postgres_task_queue, PostgresTaskQueue

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("worker")


class TaskHandlerRegistry:
    """Registry of task type handlers."""

    def __init__(self):
        self._handlers: Dict[str, Callable] = {}

    def register(self, task_type: str, handler: Callable):
        """Register a handler for a task type."""
        self._handlers[task_type] = handler
        logger.info(f"Registered handler for task type: {task_type}")

    def get(self, task_type: str) -> Optional[Callable]:
        """Get handler for a task type."""
        return self._handlers.get(task_type)

    def list_types(self) -> List[str]:
        """List registered task types."""
        return list(self._handlers.keys())


# Global handler registry
_registry = TaskHandlerRegistry()


def register_handler(task_type: str):
    """Decorator to register a task handler."""
    def decorator(func: Callable):
        _registry.register(task_type, func)
        return func
    return decorator


# ============================================================================
# Task Handlers
# ============================================================================

@register_handler("job_search")
async def handle_job_search(
    task_id: str,
    payload: Dict[str, Any],
    progress_callback: Callable[[int, str], None],
) -> Dict[str, Any]:
    """
    Handle job search task.

    This is a stub - actual implementation would import and run JobProcessor.
    The existing job search flow runs synchronously in a thread pool from the API.
    Full integration requires careful testing to ensure compatibility.
    """
    logger.info(f"[{task_id}] Job search handler - payload: {payload}")
    progress_callback(10, "Initializing job search...")

    # Stub: In production, this would:
    # 1. Load user config from payload
    # 2. Initialize JobProcessor
    # 3. Run processor.process_jobs()
    # 4. Return results

    progress_callback(50, "Processing jobs...")
    await asyncio.sleep(0.1)  # Simulate work

    progress_callback(100, "Job search complete")
    return {"status": "stub", "message": "Job search handler stub - integration pending"}


@register_handler("cv_analysis")
async def handle_cv_analysis(
    task_id: str,
    payload: Dict[str, Any],
    progress_callback: Callable[[int, str], None],
) -> Dict[str, Any]:
    """Handle CV analysis task (stub)."""
    logger.info(f"[{task_id}] CV analysis handler - payload: {payload}")
    progress_callback(50, "Analyzing CV...")
    await asyncio.sleep(0.1)
    progress_callback(100, "Analysis complete")
    return {"status": "stub", "message": "CV analysis handler stub"}


@register_handler("cv_generation")
async def handle_cv_generation(
    task_id: str,
    payload: Dict[str, Any],
    progress_callback: Callable[[int, str], None],
) -> Dict[str, Any]:
    """Handle CV generation task (stub)."""
    logger.info(f"[{task_id}] CV generation handler - payload: {payload}")
    progress_callback(50, "Generating CV...")
    await asyncio.sleep(0.1)
    progress_callback(100, "Generation complete")
    return {"status": "stub", "message": "CV generation handler stub"}


@register_handler("notification")
async def handle_notification(
    task_id: str,
    payload: Dict[str, Any],
    progress_callback: Callable[[int, str], None],
) -> Dict[str, Any]:
    """Handle notification task (stub)."""
    logger.info(f"[{task_id}] Notification handler - payload: {payload}")
    progress_callback(100, "Notification sent")
    return {"status": "stub", "message": "Notification handler stub"}


# ============================================================================
# Worker Implementation
# ============================================================================

class Worker:
    """
    Background task worker that processes tasks from the Postgres queue.

    Features:
    - Atomic task claiming with FOR UPDATE SKIP LOCKED
    - Graceful shutdown on SIGTERM/SIGINT
    - Configurable poll interval and task types
    - Heartbeat for long-running tasks
    - Retry with exponential backoff
    """

    def __init__(
        self,
        worker_id: str = None,
        task_types: List[str] = None,
        poll_interval: float = 5.0,
        heartbeat_interval: float = 30.0,
        dry_run: bool = False,
    ):
        self.worker_id = worker_id or f"worker-{uuid.uuid4().hex[:8]}"
        self.task_types = task_types
        self.poll_interval = poll_interval
        self.heartbeat_interval = heartbeat_interval
        self.dry_run = dry_run

        self.queue: PostgresTaskQueue = get_postgres_task_queue()
        self.running = False
        self.current_task_id: Optional[str] = None

        logger.info(
            f"Worker {self.worker_id} initialized "
            f"(types={task_types or 'all'}, poll={poll_interval}s, dry_run={dry_run})"
        )

    async def start(self):
        """Start the worker loop."""
        self.running = True
        logger.info(f"Worker {self.worker_id} starting")

        # Set up signal handlers
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, self._handle_shutdown)

        try:
            await self._run_loop()
        except Exception as e:
            logger.error(f"Worker error: {e}", exc_info=True)
        finally:
            self.running = False
            logger.info(f"Worker {self.worker_id} stopped")

    async def run_once(self) -> bool:
        """Process one task and return."""
        task = self._claim_task()
        if task:
            await self._process_task(task)
            return True
        return False

    def stop(self):
        """Signal the worker to stop gracefully."""
        logger.info(f"Worker {self.worker_id} stopping gracefully")
        self.running = False

    def _handle_shutdown(self):
        """Handle shutdown signals."""
        logger.info(f"Worker {self.worker_id} received shutdown signal")
        self.running = False

    async def _run_loop(self):
        """Main worker loop."""
        # Release any stale locks on startup
        self.queue.release_stale_locks()

        while self.running:
            try:
                task = self._claim_task()
                if task:
                    await self._process_task(task)
                else:
                    await asyncio.sleep(self.poll_interval)
            except Exception as e:
                logger.error(f"Worker loop error: {e}", exc_info=True)
                await asyncio.sleep(self.poll_interval)

    def _claim_task(self) -> Optional[Dict[str, Any]]:
        """Claim the next available task."""
        if self.dry_run:
            logger.debug("Dry run mode - not claiming tasks")
            return None

        return self.queue.claim_task(self.worker_id, self.task_types)

    async def _process_task(self, task: Dict[str, Any]):
        """Process a claimed task."""
        task_id = task["task_id"]
        task_type = task["task_type"]
        payload = task.get("payload", {})
        attempts = task.get("attempts", 1)
        max_attempts = task.get("max_attempts", 3)

        self.current_task_id = task_id
        logger.info(
            f"Processing task {task_id} (type={task_type}, "
            f"attempt={attempts}/{max_attempts})"
        )

        handler = _registry.get(task_type)
        if not handler:
            logger.error(f"No handler for task type: {task_type}")
            self.queue.fail_task(task_id, self.worker_id, f"No handler for type: {task_type}")
            self.current_task_id = None
            return

        # Create progress callback
        def progress_callback(progress: int, message: str):
            logger.debug(f"[{task_id}] Progress: {progress}% - {message}")
            # Heartbeat on progress updates
            self.queue.heartbeat(task_id, self.worker_id)

        try:
            # Execute handler
            result = await handler(task_id, payload, progress_callback)
            self.queue.complete_task(task_id, self.worker_id, result)

        except RetryableError as e:
            self._handle_failure(task_id, attempts, max_attempts, e, retry=True)

        except PermanentError as e:
            self._handle_failure(task_id, attempts, max_attempts, e, retry=False)

        except Exception as e:
            retry = should_retry_exception(e) and attempts < max_attempts
            self._handle_failure(task_id, attempts, max_attempts, e, retry=retry)

        finally:
            self.current_task_id = None

    def _handle_failure(
        self,
        task_id: str,
        attempts: int,
        max_attempts: int,
        error: Exception,
        retry: bool,
    ):
        """Handle task failure with optional retry."""
        error_msg = str(error)

        if retry and attempts < max_attempts:
            delay = calculate_retry_delay(attempts)
            retry_at = datetime.now(timezone.utc) + delay
            logger.warning(
                f"Task {task_id} failed (attempt {attempts}/{max_attempts}), "
                f"retry at {retry_at.isoformat()}: {error_msg}"
            )
            self.queue.fail_task(task_id, self.worker_id, error_msg, retry_after=retry_at)
        else:
            logger.error(f"Task {task_id} permanently failed: {error_msg}")
            self.queue.fail_task(task_id, self.worker_id, error_msg)


# ============================================================================
# CLI
# ============================================================================

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="WinningCV Background Worker",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "--worker-id",
        help="Unique worker identifier (default: auto-generated)",
    )

    parser.add_argument(
        "--task-types",
        nargs="+",
        choices=[t.value for t in TaskType],
        help="Task types to process (default: all)",
    )

    parser.add_argument(
        "--poll-interval",
        type=float,
        default=5.0,
        help="Seconds between queue polls when empty (default: 5)",
    )

    parser.add_argument(
        "--once",
        action="store_true",
        help="Process one task and exit",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run without processing tasks (for testing)",
    )

    parser.add_argument(
        "--release-stale",
        action="store_true",
        help="Release stale locks and exit",
    )

    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="Cleanup old completed tasks and exit",
    )

    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show queue statistics and exit",
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable debug logging",
    )

    return parser.parse_args()


async def main():
    """Main entry point."""
    args = parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    queue = get_postgres_task_queue()

    # Utility commands
    if args.stats:
        stats = queue.get_queue_stats()
        print("Queue Statistics:")
        for key, value in stats.items():
            print(f"  {key}: {value}")
        return

    if args.release_stale:
        released = queue.release_stale_locks()
        print(f"Released {released} stale locks")
        return

    if args.cleanup:
        deleted = queue.cleanup_old_tasks()
        print(f"Cleaned up {deleted} old tasks")
        return

    # Run worker
    worker = Worker(
        worker_id=args.worker_id,
        task_types=args.task_types,
        poll_interval=args.poll_interval,
        dry_run=args.dry_run,
    )

    if args.once:
        found = await worker.run_once()
        sys.exit(0 if found else 1)
    else:
        await worker.start()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Worker interrupted")
        sys.exit(0)
