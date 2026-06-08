-- Task Queue Schema for Background Worker Processing
-- Provides durable, distributed task queue with atomic claiming using FOR UPDATE SKIP LOCKED
-- Safe to run multiple times (uses IF NOT EXISTS pattern)

-- =============================================================================
-- task_queue: Generic background task queue
-- Supports priority-based processing, retries, and worker locking
-- =============================================================================
CREATE TABLE IF NOT EXISTS task_queue (
    id SERIAL PRIMARY KEY,

    -- Task identification
    task_id VARCHAR(50) NOT NULL UNIQUE,
    task_type VARCHAR(50) NOT NULL,

    -- State management (pending, running, completed, failed, cancelled)
    state VARCHAR(20) NOT NULL DEFAULT 'pending',
    priority INTEGER NOT NULL DEFAULT 0,  -- Higher = more urgent

    -- Payload and result (JSONB for flexibility)
    payload JSONB DEFAULT '{}',
    result JSONB,
    error TEXT,

    -- Retry management
    attempts INTEGER NOT NULL DEFAULT 0,
    max_attempts INTEGER NOT NULL DEFAULT 3,
    run_after TIMESTAMP WITH TIME ZONE,  -- For delayed execution or retry backoff

    -- Worker locking (for concurrent worker safety)
    locked_by VARCHAR(100),
    locked_at TIMESTAMP WITH TIME ZONE,

    -- Correlation
    user_email VARCHAR(255),
    correlation_id VARCHAR(100),  -- Links to search_tasks.task_id or other external refs

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE
);

-- Indexes for efficient queue operations
CREATE INDEX IF NOT EXISTS idx_task_queue_task_id ON task_queue(task_id);
CREATE INDEX IF NOT EXISTS idx_task_queue_state ON task_queue(state);
CREATE INDEX IF NOT EXISTS idx_task_queue_task_type ON task_queue(task_type);
CREATE INDEX IF NOT EXISTS idx_task_queue_user_email ON task_queue(user_email);
CREATE INDEX IF NOT EXISTS idx_task_queue_correlation_id ON task_queue(correlation_id);

-- Composite index for claim query: pending tasks ordered by priority and age
CREATE INDEX IF NOT EXISTS idx_task_queue_claimable
    ON task_queue(state, priority DESC, created_at)
    WHERE state = 'pending';

-- Index for finding locked tasks (for timeout detection)
CREATE INDEX IF NOT EXISTS idx_task_queue_locked
    ON task_queue(locked_at)
    WHERE locked_by IS NOT NULL;

-- Index for cleanup of old completed tasks
CREATE INDEX IF NOT EXISTS idx_task_queue_completed
    ON task_queue(completed_at)
    WHERE state IN ('completed', 'failed', 'cancelled');

-- =============================================================================
-- Trigger: Auto-update updated_at timestamp
-- =============================================================================
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'task_queue_updated_at') THEN
        CREATE TRIGGER task_queue_updated_at
            BEFORE UPDATE ON task_queue
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    END IF;
END $$;

-- =============================================================================
-- Helper function: Claim next available task atomically
-- Uses FOR UPDATE SKIP LOCKED for safe concurrent access
-- =============================================================================
CREATE OR REPLACE FUNCTION claim_next_task(
    p_worker_id VARCHAR,
    p_task_types VARCHAR[] DEFAULT NULL
)
RETURNS TABLE (
    task_id VARCHAR,
    task_type VARCHAR,
    payload JSONB,
    attempts INTEGER,
    max_attempts INTEGER,
    user_email VARCHAR,
    correlation_id VARCHAR
) AS $$
DECLARE
    v_task_id VARCHAR;
BEGIN
    -- Atomically claim one task
    UPDATE task_queue t
    SET
        state = 'running',
        locked_by = p_worker_id,
        locked_at = NOW(),
        attempts = t.attempts + 1,
        updated_at = NOW()
    WHERE t.id = (
        SELECT sq.id
        FROM task_queue sq
        WHERE sq.state = 'pending'
          AND (sq.run_after IS NULL OR sq.run_after <= NOW())
          AND (p_task_types IS NULL OR sq.task_type = ANY(p_task_types))
        ORDER BY sq.priority DESC, sq.created_at
        FOR UPDATE SKIP LOCKED
        LIMIT 1
    )
    RETURNING t.task_id INTO v_task_id;

    -- Return the claimed task details
    IF v_task_id IS NOT NULL THEN
        RETURN QUERY
        SELECT
            t.task_id,
            t.task_type,
            t.payload,
            t.attempts,
            t.max_attempts,
            t.user_email,
            t.correlation_id
        FROM task_queue t
        WHERE t.task_id = v_task_id;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- Helper function: Complete a task with result
