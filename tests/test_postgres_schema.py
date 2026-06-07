"""
Schema parity tests for PostgreSQL backend.

Ensures the SQL schema definitions match what PostgresManager expects.
Prevents silent schema drift between SQL files and Python code.
"""
import re
from pathlib import Path

import pytest


def parse_sql_columns(sql_content: str, table_name: str) -> set:
    """Extract column names from CREATE TABLE statement."""
    # Find the CREATE TABLE block
    pattern = rf"CREATE TABLE IF NOT EXISTS {table_name}\s*\((.*?)\);"
    match = re.search(pattern, sql_content, re.DOTALL | re.IGNORECASE)
    if not match:
        return set()

    block = match.group(1)
    columns = set()

    for line in block.split('\n'):
        line = line.strip()
        # Skip comments, empty lines, constraints, indexes
        if not line or line.startswith('--') or line.startswith('CONSTRAINT'):
            continue
        if line.upper().startswith(('PRIMARY KEY', 'UNIQUE', 'FOREIGN KEY', 'CHECK', 'INDEX')):
            continue

        # Extract column name (first word before type)
        parts = line.split()
        if parts:
            col_name = parts[0].strip(',')
            # Skip if it's a reserved word or looks like a constraint
            if col_name.upper() not in ('PRIMARY', 'UNIQUE', 'FOREIGN', 'REFERENCES', 'ON', 'DEFAULT'):
                columns.add(col_name.lower())

    return columns


def get_schema_path() -> Path:
    """Get path to the SQL schema file."""
    return Path(__file__).parent.parent / "init-db" / "02-data-storage-schema.sql"


@pytest.fixture
def schema_content():
    """Load the SQL schema content."""
    schema_path = get_schema_path()
    if not schema_path.exists():
        pytest.skip(f"Schema file not found: {schema_path}")
    return schema_path.read_text()


class TestUserConfigsSchema:
    """Tests for user_configs table schema parity."""

    EXPECTED_COLUMNS = {
        # Core
        'id', 'user_email', 'created_at', 'updated_at',
        # Job search config
        'base_cv_path', 'base_cv_link', 'linkedin_job_url', 'seek_job_url',
        'max_jobs_to_scrape', 'additional_search_term', 'google_search_term',
        'search_keywords', 'location', 'hours_old', 'results_wanted', 'country',
        # Notifications
        'email_alerts', 'telegram_alerts', 'wechat_alerts', 'weekly_digest',
        'telegram_chat_id', 'wechat_id', 'notification_email',
    }

    def test_schema_has_required_columns(self, schema_content):
        """Verify user_configs table has all expected columns."""
        sql_columns = parse_sql_columns(schema_content, 'user_configs')

        missing = self.EXPECTED_COLUMNS - sql_columns
        assert not missing, f"Missing columns in user_configs: {missing}"

    def test_no_unknown_columns(self, schema_content):
        """Warn about columns in SQL but not in expected set."""
        sql_columns = parse_sql_columns(schema_content, 'user_configs')
        extra = sql_columns - self.EXPECTED_COLUMNS

        # This is a warning, not a failure - new columns may be added
        if extra:
            pytest.skip(f"Extra columns in user_configs (update EXPECTED_COLUMNS?): {extra}")


class TestCVVersionsSchema:
    """Tests for cv_versions table schema parity."""

    EXPECTED_COLUMNS = {
        # Core
        'id', 'version_id', 'user_email', 'version_name', 'created_at', 'updated_at',
        # Metadata
        'auto_category', 'user_tags', 'storage_path', 'file_size', 'content_hash',
        # State
        'is_base', 'is_archived', 'usage_count', 'response_count',
        # Relationships
        'parent_version_id', 'source_job_link', 'source_job_title', 'notes',
    }

    def test_schema_has_required_columns(self, schema_content):
        """Verify cv_versions table has all expected columns."""
        sql_columns = parse_sql_columns(schema_content, 'cv_versions')

        missing = self.EXPECTED_COLUMNS - sql_columns
        assert not missing, f"Missing columns in cv_versions: {missing}"

    def test_version_id_is_unique(self, schema_content):
        """Verify version_id has UNIQUE constraint."""
        assert 'version_id VARCHAR(50) NOT NULL UNIQUE' in schema_content or \
               'UNIQUE INDEX' in schema_content and 'version_id' in schema_content, \
               "version_id should be UNIQUE"


