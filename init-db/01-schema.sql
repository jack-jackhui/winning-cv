-- CV Knowledge Base Schema
-- Full-text search enabled PostgreSQL schema for CV content indexing

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- =============================================================================
-- cv_extracted_content: Main table linking to Airtable cv_versions
-- =============================================================================
CREATE TABLE IF NOT EXISTS cv_extracted_content (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    cv_version_id VARCHAR(255) NOT NULL UNIQUE,  -- Links to Airtable cv_versions record ID
    user_email VARCHAR(255) NOT NULL,
    version_name VARCHAR(255),
    raw_content TEXT NOT NULL,
    content_hash VARCHAR(64) NOT NULL,  -- SHA-256 hash for deduplication
    indexed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Full-text search vector for the entire CV content
    search_vector TSVECTOR GENERATED ALWAYS AS (
        setweight(to_tsvector('english', COALESCE(version_name, '')), 'A') ||
        setweight(to_tsvector('english', COALESCE(raw_content, '')), 'B')
    ) STORED
);

-- Indexes for cv_extracted_content
CREATE INDEX IF NOT EXISTS idx_cv_content_user_email ON cv_extracted_content(user_email);
CREATE INDEX IF NOT EXISTS idx_cv_content_version_id ON cv_extracted_content(cv_version_id);
CREATE INDEX IF NOT EXISTS idx_cv_content_hash ON cv_extracted_content(content_hash);
CREATE INDEX IF NOT EXISTS idx_cv_content_search ON cv_extracted_content USING GIN(search_vector);
CREATE INDEX IF NOT EXISTS idx_cv_content_indexed_at ON cv_extracted_content(indexed_at DESC);

-- =============================================================================
-- cv_sections: Normalized sections extracted from CVs
-- =============================================================================
CREATE TABLE IF NOT EXISTS cv_sections (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    cv_content_id UUID NOT NULL REFERENCES cv_extracted_content(id) ON DELETE CASCADE,
    section_type VARCHAR(50) NOT NULL,  -- summary, experience, skills, education, projects, certifications
    section_title VARCHAR(255),
    content TEXT NOT NULL,
    position_order INT DEFAULT 0,  -- Order within the CV
    metadata JSONB DEFAULT '{}',  -- Additional structured data (dates, company names, etc.)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Full-text search vector for section content
    search_vector TSVECTOR GENERATED ALWAYS AS (
        setweight(to_tsvector('english', COALESCE(section_title, '')), 'A') ||
        setweight(to_tsvector('english', COALESCE(content, '')), 'B')
    ) STORED
);

-- Indexes for cv_sections
CREATE INDEX IF NOT EXISTS idx_sections_content_id ON cv_sections(cv_content_id);
CREATE INDEX IF NOT EXISTS idx_sections_type ON cv_sections(section_type);
CREATE INDEX IF NOT EXISTS idx_sections_user ON cv_sections(cv_content_id, section_type);
CREATE INDEX IF NOT EXISTS idx_sections_search ON cv_sections USING GIN(search_vector);
CREATE INDEX IF NOT EXISTS idx_sections_metadata ON cv_sections USING GIN(metadata);

-- =============================================================================
-- cv_experience_bullets: Individual experience bullet points for fine-grained search
-- =============================================================================
CREATE TABLE IF NOT EXISTS cv_experience_bullets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    section_id UUID NOT NULL REFERENCES cv_sections(id) ON DELETE CASCADE,
    bullet_text TEXT NOT NULL,
    company_name VARCHAR(255),
    job_title VARCHAR(255),
    skills_mentioned TEXT[],  -- Array of skills extracted from this bullet
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Full-text search vector
    search_vector TSVECTOR GENERATED ALWAYS AS (
        setweight(to_tsvector('english', COALESCE(job_title, '')), 'A') ||
        setweight(to_tsvector('english', COALESCE(company_name, '')), 'A') ||
        setweight(to_tsvector('english', COALESCE(bullet_text, '')), 'B')
    ) STORED
);

-- Indexes for cv_experience_bullets
CREATE INDEX IF NOT EXISTS idx_bullets_section_id ON cv_experience_bullets(section_id);
CREATE INDEX IF NOT EXISTS idx_bullets_search ON cv_experience_bullets USING GIN(search_vector);
CREATE INDEX IF NOT EXISTS idx_bullets_skills ON cv_experience_bullets USING GIN(skills_mentioned);
CREATE INDEX IF NOT EXISTS idx_bullets_company ON cv_experience_bullets(company_name);
CREATE INDEX IF NOT EXISTS idx_bullets_title ON cv_experience_bullets(job_title);

-- =============================================================================
-- Trigger: Auto-update updated_at timestamp
-- =============================================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_cv_content_updated_at
    BEFORE UPDATE ON cv_extracted_content
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- =============================================================================
-- Helper function: Search across all CV content for a user
-- =============================================================================
CREATE OR REPLACE FUNCTION search_cv_content(
    p_user_email VARCHAR,
    p_query TEXT,
    p_limit INT DEFAULT 20
)
RETURNS TABLE (
    cv_version_id VARCHAR,
    version_name VARCHAR,
    section_type VARCHAR,
    content TEXT,
    rank REAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        c.cv_version_id,
        c.version_name,
        s.section_type,
        s.content,
        ts_rank(s.search_vector, websearch_to_tsquery('english', p_query)) AS rank
    FROM cv_extracted_content c
    JOIN cv_sections s ON s.cv_content_id = c.id
    WHERE c.user_email = p_user_email
      AND s.search_vector @@ websearch_to_tsquery('english', p_query)
    ORDER BY rank DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- Helper function: Get all experience bullets for a user with optional skill filter
-- =============================================================================
CREATE OR REPLACE FUNCTION get_experience_bullets(
    p_user_email VARCHAR,
    p_skills TEXT[] DEFAULT NULL,
    p_limit INT DEFAULT 100
)
RETURNS TABLE (
    cv_version_id VARCHAR,
    company_name VARCHAR,
    job_title VARCHAR,
    bullet_text TEXT,
    skills_mentioned TEXT[]
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        c.cv_version_id,
        b.company_name,
        b.job_title,
        b.bullet_text,
        b.skills_mentioned
    FROM cv_extracted_content c
    JOIN cv_sections s ON s.cv_content_id = c.id
    JOIN cv_experience_bullets b ON b.section_id = s.id
    WHERE c.user_email = p_user_email
      AND (p_skills IS NULL OR b.skills_mentioned && p_skills)
    ORDER BY c.indexed_at DESC, s.position_order, b.id
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- View: Unified experience across all CV versions for a user
-- =============================================================================
CREATE OR REPLACE VIEW v_unified_experience AS
SELECT
    c.user_email,
    c.cv_version_id,
    c.version_name,
    s.section_type,
    s.section_title,
    s.content,
    s.metadata,
    s.position_order
FROM cv_extracted_content c
JOIN cv_sections s ON s.cv_content_id = c.id
WHERE s.section_type IN ('experience', 'projects', 'summary')
ORDER BY c.user_email, c.indexed_at DESC, s.position_order;

-- Grant permissions (adjust as needed for your setup)
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO winningcv;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO winningcv;
-- GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO winningcv;