-- =============================================================================
CREATE OR REPLACE FUNCTION complete_task(
    p_task_id VARCHAR,
    p_worker_id VARCHAR,
    p_result JSONB DEFAULT NULL
)
RETURNS BOOLEAN AS $$
DECLARE
    v_updated INTEGER;
BEGIN
    UPDATE task_queue
    SET
        state = 'completed',
        result = p_result,
        completed_at = NOW(),
        locked_by = NULL,
        locked_at = NULL,
        updated_at = NOW()
    WHERE task_id = p_task_id
      AND locked_by = p_worker_id
      AND state = 'running';

    GET DIAGNOSTICS v_updated = ROW_COUNT;
    RETURN v_updated > 0;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- Helper function: Fail a task (optionally schedule retry)
-- =============================================================================
CREATE OR REPLACE FUNCTION fail_task(
    p_task_id VARCHAR,
    p_worker_id VARCHAR,
    p_error TEXT,
    p_retry_after TIMESTAMP WITH TIME ZONE DEFAULT NULL
)
RETURNS BOOLEAN AS $$
DECLARE
    v_attempts INTEGER;
    v_max_attempts INTEGER;
    v_new_state VARCHAR;
    v_updated INTEGER;
BEGIN
    -- Get current attempt info
    SELECT attempts, max_attempts
    INTO v_attempts, v_max_attempts
    FROM task_queue
    WHERE task_id = p_task_id;

    -- Determine if retry is possible
    IF p_retry_after IS NOT NULL AND v_attempts < v_max_attempts THEN
        v_new_state := 'pending';
    ELSE
        v_new_state := 'failed';
    END IF;

    UPDATE task_queue
    SET
        state = v_new_state,
        error = p_error,
        run_after = p_retry_after,
        locked_by = NULL,
        locked_at = NULL,
        completed_at = CASE WHEN v_new_state = 'failed' THEN NOW() ELSE NULL END,
        updated_at = NOW()
    WHERE task_id = p_task_id
      AND locked_by = p_worker_id
      AND state = 'running';

    GET DIAGNOSTICS v_updated = ROW_COUNT;
    RETURN v_updated > 0;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- Helper function: Heartbeat to refresh lock (prevent timeout)
-- =============================================================================
CREATE OR REPLACE FUNCTION heartbeat_task(
    p_task_id VARCHAR,
    p_worker_id VARCHAR
)
RETURNS BOOLEAN AS $$
DECLARE
    v_updated INTEGER;
BEGIN
    UPDATE task_queue
    SET locked_at = NOW(), updated_at = NOW()
    WHERE task_id = p_task_id
      AND locked_by = p_worker_id
      AND state = 'running';

    GET DIAGNOSTICS v_updated = ROW_COUNT;
    RETURN v_updated > 0;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- Helper function: Release stale locks (for crashed workers)
-- Returns number of tasks released
-- =============================================================================
CREATE OR REPLACE FUNCTION release_stale_locks(
    p_timeout_minutes INTEGER DEFAULT 30
)
RETURNS INTEGER AS $$
DECLARE
    v_released INTEGER;
BEGIN
    UPDATE task_queue
    SET
        state = 'pending',
        locked_by = NULL,
        locked_at = NULL,
        updated_at = NOW()
    WHERE state = 'running'
      AND locked_at < NOW() - (p_timeout_minutes || ' minutes')::INTERVAL;

    GET DIAGNOSTICS v_released = ROW_COUNT;
    RETURN v_released;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- Helper function: Cleanup old completed tasks
-- =============================================================================
CREATE OR REPLACE FUNCTION cleanup_old_queue_tasks(
    p_max_age_hours INTEGER DEFAULT 168  -- 7 days
)
RETURNS INTEGER AS $$
DECLARE
    v_deleted INTEGER;
BEGIN
    DELETE FROM task_queue
    WHERE state IN ('completed', 'failed', 'cancelled')
      AND completed_at < NOW() - (p_max_age_hours || ' hours')::INTERVAL;

    GET DIAGNOSTICS v_deleted = ROW_COUNT;
    RETURN v_deleted;
END;
$$ LANGUAGE plpgsql;

-- Mark migration complete
DO $$
BEGIN
    RAISE NOTICE 'Task queue migration (04) completed successfully';
END $$;
