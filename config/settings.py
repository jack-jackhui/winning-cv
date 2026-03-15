# config/settings.py
"""
Configuration module - now powered by Pydantic Settings.

This module maintains backward compatibility with existing code while
using Pydantic for validation under the hood.

Usage (both work):
    from config.settings import Config
    print(Config.AIRTABLE_BASE_ID)

    from config.settings_v2 import settings
    print(settings.airtable_base_id)
"""

import os
import warnings

from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Try to use Pydantic settings, fall back to legacy if import fails
try:
    from config.settings_v2 import SUPPORTED_COUNTRIES, settings

    class Config:
        """Backward-compatible Config class powered by Pydantic Settings."""

        # Core settings
        BASE_CV_PATH = settings.base_cv_path

        # LinkedIn/Job URLs
        RSS_FEED_URL = settings.linkedin_rss_url or "your_default_rss_url"
        LINKEDIN_JOB_URL = settings.linkedin_job_url
        LINKEDIN_API_KEY = getattr(settings, 'linkedin_api_key', '') or ''
        SEEK_JOB_URL = settings.seek_job_url

        # Airtable
        AIRTABLE_API_KEY = settings.airtable_pat
        AIRTABLE_BASE_ID = settings.airtable_base_id
        AIRTABLE_TABLE_ID = settings.airtable_table_id
        AIRTABLE_TABLE_ID_HISTORY = settings.airtable_table_id_history
        AIRTABLE_TABLE_ID_USER_CONFIGS = settings.airtable_table_id_user_configs
        AIRTABLE_TABLE_ID_CV_VERSIONS = settings.airtable_table_id_cv_versions

        # Computed Airtable URLs
        @property
        def AIRTABLE_UI_URL(self):
            return f"https://airtable.com/{settings.airtable_base_id}/{settings.airtable_table_id}"

        @property
        def AIRTABLE_UI_HISTORY_TABLE_URL(self):
            return f"https://airtable.com/{settings.airtable_base_id}/{settings.airtable_table_id_history}"

        # Job search settings
        CHECK_INTERVAL_MIN = settings.check_interval_min
        MAX_DESCRIPTION_LENGTH = settings.max_description_length
        MAX_JOBS_FOR_DESCRIPTION = settings.max_jobs_for_description
        MAX_JOBS_TO_SCRAPE = settings.max_jobs_to_scrape
        JOB_MATCH_THRESHOLD = settings.job_match_threshold

        # Azure AI
        AZURE_AI_ENDPOINT = settings.azure_ai_endpoint
        AZURE_AI_API_KEY = settings.azure_ai_api_key
        AZURE_DEPLOYMENT = settings.azure_deployment

        # Search config
        ADDITIONAL_SEARCH_TERM = 'AI IT (manager OR head OR director) "software engineering" leadership'
        GOOGLE_SEARCH_TERM = 'head of IT or IT manager or software engineering manager or AI jobs near Melbourne, VIC since last week'
        LOCATION = settings.location
        HOURS_OLD = settings.hours_old
        RESULTS_WANTED = settings.results_wanted
        COUNTRY = settings.country

        # Notifications
        TELEGRAM_BOT_TOKEN = settings.telegram_bot_token
        TELEGRAM_CHAT_ID = settings.telegram_chat_id
        WECHAT_API_KEY = getattr(settings, 'wechat_api_key', None)
        WECHAT_BOT_URL = getattr(settings, 'wechat_bot_url', None)
        WECHAT_API_URL = getattr(settings, 'wechat_api_url', None)
        EMAIL_USER = settings.email_user
        EMAIL_PASSWORD = settings.email_password
        SMTP_SERVER = settings.smtp_server
        DEFAULT_FROM_EMAIL = settings.default_from_email
        DEFAULT_TO_EMAIL = settings.default_to_email

        # WordPress
        WORDPRESS_SITE = getattr(settings, 'wordpress_site', None)
        WORDPRESS_USERNAME = getattr(settings, 'wordpress_username', None)
        WORDPRESS_APP_PASSWORD = getattr(settings, 'wordpress_app_password', None)

        # Runtime
        RUNNING_IN_DOCKER = settings.running_in_docker
        CHROMIUM_PATH = settings.chromium_path
        CHROME_PATH = settings.chrome_path
        HEADLESS = settings.headless

        # Countries list
        SUPPORTED_COUNTRIES = SUPPORTED_COUNTRIES

        def __getattr__(self, name):
            """Allow lowercase access for backward compatibility."""
            upper = name.upper()
            if hasattr(type(self), upper):
                val = getattr(type(self), upper)
                if callable(val):
                    return val(self)
                return val
            # Try pydantic settings directly
            lower = name.lower()
            if hasattr(settings, lower):
                return getattr(settings, lower)
            raise AttributeError(f"'Config' object has no attribute '{name}'")

        @classmethod
        def validate_country_and_location(cls):
            """Validation is now handled by Pydantic - this is a no-op for compatibility."""
            pass

    # Create singleton instance
    Config = Config()

