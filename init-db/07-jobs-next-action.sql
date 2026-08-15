-- Add structured calendar-date scheduling to existing job applications.
ALTER TABLE jobs
    ADD COLUMN IF NOT EXISTS next_action_at DATE;

-- Safely convert deployments that applied the earlier timestamp prototype.
DO $$
DECLARE
    column_type TEXT;
BEGIN
    SELECT data_type
      INTO column_type
      FROM information_schema.columns
     WHERE table_schema = current_schema()
       AND table_name = 'jobs'
       AND column_name = 'next_action_at';

    IF column_type = 'timestamp with time zone' THEN
        EXECUTE 'ALTER TABLE jobs ALTER COLUMN next_action_at TYPE DATE '
             || 'USING (next_action_at AT TIME ZONE ''UTC'')::date';
    ELSIF column_type = 'timestamp without time zone' THEN
        EXECUTE 'ALTER TABLE jobs ALTER COLUMN next_action_at TYPE DATE '
             || 'USING next_action_at::date';
    END IF;
END $$;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
          FROM pg_indexes
         WHERE schemaname = current_schema()
           AND indexname = 'idx_jobs_user_next_action'
           AND indexdef NOT LIKE '%(user_email, next_action_at, created_at DESC, id)%'
    ) THEN
        EXECUTE 'DROP INDEX idx_jobs_user_next_action';
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_jobs_user_next_action
    ON jobs(user_email, next_action_at, created_at DESC, id);
