"""
Tests for Pydantic Settings configuration.
"""
import os
from unittest.mock import patch

import pytest


class TestSettingsValidation:
    """Test settings validation logic."""

    def test_settings_import(self):
        """Test that settings can be imported."""
        from config.settings_v2 import Settings
        assert Settings is not None

    def test_default_values(self):
        """Test default values are set correctly."""
        from config.settings_v2 import Settings

        # Create with defaults (no env vars)
        with patch.dict(os.environ, {}, clear=True):
            s = Settings()
            assert s.base_cv_path == "user_cv/default_cv.docx"
            assert s.location == "Melbourne, VIC"
            assert s.country == "Australia"
            assert s.headless is True
            assert s.api_port == 8000

    def test_country_validation_valid(self):
        """Test valid country passes validation."""
        from config.settings_v2 import Settings

        with patch.dict(os.environ, {"COUNTRY": "USA"}, clear=True):
            s = Settings()
            assert s.country == "USA"

    def test_country_validation_invalid(self):
        """Test invalid country raises error."""
        from config.settings_v2 import Settings

        with patch.dict(os.environ, {"COUNTRY": "InvalidCountry"}, clear=True):
            with pytest.raises(ValueError, match="Invalid country"):
                Settings()

    def test_numeric_bounds(self):
        """Test numeric field bounds validation."""
        from config.settings_v2 import Settings

        # hours_old must be <= 720
        with patch.dict(os.environ, {"HOURS_OLD": "1000"}, clear=True):
            with pytest.raises(ValueError):
                Settings()

    def test_airtable_api_key_alias(self):
        """Test airtable_api_key property alias."""
        from config.settings_v2 import Settings

        with patch.dict(os.environ, {"AIRTABLE_PAT": "test_token"}, clear=True):
            s = Settings()
            assert s.airtable_api_key == "test_token"
            assert s.airtable_pat == "test_token"


class TestConfigCompat:
    """Test backward compatibility wrapper."""

    def test_config_compat_uppercase(self):
        """Test Config works with uppercase attribute names."""
        from config.settings_v2 import Config

        # Should work with both cases
        assert Config.base_cv_path is not None or Config.BASE_CV_PATH is not None

    def test_config_compat_lowercase(self):
        """Test Config works with lowercase attribute names."""
        from config.settings_v2 import Config

        assert Config.location is not None
        assert Config.country is not None
