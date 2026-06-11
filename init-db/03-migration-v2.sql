-- Migration V2: Schema alignment for PostgresManager compatibility
-- Run this to upgrade existing databases to match 02-data-storage-schema.sql v2
-- Safe to run multiple times (uses IF NOT EXISTS / ADD IF NOT EXISTS pattern)

-- =============================================================================
-- user_configs: Add missing columns for job search config
-- =============================================================================
DO $$
BEGIN
    -- Job search config fields
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='user_configs' AND column_name='base_cv_path') THEN
        ALTER TABLE user_configs ADD COLUMN base_cv_path VARCHAR(500);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='user_configs' AND column_name='base_cv_link') THEN
        ALTER TABLE user_configs ADD COLUMN base_cv_link VARCHAR(2000);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='user_configs' AND column_name='linkedin_job_url') THEN
        ALTER TABLE user_configs ADD COLUMN linkedin_job_url VARCHAR(2000);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='user_configs' AND column_name='seek_job_url') THEN
        ALTER TABLE user_configs ADD COLUMN seek_job_url VARCHAR(2000);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='user_configs' AND column_name='max_jobs_to_scrape') THEN
        ALTER TABLE user_configs ADD COLUMN max_jobs_to_scrape INTEGER DEFAULT 10;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='user_configs' AND column_name='additional_search_term') THEN
        ALTER TABLE user_configs ADD COLUMN additional_search_term TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='user_configs' AND column_name='google_search_term') THEN
        ALTER TABLE user_configs ADD COLUMN google_search_term TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='user_configs' AND column_name='results_wanted') THEN
        ALTER TABLE user_configs ADD COLUMN results_wanted INTEGER DEFAULT 10;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='user_configs' AND column_name='country') THEN
        ALTER TABLE user_configs ADD COLUMN country VARCHAR(100) DEFAULT 'Australia';
    END IF;

    -- Notification preference fields
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='user_configs' AND column_name='wechat_alerts') THEN
        ALTER TABLE user_configs ADD COLUMN wechat_alerts BOOLEAN DEFAULT false;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='user_configs' AND column_name='weekly_digest') THEN
        ALTER TABLE user_configs ADD COLUMN weekly_digest BOOLEAN DEFAULT true;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='user_configs' AND column_name='wechat_id') THEN
        ALTER TABLE user_configs ADD COLUMN wechat_id VARCHAR(100);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='user_configs' AND column_name='notification_email') THEN
        ALTER TABLE user_configs ADD COLUMN notification_email VARCHAR(255);
    END IF;

    -- Migrate cv_path -> base_cv_path if cv_path exists
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='user_configs' AND column_name='cv_path') THEN
        UPDATE user_configs SET base_cv_path = cv_path WHERE base_cv_path IS NULL AND cv_path IS NOT NULL;
    END IF;
END $$;