except ImportError as e:
    warnings.warn(f"Pydantic settings not available ({e}), using legacy Config")

    # Legacy fallback (original implementation)
    class Config:
        def __getattr__(self, name):
            upper = name.upper()
            if hasattr(type(self), upper):
                return getattr(type(self), upper)
            raise AttributeError(f"'Config' object has no attribute '{name}'")

        BASE_CV_PATH = os.getenv("BASE_CV_PATH", "user_cv/default_cv.docx")
        RSS_FEED_URL = os.getenv("LINKEDIN_RSS_URL", "your_default_rss_url")
        LINKEDIN_JOB_URL = os.getenv("LINKEDIN_JOB_URL", "https://linkedin.com")
        LINKEDIN_API_KEY = os.getenv("LINKEDIN_API_KEY", "")
        SEEK_JOB_URL = os.getenv("SEEK_JOB_URL", "https://seek.com")
        AIRTABLE_API_KEY = os.getenv("AIRTABLE_PAT")
        AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID")
        AIRTABLE_TABLE_ID = os.getenv("AIRTABLE_TABLE_ID")
        AIRTABLE_TABLE_ID_HISTORY = os.getenv("AIRTABLE_TABLE_ID_HISTORY")
        AIRTABLE_TABLE_ID_USER_CONFIGS = os.getenv("AIRTABLE_TABLE_ID_USER_CONFIGS")
        AIRTABLE_TABLE_ID_CV_VERSIONS = os.getenv("AIRTABLE_TABLE_ID_CV_VERSIONS")
        CHECK_INTERVAL_MIN = int(os.getenv("CHECK_INTERVAL_MIN", 60))
        MAX_DESCRIPTION_LENGTH = 15000
        MAX_JOBS_FOR_DESCRIPTION = int(os.getenv("MAX_JOBS_FOR_DESCRIPTION", 10))
        MAX_JOBS_TO_SCRAPE = int(os.getenv("MAX_JOBS_TO_SCRAPE", 50))
        JOB_MATCH_THRESHOLD = int(os.getenv("JOB_MATCH_THRESHOLD", 7))
        AZURE_AI_ENDPOINT = os.getenv("AZURE_AI_ENDPOINT")
        AZURE_AI_API_KEY = os.getenv("AZURE_AI_API_KEY")
        AZURE_DEPLOYMENT = os.getenv("AZURE_DEPLOYMENT")
        ADDITIONAL_SEARCH_TERM = 'AI IT (manager OR head OR director) "software engineering" leadership'
        GOOGLE_SEARCH_TERM = 'head of IT or IT manager or software engineering manager or AI jobs near Melbourne, VIC since last week'
        LOCATION = os.getenv('LOCATION', 'Melbourne, VIC')
        HOURS_OLD = int(os.getenv('HOURS_OLD', 168))
        RESULTS_WANTED = int(os.getenv('RESULTS_WANTED', 10))
        COUNTRY = os.getenv('COUNTRY', 'Australia')
        TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
        TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
        WECHAT_API_KEY = os.getenv("WECHAT_API_KEY")
        WECHAT_BOT_URL = os.getenv("WECHAT_BOT_URL")
        WECHAT_API_URL = os.getenv("WECHAT_API_URL")
        EMAIL_USER = os.getenv("EMAIL_USER")
        EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
        SMTP_SERVER = os.getenv("SMTP_SERVER")
        DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL")
        DEFAULT_TO_EMAIL = os.getenv("DEFAULT_TO_EMAIL")
        WORDPRESS_SITE = os.getenv("WORDPRESS_SITE")
        WORDPRESS_USERNAME = os.getenv("WORDPRESS_USERNAME")
        WORDPRESS_APP_PASSWORD = os.getenv("WORDPRESS_APP_PASSWORD")
        RUNNING_IN_DOCKER = os.getenv('RUNNING_IN_DOCKER', 'false').lower() == 'true'
        CHROMIUM_PATH = os.getenv('CHROMIUM_PATH')
        CHROME_PATH = os.getenv('CHROME_PATH')
        HEADLESS = os.getenv('HEADLESS', 'true').lower() == 'true'

        SUPPORTED_COUNTRIES = [
            "Argentina", "Australia", "Austria", "Bahrain", "Belgium", "Brazil",
            "Canada", "Chile", "China", "Colombia", "Costa Rica", "Czech Republic",
            "Denmark", "Ecuador", "Egypt", "Finland", "France", "Germany", "Greece",
            "Hong Kong", "Hungary", "India", "Indonesia", "Ireland", "Israel", "Italy",
            "Japan", "Kuwait", "Luxembourg", "Malaysia", "Mexico", "Morocco",
            "Netherlands", "New Zealand", "Nigeria", "Norway", "Oman", "Pakistan",
            "Panama", "Peru", "Philippines", "Poland", "Portugal", "Qatar", "Romania",
            "Saudi Arabia", "Singapore", "South Africa", "South Korea", "Spain",
            "Sweden", "Switzerland", "Taiwan", "Thailand", "Turkey", "Ukraine",
            "United Arab Emirates", "UK", "USA", "Uruguay", "Venezuela", "Vietnam"
        ]

        @classmethod
        def validate_country_and_location(cls):
            country = cls.COUNTRY
            location = cls.LOCATION
            # Case-insensitive matching
            country_map = {c.lower(): c for c in cls.SUPPORTED_COUNTRIES}
            if country.lower() not in country_map:
                raise ValueError(f"Invalid country '{country}'")
            if not location or len(location.strip()) < 2:
                raise ValueError("Location is required")

    Config.validate_country_and_location()
