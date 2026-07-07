#!/usr/bin/env bash
set -euo pipefail
POSTGRES_CONTAINER="${POSTGRES_CONTAINER:-winning-cv-postgres}"
POSTGRES_USER="${POSTGRES_USER:-winningcv}"
POSTGRES_DB="${POSTGRES_DB:-winningcv}"

docker exec "$POSTGRES_CONTAINER" psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 <<'SQL'
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS application_status VARCHAR(50) DEFAULT 'saved';
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS application_notes TEXT;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS applied_at TIMESTAMP WITH TIME ZONE;
CREATE INDEX IF NOT EXISTS idx_jobs_application_status ON jobs(application_status);

ALTER TABLE cv_history ADD COLUMN IF NOT EXISTS cv_docx_url VARCHAR(2000);

ALTER TABLE cv_versions ADD COLUMN IF NOT EXISTS docx_storage_path VARCHAR(500);
ALTER TABLE cv_versions ADD COLUMN IF NOT EXISTS docx_file_size INTEGER DEFAULT 0;
ALTER TABLE cv_versions ADD COLUMN IF NOT EXISTS docx_content_hash VARCHAR(64);
SQL
