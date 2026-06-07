# Queue Worker Architecture Design

## Overview

This document describes the target architecture for WinningCV's background task processing system, migrating from the current in-process ThreadPoolExecutor approach to a robust, scalable queue-based worker system.

## Current Architecture

### Components
- **FileBasedTaskManager**: JSON file storage in `/tmp/winningcv_search_tasks.json` with file locking
- **ThreadPoolExecutor**: In-process background execution (`_executor` in `api/routes/jobs.py`)
- **Status tracking**: Simple states (pending, running, completed, failed)

### Limitations
1. Tasks are lost on process restart
2. No retry mechanism for transient failures
3. Single-process execution (no horizontal scaling)
4. No observability or monitoring
5. File-based storage is not suitable for production

## Target Architecture

### Database Tables

```sql
-- Core task queue table
CREATE TABLE task_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_type VARCHAR(50) NOT NULL,  -- 'job_search', 'cv_analysis', 'cv_generation', 'notification'
    status VARCHAR(20) NOT NULL DEFAULT 'pending',  -- pending, running, completed, failed, cancelled
    priority INTEGER DEFAULT 0,  -- higher = more urgent

    -- Ownership
    user_id UUID REFERENCES users(id),
    worker_id VARCHAR(100),  -- which worker claimed this task

    -- Task data
    payload JSONB NOT NULL,  -- task-specific input data
    result JSONB,  -- task output or error details

    -- Retry handling
    attempts INTEGER DEFAULT 0,
    max_attempts INTEGER DEFAULT 3,
    retry_after TIMESTAMPTZ,  -- exponential backoff

    -- Progress tracking
    progress INTEGER DEFAULT 0,  -- 0-100
    progress_message TEXT,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for efficient polling
CREATE INDEX idx_task_queue_status_priority ON task_queue(status, priority DESC, created_at);
CREATE INDEX idx_task_queue_user ON task_queue(user_id, created_at DESC);
CREATE INDEX idx_task_queue_worker ON task_queue(worker_id) WHERE status = 'running';
CREATE INDEX idx_task_queue_retry ON task_queue(retry_after) WHERE status = 'pending' AND retry_after IS NOT NULL;
```

### Task States

```
pending -> running -> completed
    |         |
    v         v
cancelled   failed -> pending (retry)
```

- **pending**: Waiting to be picked up by a worker
- **running**: Currently being processed by a worker
- **completed**: Successfully finished
- **failed**: Failed after all retry attempts
- **cancelled**: Manually cancelled by user or system

### Worker Lifecycle

```python
class TaskWorker:
    def __init__(self, worker_id: str, task_types: List[str]):
        self.worker_id = worker_id
        self.task_types = task_types
        self.running = True

    async def run(self):
        """Main worker loop."""
        while self.running:
            task = await self.claim_task()
            if task:
                await self.process_task(task)
            else:
                await asyncio.sleep(POLL_INTERVAL)

    async def claim_task(self) -> Optional[Task]:
        """Atomically claim a pending task."""
        # Use FOR UPDATE SKIP LOCKED for safe concurrent claiming
        return await db.execute("""
            UPDATE task_queue
            SET status = 'running',
                worker_id = :worker_id,
                started_at = NOW(),
                attempts = attempts + 1
            WHERE id = (
                SELECT id FROM task_queue
                WHERE status = 'pending'
                  AND task_type = ANY(:task_types)
                  AND (retry_after IS NULL OR retry_after <= NOW())
                ORDER BY priority DESC, created_at
                FOR UPDATE SKIP LOCKED
                LIMIT 1
            )
            RETURNING *
        """, worker_id=self.worker_id, task_types=self.task_types)

    async def process_task(self, task: Task):
        """Process a claimed task with error handling."""
        try:
            handler = self.get_handler(task.task_type)
            result = await handler.execute(task.payload, self.update_progress)
            await self.complete_task(task.id, result)
        except RetryableError as e:
            await self.schedule_retry(task, e)
        except Exception as e:
            await self.fail_task(task, e)
```

### Retry/Backoff Strategy

```python
def calculate_retry_delay(attempts: int) -> timedelta:
    """Exponential backoff with jitter."""
    base_delay = 30  # seconds
    max_delay = 3600  # 1 hour cap

    delay = min(base_delay * (2 ** attempts), max_delay)
    jitter = random.uniform(0, delay * 0.1)

    return timedelta(seconds=delay + jitter)
```

