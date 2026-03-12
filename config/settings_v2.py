"""
Pydantic Settings v2 - Type-safe configuration with validation.
"""
from typing import Literal, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

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

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Core
    base_cv_path: str = Field(default="user_cv/default_cv.docx")

    # Azure AI
    azure_ai_endpoint: Optional[str] = None
    azure_ai_api_key: Optional[str] = None
    azure_deployment: Optional[str] = None

    # Airtable
    airtable_pat: Optional[str] = None
    airtable_base_id: Optional[str] = None
    airtable_table_id: Optional[str] = None
    airtable_table_id_history: Optional[str] = None
    airtable_table_id_user_configs: Optional[str] = None
    airtable_table_id_cv_versions: Optional[str] = None

    # Job Search
    linkedin_job_url: str = "https://linkedin.com"
    linkedin_rss_url: Optional[str] = None
    seek_job_url: str = "https://seek.com"
    location: str = Field(default="Melbourne, VIC", min_length=2)
    country: str = "Australia"
    hours_old: int = Field(default=168, ge=1, le=720)
    results_wanted: int = Field(default=10, ge=1, le=100)
    max_jobs_to_scrape: int = Field(default=50, ge=1, le=200)
    max_jobs_for_description: int = Field(default=10, ge=1, le=50)
    job_match_threshold: int = Field(default=7, ge=1, le=10)
    check_interval_min: int = Field(default=60, ge=5)
    max_description_length: int = 15000

    # Notifications
    telegram_bot_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    email_user: Optional[str] = None
    email_password: Optional[str] = None
    smtp_server: Optional[str] = None
    default_from_email: Optional[str] = None
    default_to_email: Optional[str] = None

    # PostgreSQL (CV Knowledge Base)
    postgres_host: str = "postgres"
    postgres_port: int = 5432
    postgres_user: str = "winningcv"
    postgres_password: str = "winningcv_secret"
    postgres_db: str = "winningcv"
    postgres_pool_min: int = 2
    postgres_pool_max: int = 10

    @property
    def postgres_dsn(self) -> str:
        """Get PostgreSQL connection DSN."""
        return f"postgresql://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    # MinIO
    minio_endpoint: str = "minio:9000"
    minio_external_endpoint: Optional[str] = None
    minio_root_user: str = "minioadmin"
    minio_root_password: str = "minioadmin123"
    minio_bucket: str = "winningcv-cvs"
    minio_secure: bool = False
    cv_storage_backend: Literal["minio", "wordpress"] = "minio"

    # Runtime
    running_in_docker: bool = False
    chromium_path: Optional[str] = None
    chrome_path: Optional[str] = None
    headless: bool = True
    api_port: int = Field(default=8000, ge=1, le=65535)
    api_host: str = "0.0.0.0"

    @property
    def airtable_api_key(self) -> Optional[str]:
        return self.airtable_pat

    @property
    def airtable_ui_url(self) -> str:
        return f"https://airtable.com/{self.airtable_base_id}/{self.airtable_table_id}"

    @field_validator("country")
    @classmethod
    def validate_country(cls, v: str) -> str:
        if v not in SUPPORTED_COUNTRIES:
            raise ValueError(f"Invalid country: {v}")
        return v

try:
    settings = Settings()
except Exception as e:
    import sys
    print(f"Config error: {e}", file=sys.stderr)
    raise

class ConfigCompat:
    """Backward-compatible wrapper for legacy Config usage."""
    def __getattr__(self, name: str):
        lower = name.lower()
        if hasattr(settings, lower):
            return getattr(settings, lower)
        if hasattr(settings, name):
            return getattr(settings, name)
        raise AttributeError(f"Config has no attribute '{name}'")

Config = ConfigCompat()
