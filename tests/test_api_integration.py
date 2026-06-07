"""
Integration tests for API route modules.

These smoke tests verify that route modules can be imported without crashing.
"""
import os
from unittest.mock import patch

import pytest


@pytest.fixture
def mock_config():
    """Fixture providing mock environment variables for Config."""
    env_vars = {
        "AIRTABLE_PAT": "fake_pat_for_testing",
        "AIRTABLE_BASE_ID": "fake_base_id",
        "AIRTABLE_TABLE_ID": "fake_table_id",
        "AIRTABLE_TABLE_ID_HISTORY": "fake_history_table",
        "AIRTABLE_TABLE_ID_USER_CONFIGS": "fake_user_configs",
        "AIRTABLE_TABLE_ID_CV_VERSIONS": "fake_cv_versions",
        "AZURE_AI_ENDPOINT": "https://fake.openai.azure.com",
        "AZURE_AI_API_KEY": "fake_azure_key",
        "AZURE_DEPLOYMENT": "fake_deployment",
        "MINIO_ENDPOINT": "localhost:9000",
        "MINIO_ACCESS_KEY": "fake_access_key",
        "MINIO_SECRET_KEY": "fake_secret_key",
    }
    with patch.dict(os.environ, env_vars):
        yield env_vars


@pytest.fixture
def mock_config_minimal():
    """Fixture providing minimal mock config for basic imports."""
    env_vars = {
        "AIRTABLE_PAT": "fake_for_testing",
        "AIRTABLE_BASE_ID": "fake_base",
        "AIRTABLE_TABLE_ID": "fake_table",
        "AIRTABLE_TABLE_ID_HISTORY": "fake_history",
        "AIRTABLE_TABLE_ID_USER_CONFIGS": "fake_configs",
        "AIRTABLE_TABLE_ID_CV_VERSIONS": "fake_versions",
        "AZURE_AI_ENDPOINT": "https://fake.openai.azure.com",
        "AZURE_AI_API_KEY": "fake_key",
        "AZURE_DEPLOYMENT": "fake_deployment",
    }
    with patch.dict(os.environ, env_vars):
        yield env_vars


class TestRouteModuleImports:
    """Smoke tests to verify route modules can be imported."""

    def test_import_auth_routes(self, mock_config_minimal):
        """Auth routes module should import without errors."""
        from api.routes import auth
        assert hasattr(auth, 'router')

    def test_import_cv_routes(self, mock_config_minimal):
        """CV routes module should import without errors."""
        from api.routes import cv
        assert hasattr(cv, 'router')

    def test_import_cv_versions_routes(self, mock_config_minimal):
        """CV versions routes module should import without errors."""
        from api.routes import cv_versions
        assert hasattr(cv_versions, 'router')

    def test_import_jobs_routes(self, mock_config_minimal):
        """Jobs routes module should import without errors."""
        from api.routes import jobs
        assert hasattr(jobs, 'router')

    def test_import_knowledge_base_routes(self, mock_config_minimal):
        """Knowledge base routes module should import without errors."""
        from api.routes import knowledge_base
        assert hasattr(knowledge_base, 'router')

    def test_import_profile_routes(self, mock_config_minimal):
        """Profile routes module should import without errors."""
        from api.routes import profile
        assert hasattr(profile, 'router')

    def test_import_webhooks_routes(self, mock_config_minimal):
        """Webhooks routes module should import without errors."""
        from api.routes import webhooks
        assert hasattr(webhooks, 'router')


class TestRouteModuleExports:
    """Test that route modules export expected routers."""

    def test_routes_init_exports_all_routers(self, mock_config_minimal):
        """api.routes should export all router instances."""
        from api import routes

        expected_routers = [
            'auth_router',
            'cv_router',
            'cv_versions_router',
            'jobs_router',
            'knowledge_base_router',
            'profile_router',
            'webhooks_router',
        ]

        for router_name in expected_routers:
            assert hasattr(routes, router_name), f"Missing export: {router_name}"


class TestHealthModule:
    """Test health check module."""

    def test_health_module_imports(self, mock_config_minimal):
        """Health module should import without errors."""
        from api import health
        assert hasattr(health, 'get_comprehensive_health')
        assert hasattr(health, 'check_postgres_health')
        assert hasattr(health, 'check_minio_health')

    def test_comprehensive_health_returns_dict(self, mock_config_minimal):
        """get_comprehensive_health should return a valid dict."""
        from api.health import get_comprehensive_health
        result = get_comprehensive_health()

        assert isinstance(result, dict)
        assert 'status' in result
        assert 'components' in result
        assert 'timestamp' in result


class TestCVValidation:
    """Test CV file validation utilities."""

    def test_validate_cv_file_rejects_empty(self, mock_config_minimal):
        """Empty files should be rejected."""
        from api.routes.cv import validate_cv_file
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            validate_cv_file(
                filename="test.pdf",
                content_type="application/pdf",
                content=b""
            )
        assert exc_info.value.status_code == 400
        assert "Empty" in exc_info.value.detail

    def test_validate_cv_file_rejects_large_files(self, mock_config_minimal):
        """Files over size limit should be rejected."""
        from api.routes.cv import validate_cv_file, MAX_CV_FILE_SIZE
        from fastapi import HTTPException

        large_content = b"x" * (MAX_CV_FILE_SIZE + 1)

        with pytest.raises(HTTPException) as exc_info:
            validate_cv_file(
                filename="test.pdf",
                content_type="application/pdf",
                content=large_content
            )
        assert exc_info.value.status_code == 413
        assert "too large" in exc_info.value.detail

    def test_validate_cv_file_rejects_bad_extension(self, mock_config_minimal):
        """Invalid extensions should be rejected."""
        from api.routes.cv import validate_cv_file
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            validate_cv_file(
                filename="malware.exe",
                content_type="application/octet-stream",
                content=b"MZ" + b"\x00" * 100
            )
        assert exc_info.value.status_code == 400
        assert "extension" in exc_info.value.detail.lower()

    def test_validate_cv_file_accepts_valid_pdf(self, mock_config_minimal):
        """Valid PDF files should be accepted."""
        from api.routes.cv import validate_cv_file

        # Minimal valid PDF header
        valid_pdf = b"%PDF-1.4\n" + b"\x00" * 100

        # Should not raise
        validate_cv_file(
            filename="resume.pdf",
            content_type="application/pdf",
            content=valid_pdf
        )


class TestTaskManager:
    """Test task manager functionality."""

    def test_file_based_task_manager_create_get(self, mock_config_minimal):
        """FileBasedTaskManager should create and retrieve tasks."""
        from api.routes.jobs import FileBasedTaskManager

        mgr = FileBasedTaskManager()

        task = mgr.create_task(
            task_id="test-task-123",
            user_email="test@example.com",
            status="pending",
            message="Test task"
        )

        assert task["task_id"] == "test-task-123"
        assert task["status"] == "pending"

        retrieved = mgr.get_task("test-task-123")
        assert retrieved is not None
        assert retrieved["task_id"] == "test-task-123"

    def test_file_based_task_manager_update(self, mock_config_minimal):
        """FileBasedTaskManager should update task fields."""
        from api.routes.jobs import FileBasedTaskManager

        mgr = FileBasedTaskManager()
        mgr.create_task(
            task_id="test-task-456",
            user_email="test@example.com"
        )

        mgr.update_task(
            task_id="test-task-456",
            status="completed",
            progress=100,
            message="Done!"
        )

        task = mgr.get_task("test-task-456")
        assert task["status"] == "completed"
        assert task["progress"] == 100
        assert task["message"] == "Done!"
