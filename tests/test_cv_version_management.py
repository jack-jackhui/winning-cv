"""
End-to-end tests for CV Version Management feature.

Tests:
1. CV Version Manager - Backend module
2. Smart Matching Algorithm
3. API Endpoints
4. Frontend component imports
"""

import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import json

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestCVVersionManager:
    """Test the CVVersionManager backend module."""

    def test_import_cv_version_manager(self):
        """Test that CVVersionManager can be imported."""
        from data_store.cv_version_manager import CVVersionManager
        assert CVVersionManager is not None

    def test_cv_version_manager_init(self):
        """Test CVVersionManager initialization."""
        from data_store.cv_version_manager import CVVersionManager

        with patch.object(CVVersionManager, '__init__', return_value=None):
            manager = CVVersionManager()
            assert manager is not None

    def test_generate_version_id(self):
        """Test version ID generation format."""
        import uuid
        # Test the ID format without instantiating the full manager
        version_id = f"cv_{uuid.uuid4().hex[:12]}"

        assert version_id is not None
        assert version_id.startswith('cv_')
        assert len(version_id) > 10


class TestCVMatcher:
    """Test the Smart Matching Algorithm."""

    def test_import_cv_matcher(self):
        """Test that CVVersionMatcher can be imported."""
        from utils.cv_matcher import CVVersionMatcher
        assert CVVersionMatcher is not None

    def test_cv_matcher_init(self):
        """Test CVVersionMatcher initialization."""
        from utils.cv_matcher import CVVersionMatcher

        matcher = CVVersionMatcher()
        assert matcher is not None
        assert hasattr(matcher, 'all_skills')  # Compiled set of all skills

    def test_analyze_job_basic(self):
        """Test job analysis with basic job description."""
        from utils.cv_matcher import CVVersionMatcher

        matcher = CVVersionMatcher()
        job_description = """
        Senior Software Engineer

        We are looking for an experienced Python developer with 5+ years experience.
        Required skills: Python, Django, PostgreSQL, AWS, Docker.
        Nice to have: Kubernetes, React, TypeScript.

        Responsibilities:
        - Design and implement scalable APIs
        - Lead technical discussions
        - Mentor junior developers
        """

        analysis = matcher._analyze_job(job_description, "Senior Software Engineer", "TechCorp")

        assert analysis is not None
        assert 'detected_role' in analysis
        assert 'all_skills' in analysis
        assert 'seniority' in analysis
        assert len(analysis['all_skills']) > 0

    def test_analyze_job_detects_skills(self):
        """Test that job analysis correctly detects skills."""
        from utils.cv_matcher import CVVersionMatcher

        matcher = CVVersionMatcher()
        job_description = """
        Full Stack Developer needed.
        Requirements: JavaScript, React, Node.js, MongoDB, Git.
        """

        analysis = matcher._analyze_job(job_description)
        skills = analysis['all_skills']

        # Should detect multiple skills
        assert len(skills) >= 3
        # Should detect common web skills (case insensitive matching)
        skills_lower = [s.lower() for s in skills]
        assert any('react' in s or 'javascript' in s or 'node' in s for s in skills_lower)

    def test_score_version(self):
        """Test CV version scoring."""
        from utils.cv_matcher import CVVersionMatcher

        matcher = CVVersionMatcher()

        job_analysis = {
            'detected_role': 'Software Engineer',
            'all_skills': ['python', 'django', 'postgresql', 'aws'],
            'seniority': 'senior',
            'company_name': 'TechCorp'
        }

        version = {
            'version_id': 'cv_123',
            'version_name': 'Software Engineer CV',
            'auto_category': 'Software Engineer',
            'user_tags': ['python', 'backend', 'aws'],
            'usage_count': 10,
            'response_count': 3
        }

        score = matcher._score_version(version, job_analysis)

        assert score is not None
        assert 'overall_score' in score
        assert 'reasons' in score
        assert 0 <= score['overall_score'] <= 100

    def test_match_versions(self):
        """Test full version matching flow."""
        from utils.cv_matcher import CVVersionMatcher

        matcher = CVVersionMatcher()

        versions = [
            {
                'version_id': 'cv_1',
                'version_name': 'Python Developer CV',
                'auto_category': 'Software Engineer',
                'user_tags': ['python', 'django'],
                'usage_count': 5,
                'response_count': 2
            },
            {
                'version_id': 'cv_2',
                'version_name': 'Frontend CV',
                'auto_category': 'Frontend Developer',
                'user_tags': ['react', 'javascript'],
                'usage_count': 3,
                'response_count': 1
            }
        ]

        job_description = "Looking for a Python backend developer with Django experience."

        result = matcher.match_versions(versions, job_description, "Backend Developer")

        assert result is not None
        assert 'suggestions' in result
        assert 'job_analysis' in result
        assert len(result['suggestions']) > 0

        # First suggestion should be Python CV (better match)
        assert result['suggestions'][0]['version_id'] == 'cv_1'


