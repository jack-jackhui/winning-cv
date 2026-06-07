-- Data Storage Schema for Postgres Backend Migration
-- Jobs, History, User Config, CV Versions tables

-- =============================================================================
-- jobs: Job listings scraped from job boards
-- =============================================================================
CREATE TABLE IF NOT EXISTS jobs (
    id SERIAL PRIMARY KEY,
    user_email VARCHAR(255) NOT NULL DEFAULT 'system',
    job_title VARCHAR(500),
    job_description TEXT,
    job_date TIMESTAMP WITH TIME ZONE,
    job_link VARCHAR(2000) UNIQUE,
    company VARCHAR(255),
    location VARCHAR(255),
    matching_score INTEGER DEFAULT 0,
    cv_link VARCHAR(2000),
    match_reasons TEXT,
    match_suggestions TEXT,
    ats_score INTEGER,
    hr_score INTEGER,
    llm_score INTEGER,
    hr_recommendation TEXT,
    matched_keywords VARCHAR(500),
    missing_keywords VARCHAR(500),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_jobs_job_link ON jobs(job_link);
CREATE INDEX IF NOT EXISTS idx_jobs_user_email ON jobs(user_email);
CREATE INDEX IF NOT EXISTS idx_jobs_created_at ON jobs(created_at DESC);

-- =============================================================================
-- cv_history: CV generation history
-- =============================================================================
CREATE TABLE IF NOT EXISTS cv_history (
    id SERIAL PRIMARY KEY,
    user_email VARCHAR(255) NOT NULL,
    job_title VARCHAR(500),
    job_description TEXT,
    instructions TEXT,
    cv_markdown TEXT,
    cv_pdf_url VARCHAR(2000),
    cv_analysis JSONB,
    analysis_status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_cv_history_user_email ON cv_history(user_email);
CREATE INDEX IF NOT EXISTS idx_cv_history_created_at ON cv_history(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_cv_history_status ON cv_history(analysis_status);

-- =============================================================================
-- user_configs: User preferences and settings (consolidated)
-- Includes job search config + notification preferences
-- =============================================================================
CREATE TABLE IF NOT EXISTS user_configs (
    id SERIAL PRIMARY KEY,
    user_email VARCHAR(255) NOT NULL UNIQUE,

    -- Job search configuration
    base_cv_path VARCHAR(500),
    base_cv_link VARCHAR(2000),
    linkedin_job_url VARCHAR(2000),
    seek_job_url VARCHAR(2000),
    max_jobs_to_scrape INTEGER DEFAULT 10,
    additional_search_term TEXT,
    google_search_term TEXT,
    search_keywords TEXT,
    location VARCHAR(255),
    hours_old INTEGER DEFAULT 168,
    results_wanted INTEGER DEFAULT 10,
    country VARCHAR(100) DEFAULT 'Australia',

    -- Notification preferences
    email_alerts BOOLEAN DEFAULT true,
    telegram_alerts BOOLEAN DEFAULT false,
    wechat_alerts BOOLEAN DEFAULT false,
    weekly_digest BOOLEAN DEFAULT true,
    telegram_chat_id VARCHAR(100),
    wechat_id VARCHAR(100),
    notification_email VARCHAR(255),

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_user_configs_user_email ON user_configs(user_email);

-- =============================================================================
-- cv_versions: CV version tracking and metadata
-- Matches PostgresCVVersionManager expectations
-- =============================================================================
CREATE TABLE IF NOT EXISTS cv_versions (
    id SERIAL PRIMARY KEY,
    version_id VARCHAR(50) NOT NULL UNIQUE,
    user_email VARCHAR(255) NOT NULL,
    version_name VARCHAR(255) NOT NULL,
    auto_category VARCHAR(100),
    user_tags TEXT[] DEFAULT '{}',
    storage_path VARCHAR(500),
    file_size INTEGER DEFAULT 0,
    content_hash VARCHAR(64),
    is_base BOOLEAN DEFAULT false,
    is_archived BOOLEAN DEFAULT false,
    usage_count INTEGER DEFAULT 0,
    response_count INTEGER DEFAULT 0,
    parent_version_id VARCHAR(50),
    source_job_link VARCHAR(2000),
    source_job_title VARCHAR(500),
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_cv_versions_version_id ON cv_versions(version_id);
CREATE INDEX IF NOT EXISTS idx_cv_versions_user_email ON cv_versions(user_email);
CREATE INDEX IF NOT EXISTS idx_cv_versions_category ON cv_versions(auto_category);
CREATE INDEX IF NOT EXISTS idx_cv_versions_is_archived ON cv_versions(is_archived);
CREATE INDEX IF NOT EXISTS idx_cv_versions_created_at ON cv_versions(created_at DESC);

-- =============================================================================
-- search_tasks: Durable job task tracking (replaces file-based /tmp storage)
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

-- =============================================================================
-- CV version analytics helper function
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

-- =============================================================================
-- Trigger to auto-update updated_at on data tables
-- =============================================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'jobs_updated_at') THEN
        CREATE TRIGGER jobs_updated_at BEFORE UPDATE ON jobs
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'cv_history_updated_at') THEN
        CREATE TRIGGER cv_history_updated_at BEFORE UPDATE ON cv_history
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'user_configs_updated_at') THEN
        CREATE TRIGGER user_configs_updated_at BEFORE UPDATE ON user_configs
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'cv_versions_updated_at') THEN
        CREATE TRIGGER cv_versions_updated_at BEFORE UPDATE ON cv_versions
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'search_tasks_updated_at') THEN
        CREATE TRIGGER search_tasks_updated_at BEFORE UPDATE ON search_tasks
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    END IF;
END $$;
