# config/settings.py
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    def __getattr__(self, name):
        # Allow lowercase access
        upper = name.upper()
        if hasattr(type(self), upper):
            return getattr(type(self), upper)
        raise AttributeError(f"'Config' object has no attribute '{name}'")

    BASE_CV_PATH = os.getenv("BASE_CV_PATH", "user_cv/default_cv.docx")
    RSS_FEED_URL = os.getenv("LINKEDIN_RSS_URL", "your_default_rss_url")
    LINKEDIN_JOB_URL=os.getenv("LINKEDIN_JOB_URL", "https://linkedin.com")
    LINKEDIN_API_KEY = os.getenv("LINKEDIN_API_KEY", "")
    SEEK_JOB_URL=os.getenv("SEEK_JOB_URL", "https://seek.com")
    AIRTABLE_API_KEY = os.getenv("AIRTABLE_PAT")
    AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID")
    AIRTABLE_TABLE_ID = os.getenv("AIRTABLE_TABLE_ID")
    AIRTABLE_TABLE_ID_HISTORY = os.getenv("AIRTABLE_TABLE_ID_HISTORY")
    AIRTABLE_UI_URL = f"https://airtable.com/{AIRTABLE_BASE_ID}/{AIRTABLE_TABLE_ID}"
    AIRTABLE_UI_HISTORY_TABLE_URL = (
        f"https://airtable.com/{AIRTABLE_BASE_ID}/{AIRTABLE_TABLE_ID_HISTORY}"
    )
    AIRTABLE_TABLE_ID_USER_CONFIGS = os.getenv("AIRTABLE_TABLE_ID_USER_CONFIGS")
    CHECK_INTERVAL_MIN = int(os.getenv("CHECK_INTERVAL_MIN", 60))
    MAX_DESCRIPTION_LENGTH = 15000
    MAX_JOBS_FOR_DESCRIPTION = int(os.getenv("MAX_JOBS_FOR_DESCRIPTION", 10))
    MAX_JOBS_TO_SCRAPE = int(os.getenv("MAX_JOBS_TO_SCRAPE", 50))
    JOB_MATCH_THRESHOLD = int(os.getenv("JOB_MATCH_THRESHOLD", 7))

    # Azure AI configurations
    AZURE_AI_ENDPOINT = os.getenv("AZURE_AI_ENDPOINT")
    AZURE_AI_API_KEY = os.getenv("AZURE_AI_API_KEY")
    AZURE_DEPLOYMENT = os.getenv("AZURE_DEPLOYMENT")

    # Additional Search Config for Indeed and Glassdoor
    ADDITIONAL_SEARCH_TERM = 'AI IT (manager OR head OR director) "software engineering" leadership'
    GOOGLE_SEARCH_TERM = 'head of IT or IT manager or software engineering manager or AI jobs near Melbourne, VIC since last week'
    LOCATION = os.getenv('LOCATION', 'Melbourne, VIC')
    HOURS_OLD = int(os.getenv('HOURS_OLD', 168))
    RESULTS_WANTED = int(os.getenv('RESULTS_WANTED', 10))
    COUNTRY = os.getenv('COUNTRY', 'Australia')

    #Email and Telegram and Wechat Settings
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
    WECHAT_API_KEY = os.getenv("WECHAT_API_KEY")
    WECHAT_BOT_URL = os.getenv("WECHAT_BOT_URL")
    EMAIL_USER = os.getenv("EMAIL_USER")
    EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
    SMTP_SERVER = os.getenv("SMTP_SERVER")
    DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL")
    DEFAULT_TO_EMAIL = os.getenv("DEFAULT_TO_EMAIL")

    # Wordpress Config for File Upload
    WORDPRESS_SITE = os.getenv("WORDPRESS_SITE")
    WORDPRESS_USERNAME = os.getenv("WORDPRESS_USERNAME")
    WORDPRESS_APP_PASSWORD = os.getenv("WORDPRESS_APP_PASSWORD")

    # New Docker-related settings
    RUNNING_IN_DOCKER = os.getenv('RUNNING_IN_DOCKER', 'false').lower() == 'true'
    CHROMIUM_PATH = os.getenv('CHROMIUM_PATH')
    CHROME_PATH = os.getenv('CHROME_PATH')
    HEADLESS = os.getenv('HEADLESS', 'true').lower() == 'true'

    SUPPORTED_COUNTRIES = [
        "Argentina", "Australia", "Austria", "Bahrain",
        "Belgium", "Brazil", "Canada", "Chile", "China", "Colombia", "Costa Rica", "Czech Republic",
        "Denmark", "Ecuador", "Egypt", "Finland", "France", "Germany", "Greece", "Hong Kong",
        "Hungary", "India", "Indonesia", "Ireland", "Israel", "Italy", "Japan", "Kuwait",
        "Luxembourg", "Malaysia", "Mexico", "Morocco", "Netherlands", "New Zealand", "Nigeria",
        "Norway", "Oman", "Pakistan", "Panama", "Peru", "Philippines", "Poland", "Portugal",
        "Qatar", "Romania", "Saudi Arabia", "Singapore", "South Africa", "South Korea", "Spain",
        "Sweden", "Switzerland", "Taiwan", "Thailand", "Turkey", "Ukraine", "United Arab Emirates",
        "UK", "USA", "Uruguay", "Venezuela", "Vietnam"
    ]

    @classmethod
    def validate_country_and_location(cls):
        country = cls.COUNTRY
        location = cls.LOCATION
        if country not in cls.SUPPORTED_COUNTRIES:
            raise ValueError(
                f"Invalid country_indeed '{country}'. Must be one of: {', '.join(cls.SUPPORTED_COUNTRIES)}"
            )
        if not location or len(location.strip()) < 2:
            raise ValueError("Location is required and must be a non-empty string.")

Config.validate_country_and_location()