### Task Types and Handlers

| Task Type | Handler | Timeout | Max Retries |
|-----------|---------|---------|-------------|
| `job_search` | JobSearchHandler | 10 min | 2 |
| `cv_analysis` | CVAnalysisHandler | 5 min | 3 |
| `cv_generation` | CVGenerationHandler | 5 min | 3 |
| `notification` | NotificationHandler | 1 min | 5 |
| `cv_index` | KBIndexHandler | 3 min | 3 |

### Migration Path

#### Phase 1: Database Storage (Low Risk)
1. Create `task_queue` table with migration
2. Add `PostgresTaskManager` implementing same interface as `FileBasedTaskManager`
3. Feature flag to switch between file/postgres storage
4. Keep ThreadPoolExecutor for execution

#### Phase 2: Worker Process (Medium Risk)
1. Extract task handlers into separate module
2. Create standalone worker script (`worker.py`)
3. Run worker alongside API process
4. Add health checks and graceful shutdown

#### Phase 3: Horizontal Scaling (Higher Risk)
1. Multiple worker instances with unique IDs
2. Task-type routing (some workers handle only certain types)
3. Priority queues for time-sensitive tasks
4. Dead letter queue for repeatedly failed tasks

### Observability

#### Metrics to Track
- Queue depth by task type
- Task latency (time from created to completed)
- Worker utilization
- Retry rates and failure rates
- Task throughput (tasks/minute)

#### Logging
```python
logger.info("task_claimed", extra={
    "task_id": task.id,
    "task_type": task.task_type,
    "worker_id": self.worker_id,
    "queue_wait_time": (now - task.created_at).total_seconds()
})
```

#### Health Endpoint
```json
GET /api/v1/health/workers
{
  "workers": [
    {"worker_id": "worker-1", "status": "running", "tasks_processed": 142, "last_heartbeat": "..."},
    {"worker_id": "worker-2", "status": "running", "tasks_processed": 138, "last_heartbeat": "..."}
  ],
  "queue": {
    "pending": 5,
    "running": 2,
    "failed_today": 1
  }
}
```

### API Changes

#### Task Creation (No Change to External API)
```python
async def start_job_search(user: User, config: JobConfig) -> TaskResponse:
    task = await task_manager.create_task(
        task_type="job_search",
        user_id=user.id,
        payload={"config": config.dict()}
    )
    return TaskResponse(task_id=task.id, status="pending")
```

#### Task Status (Minor Enhancement)
```python
async def get_search_status(task_id: str) -> TaskStatus:
    task = await task_manager.get_task(task_id)
    return TaskStatus(
        task_id=task.id,
        status=task.status,
        progress=task.progress,
        message=task.progress_message,
        results_count=task.result.get("count") if task.result else None,
        retry_info={
            "attempts": task.attempts,
            "max_attempts": task.max_attempts,
            "next_retry": task.retry_after.isoformat() if task.retry_after else None
        } if task.status == "pending" and task.attempts > 0 else None
    )
```

### Deployment Considerations

1. **Worker Count**: Start with 2 workers, scale based on queue depth
2. **Resource Limits**: Workers should have memory limits (CV generation is memory-intensive)
3. **Graceful Shutdown**: Workers must finish current task before shutting down
4. **Task Timeouts**: Long-running tasks should be killed and retried
5. **Database Connections**: Workers need their own connection pool

### Rollback Plan

If issues arise:
1. Feature flag to disable new worker system
2. Fall back to in-process ThreadPoolExecutor
3. Tasks in queue can be replayed once fixed

## Implementation Checklist

- [ ] Create database migration for `task_queue` table
- [ ] Implement `PostgresTaskManager` with same interface
- [ ] Add feature flag for storage backend
- [ ] Extract task handlers into `tasks/` module
- [ ] Create worker entrypoint script
- [ ] Add health check endpoints
- [ ] Add structured logging
- [ ] Write integration tests for task lifecycle
- [ ] Document deployment procedure
- [ ] Create monitoring dashboard

## References

- [Postgres Advisory Locks](https://www.postgresql.org/docs/current/explicit-locking.html)
- [Python asyncio Task Groups](https://docs.python.org/3/library/asyncio-task.html)
- [12-Factor App - Concurrency](https://12factor.net/concurrency)