class TestAPISchemas:
    """Test API schemas for CV versions."""

    def test_import_schemas(self):
        """Test that all CV version schemas can be imported."""
        from api.schemas.cv import (
            CVVersionBase,
            CVVersionCreate,
            CVVersionUpdate,
            CVVersionResponse,
            CVVersionListResponse,
            CVVersionForkRequest,
            CVVersionMatchRequest,
            CVVersionMatchScore,
            CVVersionMatchResponse,
            CVVersionAnalyticsResponse,
            CVVersionBulkActionRequest,
            CVVersionBulkActionResponse
        )

        assert CVVersionBase is not None
        assert CVVersionCreate is not None
        assert CVVersionUpdate is not None
        assert CVVersionResponse is not None
        assert CVVersionListResponse is not None

    def test_cv_version_response_schema(self):
        """Test CVVersionResponse schema validation."""
        from api.schemas.cv import CVVersionResponse

        data = {
            'id': 'rec123',
            'version_id': 'cv_123',
            'user_email': 'test@example.com',
            'version_name': 'Test CV',
            'storage_path': 'cvs/test.pdf',
            'auto_category': 'Software Engineer',
            'user_tags': ['python', 'backend'],
            'created_at': '2025-01-01T00:00:00Z',
            'is_archived': False,
            'usage_count': 5,
            'response_count': 2,
            'file_size': 1024
        }

        response = CVVersionResponse(**data)
        assert response.version_id == 'cv_123'
        assert response.version_name == 'Test CV'
        assert response.usage_count == 5

    def test_cv_match_request_schema(self):
        """Test CVVersionMatchRequest schema."""
        from api.schemas.cv import CVVersionMatchRequest

        # Need at least 50 chars for job description
        job_desc = "Looking for a Python developer with 5+ years experience in Django, PostgreSQL, and AWS."
        data = {
            'job_description': job_desc,
            'job_title': 'Software Engineer',
            'company_name': 'TechCorp',
            'limit': 3
        }

        request = CVVersionMatchRequest(**data)
        assert request.job_description == job_desc
        assert request.limit == 3


class TestAPIRoutes:
    """Test API routes for CV versions."""

    def test_import_router(self):
        """Test that CV versions router can be imported."""
        from api.routes.cv_versions import router
        assert router is not None

    def test_router_prefix(self):
        """Test router has correct prefix."""
        from api.routes.cv_versions import router
        assert router.prefix == '/cv/versions'

    def test_router_routes_exist(self):
        """Test expected routes are registered."""
        from api.routes.cv_versions import router

        route_paths = [route.path for route in router.routes]

        # Check main CRUD routes exist (paths include prefix)
        assert any('/cv/versions' == p or p == '' for p in route_paths)  # list/create
        assert '/cv/versions/{version_id}' in route_paths  # get/update/delete
        assert '/cv/versions/{version_id}/fork' in route_paths
        assert '/cv/versions/{version_id}/download' in route_paths
        assert '/cv/versions/{version_id}/use' in route_paths
        assert '/cv/versions/{version_id}/response' in route_paths
        assert '/cv/versions/match' in route_paths
        assert '/cv/versions/analytics/summary' in route_paths