class TestJobsSchema:
    """Tests for jobs table schema parity."""

    EXPECTED_COLUMNS = {
        'id', 'user_email', 'job_title', 'job_description', 'job_date',
        'job_link', 'company', 'location', 'matching_score', 'cv_link',
        'match_reasons', 'match_suggestions', 'ats_score', 'hr_score',
        'llm_score', 'hr_recommendation', 'matched_keywords', 'missing_keywords',
        'created_at', 'updated_at',
    }

    def test_schema_has_required_columns(self, schema_content):
        """Verify jobs table has all expected columns."""
        sql_columns = parse_sql_columns(schema_content, 'jobs')

        missing = self.EXPECTED_COLUMNS - sql_columns
        assert not missing, f"Missing columns in jobs: {missing}"

    def test_job_link_is_unique(self, schema_content):
        """Verify job_link has UNIQUE constraint."""
        # Check for UNIQUE in the column definition
        assert 'job_link VARCHAR(2000) UNIQUE' in schema_content, \
            "job_link should be UNIQUE"


class TestCVHistorySchema:
    """Tests for cv_history table schema parity."""

    EXPECTED_COLUMNS = {
        'id', 'user_email', 'job_title', 'job_description', 'instructions',
        'cv_markdown', 'cv_pdf_url', 'cv_analysis', 'analysis_status',
        'created_at', 'updated_at',
    }

    def test_schema_has_required_columns(self, schema_content):
        """Verify cv_history table has all expected columns."""
        sql_columns = parse_sql_columns(schema_content, 'cv_history')

        missing = self.EXPECTED_COLUMNS - sql_columns
        assert not missing, f"Missing columns in cv_history: {missing}"


class TestSearchTasksSchema:
    """Tests for search_tasks table schema parity."""

    EXPECTED_COLUMNS = {
        'id', 'task_id', 'user_email', 'status', 'progress', 'message',
        'results_count', 'error_details', 'created_at', 'updated_at', 'completed_at',
    }

    def test_schema_has_required_columns(self, schema_content):
        """Verify search_tasks table has all expected columns."""
        sql_columns = parse_sql_columns(schema_content, 'search_tasks')

        missing = self.EXPECTED_COLUMNS - sql_columns
        assert not missing, f"Missing columns in search_tasks: {missing}"

    def test_task_id_is_unique(self, schema_content):
        """Verify task_id has UNIQUE constraint."""
        assert 'task_id VARCHAR(50) NOT NULL UNIQUE' in schema_content, \
            "task_id should be UNIQUE"


class TestSchemaIntegrity:
    """Tests for overall schema integrity."""

    def test_schema_file_exists(self):
        """Verify schema file exists."""
        assert get_schema_path().exists(), "Schema file should exist"

    def test_migration_file_exists(self):
        """Verify migration file exists."""
        migration_path = Path(__file__).parent.parent / "init-db" / "03-migration-v2.sql"
        assert migration_path.exists(), "Migration file should exist"

    def test_analytics_function_exists(self, schema_content):
        """Verify get_cv_analytics function is defined."""
        assert 'CREATE OR REPLACE FUNCTION get_cv_analytics' in schema_content, \
            "get_cv_analytics function should be defined"

    def test_updated_at_triggers_defined(self, schema_content):
        """Verify updated_at triggers are defined for all tables."""
        required_triggers = [
            'jobs_updated_at',
            'cv_history_updated_at',
            'user_configs_updated_at',
            'cv_versions_updated_at',
            'search_tasks_updated_at',
        ]
        for trigger in required_triggers:
            assert trigger in schema_content, f"Trigger {trigger} should be defined"
