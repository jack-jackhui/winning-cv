-- Product Telemetry Schema for Funnel Analytics
-- Stores user events for understanding product usage and conversion funnels
-- Safe to run multiple times (uses IF NOT EXISTS pattern)

-- =============================================================================
-- product_events: Core event tracking table
-- =============================================================================
CREATE TABLE IF NOT EXISTS product_events (
    id BIGSERIAL PRIMARY KEY,

    -- User identification (nullable for potential anonymous tracking)
    user_id INTEGER,                      -- auth_user_id from auth service
    user_email VARCHAR(255),              -- Email for easier querying
    session_id VARCHAR(64),               -- Browser session identifier

    -- Event details
    event_name VARCHAR(100) NOT NULL,     -- e.g. 'cv_upload', 'job_search_start'
    funnel_step INTEGER,                  -- Optional step number in funnel (1-14)

    -- Entity references (what was acted upon)
    entity_type VARCHAR(50),              -- e.g. 'cv', 'job', 'search_task'
    entity_id VARCHAR(100),               -- ID of the entity

    -- Additional context
    metadata JSONB DEFAULT '{}',          -- Flexible additional data
    path VARCHAR(500),                    -- URL path where event occurred
    referrer VARCHAR(500),                -- Previous page/referrer

    -- Timestamps
    client_timestamp TIMESTAMP WITH TIME ZONE,  -- When event occurred on client
    server_timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()  -- When server received
);

-- =============================================================================
-- Indexes for efficient querying
-- =============================================================================

-- User and session lookups
CREATE INDEX IF NOT EXISTS idx_events_user_id ON product_events(user_id);
CREATE INDEX IF NOT EXISTS idx_events_user_email ON product_events(user_email);
CREATE INDEX IF NOT EXISTS idx_events_session_id ON product_events(session_id);

-- Event type and funnel analysis
CREATE INDEX IF NOT EXISTS idx_events_name ON product_events(event_name);
CREATE INDEX IF NOT EXISTS idx_events_funnel_step ON product_events(funnel_step);

-- Time-based queries
CREATE INDEX IF NOT EXISTS idx_events_server_timestamp ON product_events(server_timestamp DESC);

-- Composite index for common funnel queries
CREATE INDEX IF NOT EXISTS idx_events_funnel_analysis
    ON product_events(event_name, server_timestamp DESC)
    WHERE funnel_step IS NOT NULL;

-- Composite index for user journey analysis
CREATE INDEX IF NOT EXISTS idx_events_user_journey
    ON product_events(user_id, server_timestamp DESC)
    WHERE user_id IS NOT NULL;

-- =============================================================================
-- Helper function: Get funnel conversion rates for a time period
-- =============================================================================
CREATE OR REPLACE FUNCTION get_funnel_metrics(
    p_start_date TIMESTAMP WITH TIME ZONE DEFAULT NOW() - INTERVAL '7 days',
    p_end_date TIMESTAMP WITH TIME ZONE DEFAULT NOW()
)
RETURNS TABLE (
    funnel_step INTEGER,
    event_name VARCHAR,
    event_count BIGINT,
    unique_users BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        pe.funnel_step,
        pe.event_name,
        COUNT(*)::BIGINT AS event_count,
        COUNT(DISTINCT pe.user_id)::BIGINT AS unique_users
    FROM product_events pe
    WHERE pe.funnel_step IS NOT NULL
      AND pe.server_timestamp BETWEEN p_start_date AND p_end_date
    GROUP BY pe.funnel_step, pe.event_name
    ORDER BY pe.funnel_step;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- Helper function: Get top events by volume
-- =============================================================================
CREATE OR REPLACE FUNCTION get_top_events(
    p_start_date TIMESTAMP WITH TIME ZONE DEFAULT NOW() - INTERVAL '7 days',
    p_end_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    p_limit INTEGER DEFAULT 20
)
RETURNS TABLE (
    event_name VARCHAR,
    event_count BIGINT,
    unique_users BIGINT,
    unique_sessions BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        pe.event_name,
        COUNT(*)::BIGINT AS event_count,
        COUNT(DISTINCT pe.user_id)::BIGINT AS unique_users,
        COUNT(DISTINCT pe.session_id)::BIGINT AS unique_sessions
    FROM product_events pe
    WHERE pe.server_timestamp BETWEEN p_start_date AND p_end_date
    GROUP BY pe.event_name
    ORDER BY event_count DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- Helper function: Get active users/sessions summary
-- =============================================================================
CREATE OR REPLACE FUNCTION get_activity_summary(
    p_start_date TIMESTAMP WITH TIME ZONE DEFAULT NOW() - INTERVAL '7 days',
    p_end_date TIMESTAMP WITH TIME ZONE DEFAULT NOW()
)
RETURNS TABLE (
    period_start TIMESTAMP WITH TIME ZONE,
    period_end TIMESTAMP WITH TIME ZONE,
    total_events BIGINT,
    unique_users BIGINT,
    unique_sessions BIGINT,
    cvs_generated BIGINT,
    cvs_downloaded BIGINT,
    jobs_searched BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        p_start_date AS period_start,
        p_end_date AS period_end,
        COUNT(*)::BIGINT AS total_events,
        COUNT(DISTINCT pe.user_id)::BIGINT AS unique_users,
        COUNT(DISTINCT pe.session_id)::BIGINT AS unique_sessions,
        COUNT(*) FILTER (WHERE pe.event_name = 'cv_generate_complete')::BIGINT AS cvs_generated,
        COUNT(*) FILTER (WHERE pe.event_name = 'cv_download')::BIGINT AS cvs_downloaded,
        COUNT(*) FILTER (WHERE pe.event_name = 'job_search_start')::BIGINT AS jobs_searched
    FROM product_events pe
    WHERE pe.server_timestamp BETWEEN p_start_date AND p_end_date;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- Helper function: Get error events breakdown
-- =============================================================================
CREATE OR REPLACE FUNCTION get_error_events(
    p_start_date TIMESTAMP WITH TIME ZONE DEFAULT NOW() - INTERVAL '7 days',
    p_end_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    p_limit INTEGER DEFAULT 20
)
RETURNS TABLE (
    event_name VARCHAR,
    error_count BIGINT,
    affected_users BIGINT,
    latest_occurrence TIMESTAMP WITH TIME ZONE,
    sample_metadata JSONB
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        pe.event_name,
        COUNT(*)::BIGINT AS error_count,
        COUNT(DISTINCT pe.user_id)::BIGINT AS affected_users,
        MAX(pe.server_timestamp) AS latest_occurrence,
        (SELECT pe2.metadata FROM product_events pe2
         WHERE pe2.event_name = pe.event_name
         ORDER BY pe2.server_timestamp DESC LIMIT 1) AS sample_metadata
    FROM product_events pe
    WHERE pe.event_name IN (
        'search_empty_results',
        'cv_generation_failed',
        'validation_error',
        'api_error'
    )
    AND pe.server_timestamp BETWEEN p_start_date AND p_end_date
    GROUP BY pe.event_name
    ORDER BY error_count DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

-- Mark migration complete
DO $$
BEGIN
    RAISE NOTICE 'Product telemetry migration (05) completed successfully';
END $$;