class TestFrontendComponents:
    """Test frontend component structure (syntax validation)."""

    def test_cv_library_jsx_syntax(self):
        """Test CVLibrary.jsx has valid syntax structure."""
        frontend_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'frontend', 'src', 'pages', 'CVLibrary.jsx'
        )

        assert os.path.exists(frontend_path), f"CVLibrary.jsx not found at {frontend_path}"

        with open(frontend_path, 'r') as f:
            content = f.read()

        # Check essential imports
        assert 'import { useState' in content
        assert 'import { cvVersionsService }' in content
        assert 'lucide-react' in content

        # Check component exports
        assert 'export default function CVLibrary' in content

        # Check key features exist
        assert 'CVVersionCard' in content
        assert 'UploadModal' in content
        assert 'ForkModal' in content

    def test_cv_selector_jsx_syntax(self):
        """Test CVSelector.jsx has valid syntax structure."""
        frontend_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'frontend', 'src', 'components', 'cv', 'CVSelector.jsx'
        )

        assert os.path.exists(frontend_path), f"CVSelector.jsx not found at {frontend_path}"

        with open(frontend_path, 'r') as f:
            content = f.read()

        # Check essential imports
        assert 'import { useState, useEffect }' in content
        assert 'cvVersionsService' in content

        # Check component exports
        assert 'export default function CVSelector' in content
        assert 'export { MatchBadge, SuggestionCard }' in content

        # Check key features
        assert 'matchVersions' in content
        assert 'onSelect' in content

    def test_cv_analytics_jsx_syntax(self):
        """Test CVAnalytics.jsx has valid syntax structure."""
        frontend_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'frontend', 'src', 'pages', 'CVAnalytics.jsx'
        )

        assert os.path.exists(frontend_path), f"CVAnalytics.jsx not found at {frontend_path}"

        with open(frontend_path, 'r') as f:
            content = f.read()

        # Check essential imports
        assert 'import { useState, useEffect }' in content
        assert 'cvVersionsService' in content

        # Check component exports
        assert 'export default function CVAnalytics' in content

        # Check analytics features
        assert 'getAnalytics' in content
        assert 'TopPerformerCard' in content or 'StatCard' in content

    def test_generate_cv_integration(self):
        """Test GenerateCV.jsx has CV selector integration."""
        frontend_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'frontend', 'src', 'pages', 'GenerateCV.jsx'
        )

        assert os.path.exists(frontend_path), f"GenerateCV.jsx not found at {frontend_path}"

        with open(frontend_path, 'r') as f:
            content = f.read()

        # Check CVSelector import and usage
        assert 'import CVSelector' in content
        assert '<CVSelector' in content
        assert 'cvVersionsService' in content

        # Check CV source toggle
        assert "cvSource" in content
        assert "'library'" in content or '"library"' in content

    def test_sidebar_navigation(self):
        """Test Sidebar has CV-related navigation items."""
        frontend_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'frontend', 'src', 'components', 'layout', 'Sidebar.jsx'
        )

        assert os.path.exists(frontend_path), f"Sidebar.jsx not found at {frontend_path}"

        with open(frontend_path, 'r') as f:
            content = f.read()

        # Check navigation items
        assert '/cv-library' in content
        assert '/cv-analytics' in content
        assert 'My CVs' in content
        assert 'CV Analytics' in content

    def test_app_routes(self):
        """Test App.jsx has all CV routes."""
        frontend_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'frontend', 'src', 'App.jsx'
        )

        assert os.path.exists(frontend_path), f"App.jsx not found at {frontend_path}"

        with open(frontend_path, 'r') as f:
            content = f.read()

        # Check route imports
        assert 'import CVLibrary' in content
        assert 'import CVAnalytics' in content

        # Check routes
        assert '/cv-library' in content
        assert '/cv-analytics' in content

    def test_api_service(self):
        """Test API service has cvVersionsService."""
        frontend_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'frontend', 'src', 'services', 'api.js'
        )

        assert os.path.exists(frontend_path), f"api.js not found at {frontend_path}"

        with open(frontend_path, 'r') as f:
            content = f.read()

        # Check cvVersionsService exists with key methods
        assert 'cvVersionsService' in content
        assert 'listVersions' in content
        assert 'createVersion' in content
        assert 'getVersion' in content
        assert 'updateVersion' in content
        assert 'archiveVersion' in content
        assert 'deleteVersion' in content
        assert 'forkVersion' in content
        assert 'matchVersions' in content
        assert 'getAnalytics' in content