-- =============================================================================
-- cv_versions: Add missing columns for PostgresCVVersionManager
-- =============================================================================
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='cv_versions' AND column_name='version_id') THEN
        ALTER TABLE cv_versions ADD COLUMN version_id VARCHAR(50);
        -- Populate version_id for existing rows
        UPDATE cv_versions SET version_id = 'cv_' || SUBSTRING(MD5(RANDOM()::TEXT), 1, 12) WHERE version_id IS NULL;
        ALTER TABLE cv_versions ALTER COLUMN version_id SET NOT NULL;
        CREATE UNIQUE INDEX IF NOT EXISTS idx_cv_versions_version_id ON cv_versions(version_id);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='cv_versions' AND column_name='auto_category') THEN
        ALTER TABLE cv_versions ADD COLUMN auto_category VARCHAR(100);
        -- Migrate category -> auto_category if category exists
        IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='cv_versions' AND column_name='category') THEN
            UPDATE cv_versions SET auto_category = category WHERE auto_category IS NULL AND category IS NOT NULL;
        END IF;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='cv_versions' AND column_name='user_tags') THEN
        ALTER TABLE cv_versions ADD COLUMN user_tags TEXT[] DEFAULT '{}';
        -- Migrate tags (comma-separated) -> user_tags (array) if tags exists
        IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='cv_versions' AND column_name='tags') THEN
            UPDATE cv_versions SET user_tags = STRING_TO_ARRAY(tags, ',')
            WHERE user_tags = '{}' AND tags IS NOT NULL AND tags != '';
        END IF;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='cv_versions' AND column_name='storage_path') THEN
        ALTER TABLE cv_versions ADD COLUMN storage_path VARCHAR(500);
        -- Migrate file_path -> storage_path if file_path exists
        IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='cv_versions' AND column_name='file_path') THEN
            UPDATE cv_versions SET storage_path = file_path WHERE storage_path IS NULL AND file_path IS NOT NULL;
        END IF;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='cv_versions' AND column_name='file_size') THEN
        ALTER TABLE cv_versions ADD COLUMN file_size INTEGER DEFAULT 0;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='cv_versions' AND column_name='content_hash') THEN
        ALTER TABLE cv_versions ADD COLUMN content_hash VARCHAR(64);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='cv_versions' AND column_name='source_job_link') THEN
        ALTER TABLE cv_versions ADD COLUMN source_job_link VARCHAR(2000);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='cv_versions' AND column_name='source_job_title') THEN
        ALTER TABLE cv_versions ADD COLUMN source_job_title VARCHAR(500);
    END IF;

    -- Update parent_version_id to VARCHAR if it's currently INTEGER
    -- This is a more complex migration - need to handle FK
END $$;

-- =============================================================================
-- search_tasks: Create if not exists (new table)
-- =============================================================================
CREATE TABLE IF NOT EXISTS search_tasks (
    id SERIAL PRIMARY KEY,
    task_id VARCHAR(50) NOT NULL UNIQUE,
    user_email VARCHAR(255) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    progress INTEGER DEFAULT 0,
    message TEXT,
    results_count INTEGER,
    error_details TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_search_tasks_task_id ON search_tasks(task_id);
CREATE INDEX IF NOT EXISTS idx_search_tasks_user_email ON search_tasks(user_email);
CREATE INDEX IF NOT EXISTS idx_search_tasks_status ON search_tasks(status);
CREATE INDEX IF NOT EXISTS idx_search_tasks_created_at ON search_tasks(created_at DESC);

-- Add trigger if not exists
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'search_tasks_updated_at') THEN
        CREATE TRIGGER search_tasks_updated_at BEFORE UPDATE ON search_tasks
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    END IF;
END $$;

-- =============================================================================
-- CV version analytics helper function (create or replace)
-- =============================================================================
CREATE OR REPLACE FUNCTION get_cv_analytics(p_user_email VARCHAR)
RETURNS TABLE (
    total_versions INTEGER,
    active_versions INTEGER,
    archived_versions INTEGER,
    total_usage INTEGER,
    total_responses INTEGER,
    overall_response_rate NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        COUNT(*)::INTEGER AS total_versions,
        COUNT(*) FILTER (WHERE NOT is_archived)::INTEGER AS active_versions,
        COUNT(*) FILTER (WHERE is_archived)::INTEGER AS archived_versions,
        COALESCE(SUM(usage_count), 0)::INTEGER AS total_usage,
        COALESCE(SUM(response_count), 0)::INTEGER AS total_responses,
        CASE
            WHEN COALESCE(SUM(usage_count), 0) > 0
            THEN ROUND(COALESCE(SUM(response_count), 0)::NUMERIC / SUM(usage_count) * 100, 1)
            ELSE 0
        END AS overall_response_rate
    FROM cv_versions
    WHERE user_email = p_user_email;
END;
$$ LANGUAGE plpgsql;

-- Mark migration complete
DO $$
BEGIN
    RAISE NOTICE 'Migration V2 completed successfully';
END $$;


-- Application tracking state (safe for existing deployments)
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS application_status VARCHAR(40) DEFAULT 'saved';
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS application_notes TEXT;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS applied_at TIMESTAMP WITH TIME ZONE;
CREATE INDEX IF NOT EXISTS idx_jobs_application_status ON jobs(application_status);
