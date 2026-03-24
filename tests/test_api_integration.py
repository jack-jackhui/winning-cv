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