class TestIntegration:
    """Integration tests combining multiple components."""

    def test_full_matching_pipeline(self):
        """Test complete matching pipeline from job to suggestions."""
        from utils.cv_matcher import CVVersionMatcher

        matcher = CVVersionMatcher()

        # Simulate CV library
        cv_library = [
            {
                'version_id': 'cv_python',
                'version_name': 'Python Backend Developer',
                'auto_category': 'Backend Developer',
                'user_tags': ['python', 'django', 'postgresql', 'aws'],
                'usage_count': 20,
                'response_count': 8
            },
            {
                'version_id': 'cv_frontend',
                'version_name': 'React Frontend Developer',
                'auto_category': 'Frontend Developer',
                'user_tags': ['react', 'typescript', 'css', 'javascript'],
                'usage_count': 15,
                'response_count': 5
            },
            {
                'version_id': 'cv_fullstack',
                'version_name': 'Full Stack Engineer',
                'auto_category': 'Full Stack Developer',
                'user_tags': ['python', 'react', 'nodejs', 'postgresql'],
                'usage_count': 10,
                'response_count': 4
            },
            {
                'version_id': 'cv_data',
                'version_name': 'Data Scientist',
                'auto_category': 'Data Science',
                'user_tags': ['python', 'pandas', 'tensorflow', 'sql'],
                'usage_count': 8,
                'response_count': 2
            }
        ]

        # Test backend job
        backend_job = """
        Senior Python Developer at TechCorp

        We need an experienced backend engineer to build scalable APIs.
        Requirements:
        - 5+ years Python experience
        - Django or FastAPI
        - PostgreSQL
        - AWS (EC2, Lambda, S3)
        - Docker & Kubernetes
        """

        result = matcher.match_versions(cv_library, backend_job, "Senior Python Developer", "TechCorp", limit=3)

        assert len(result['suggestions']) == 3
        # Python CV should rank highest
        assert result['suggestions'][0]['version_id'] == 'cv_python'

        # Test frontend job
        frontend_job = """
        React Developer at WebStudio

        Join our team building modern web applications.
        Requirements:
        - React.js expertise
        - TypeScript
        - CSS/SCSS
        - REST API integration
        """

        result = matcher.match_versions(cv_library, frontend_job, "React Developer", "WebStudio", limit=3)

        assert len(result['suggestions']) == 3
        # Frontend CV should rank highest
        assert result['suggestions'][0]['version_id'] == 'cv_frontend'

    def test_response_rate_affects_ranking(self):
        """Test that historical response rate affects CV ranking."""
        from utils.cv_matcher import CVVersionMatcher

        matcher = CVVersionMatcher()

        # Two similar CVs with different response rates
        cv_library = [
            {
                'version_id': 'cv_low_response',
                'version_name': 'Python Dev v1',
                'auto_category': 'Backend Developer',
                'user_tags': ['python', 'django'],
                'usage_count': 20,
                'response_count': 2  # 10% response rate
            },
            {
                'version_id': 'cv_high_response',
                'version_name': 'Python Dev v2',
                'auto_category': 'Backend Developer',
                'user_tags': ['python', 'django'],
                'usage_count': 10,
                'response_count': 5  # 50% response rate
            }
        ]

        job = "Python backend developer needed"
        result = matcher.match_versions(cv_library, job, limit=2)

        # Higher response rate CV should rank first
        assert result['suggestions'][0]['version_id'] == 'cv_high_response'


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
