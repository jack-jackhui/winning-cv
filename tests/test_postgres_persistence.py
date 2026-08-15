"""Real PostgreSQL persistence tests for user-owned application records."""
import os
import uuid
from datetime import date
from pathlib import Path
from urllib.parse import quote

import psycopg2
import pytest

from data_store.postgres_manager import PostgresManager
from data_store.storage_factory import DualWriteDataManager, ShadowWriteError


@pytest.fixture
def postgres_manager():
    base_dsn = os.getenv("TEST_POSTGRES_DSN")
    if not base_dsn:
        pytest.skip("TEST_POSTGRES_DSN is required for PostgreSQL integration tests")

    schema = f"test_jobs_{uuid.uuid4().hex}"
    admin = psycopg2.connect(base_dsn)
    admin.autocommit = True
    try:
        with admin.cursor() as cursor:
            cursor.execute(f'CREATE SCHEMA "{schema}"')
            cursor.execute(f'''SET search_path TO "{schema}"''')
            cursor.execute("""
                CREATE TABLE jobs (
                    id SERIAL PRIMARY KEY,
                    user_email VARCHAR(255) NOT NULL,
                    job_title VARCHAR(500),
                    job_description TEXT,
                    job_date TIMESTAMP WITH TIME ZONE,
                    job_link VARCHAR(2000),
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
                    application_status VARCHAR(40) DEFAULT 'saved',
                    application_notes TEXT,
                    applied_at TIMESTAMP WITH TIME ZONE,
                    next_action_at DATE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """)
            cursor.execute("CREATE UNIQUE INDEX uq_jobs_user_email_job_link ON jobs(user_email, job_link)")

        separator = "&" if "?" in base_dsn else "?"
        manager_dsn = f"{base_dsn}{separator}options={quote(f'-csearch_path={schema}')}"
        yield PostgresManager(manager_dsn)
    finally:
        with admin.cursor() as cursor:
            cursor.execute(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')
        admin.close()


def _job(url: str) -> dict:
    return {
        "Job Title": "Platform Engineer",
        "Job Description": "Build reliable systems",
        "Job Link": url,
        "Company": "Example Co",
        "Location": "Melbourne",
        "score": 9,
    }


def test_cross_user_persistence_ownership_and_apostrophe_listing(postgres_manager):
    url = "https://jobs.example.com/shared-listing"
    apostrophe_owner = "o'connor@example.com"
    other_owner = "other@example.com"

    first = postgres_manager.create_job_record(_job(url), apostrophe_owner)
    second = postgres_manager.create_job_record(_job(url), other_owner)

    assert first is not None and second is not None
    assert first["id"] != second["id"]
    assert postgres_manager.create_job_record(_job(url), apostrophe_owner) is None

    listed = postgres_manager.get_jobs_by_user(apostrophe_owner)
    assert [record["id"] for record in listed] == [first["id"]]
    assert listed[0]["fields"]["User Email"] == apostrophe_owner

    assert postgres_manager.get_job_result(first["id"], apostrophe_owner)["id"] == first["id"]
    assert postgres_manager.get_job_result(first["id"], other_owner) is None
    assert postgres_manager.update_application_status(first["id"], other_owner, "applied") is None

    cv_update = postgres_manager.update_cv_info(
        url, 8, "https://files.example.com/first.pdf", user_email=apostrophe_owner
    )
    assert cv_update == {"id": first["id"]}
    assert postgres_manager.get_job_result(first["id"], apostrophe_owner)["fields"]["Matching Score"] == 8
    assert postgres_manager.get_job_result(second["id"], other_owner)["fields"]["Matching Score"] == 9

    updated = postgres_manager.update_application_status(
        first["id"],
        apostrophe_owner,
        "interviewing",
        "Phone screen",
        date(2026, 7, 30),
        True,
    )
    assert updated == {"id": first["id"]}
    persisted = postgres_manager.get_job_result(first["id"], apostrophe_owner)
    assert persisted["fields"]["Application Status"] == "interviewing"
    assert persisted["fields"]["Application Notes"] == "Phone screen"
    assert persisted["fields"]["Next Action At"] == date(2026, 7, 30)


def test_dual_write_shadow_miss_is_observable_with_real_postgres(postgres_manager, caplog):
    class AirtablePrimary:
        def update_application_status(
            self,
            job_id,
            user_email,
            status,
            notes,
            next_action_at,
            update_next_action,
        ):
            return {
                "id": job_id,
                "fields": {
                    "User Email": user_email,
                    "Job Link": "https://jobs.example.com/missing-shadow",
                    "Application Status": status,
                    "Application Notes": notes,
                },
            }

    manager = DualWriteDataManager(AirtablePrimary(), postgres_manager)
    with pytest.raises(ShadowWriteError, match="did not persist"):
        manager.update_application_status(
            "airtable-record", "owner@example.com", "applied", "Submitted"
        )

    assert "Postgres shadow write missed" in caplog.text


def test_next_action_migration_is_idempotent_and_replaces_old_index():
    base_dsn = os.getenv("TEST_POSTGRES_DSN")
    if not base_dsn:
        pytest.skip("TEST_POSTGRES_DSN is required for PostgreSQL integration tests")

    schema = f"test_next_action_migration_{uuid.uuid4().hex}"
    migration_sql = (
        Path(__file__).parent.parent / "init-db" / "07-jobs-next-action.sql"
    ).read_text()
    conn = psycopg2.connect(base_dsn)
    conn.autocommit = True
    try:
        with conn.cursor() as cursor:
            cursor.execute(f'CREATE SCHEMA "{schema}"')
            cursor.execute(f'SET search_path TO "{schema}"')
            cursor.execute("""
                CREATE TABLE jobs (
                    id SERIAL PRIMARY KEY,
                    user_email VARCHAR(255) NOT NULL,
                    next_action_at TIMESTAMP WITH TIME ZONE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """)
            cursor.execute(
                "CREATE INDEX idx_jobs_user_next_action "
                "ON jobs(user_email, next_action_at, id)"
            )
            cursor.execute(
                "INSERT INTO jobs (user_email, next_action_at) VALUES (%s, %s)",
                ("owner@example.com", "2026-07-30T23:30:00-05:00"),
            )

            cursor.execute(migration_sql)
            cursor.execute(migration_sql)

            cursor.execute("""
                SELECT data_type
                FROM information_schema.columns
                WHERE table_schema = %s
                  AND table_name = 'jobs'
                  AND column_name = 'next_action_at'
            """, (schema,))
            assert cursor.fetchone()[0] == "date"
            cursor.execute("SELECT next_action_at FROM jobs")
            assert cursor.fetchone()[0] == date(2026, 7, 31)
            cursor.execute("""
                SELECT indexdef
                FROM pg_indexes
                WHERE schemaname = %s
                  AND indexname = 'idx_jobs_user_next_action'
            """, (schema,))
            assert "(user_email, next_action_at, created_at DESC, id)" in cursor.fetchone()[0]
    finally:
        with conn.cursor() as cursor:
            cursor.execute(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')
        conn.close()


def test_user_link_migration_is_idempotent_on_existing_postgres():
    base_dsn = os.getenv("TEST_POSTGRES_DSN")
    if not base_dsn:
        pytest.skip("TEST_POSTGRES_DSN is required for PostgreSQL integration tests")

    schema = f"test_migration_{uuid.uuid4().hex}"
    migration_sql = (
        Path(__file__).parent.parent / "init-db" / "06-jobs-user-link-uniqueness.sql"
    ).read_text()
    conn = psycopg2.connect(base_dsn)
    conn.autocommit = True
    try:
        with conn.cursor() as cursor:
            cursor.execute(f'CREATE SCHEMA "{schema}"')
            cursor.execute(f'SET search_path TO "{schema}"')
            cursor.execute("""
                CREATE TABLE jobs (
                    id SERIAL PRIMARY KEY,
                    user_email VARCHAR(255) NOT NULL,
                    job_link VARCHAR(2000) UNIQUE
                )
            """)
            cursor.execute(
                "INSERT INTO jobs (user_email, job_link) VALUES (%s, %s)",
                ("first@example.com", "https://jobs.example.com/shared"),
            )

            cursor.execute(migration_sql)
            cursor.execute(migration_sql)

            cursor.execute(
                "INSERT INTO jobs (user_email, job_link) VALUES (%s, %s)",
                ("second@example.com", "https://jobs.example.com/shared"),
            )
            cursor.execute(
                "SELECT user_email FROM jobs WHERE job_link = %s ORDER BY user_email",
                ("https://jobs.example.com/shared",),
            )
            assert [row[0] for row in cursor.fetchall()] == [
                "first@example.com",
                "second@example.com",
            ]

            with pytest.raises(psycopg2.errors.UniqueViolation):
                cursor.execute(
                    "INSERT INTO jobs (user_email, job_link) VALUES (%s, %s)",
                    ("first@example.com", "https://jobs.example.com/shared"),
                )
    finally:
        with conn.cursor() as cursor:
            cursor.execute(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')
        conn.close()
