# tests/test_linkedin_job_fetching.py
import logging
import os
from unittest import mock

import pytest

from config.settings_v2 import Config
from data_store.airtable_manager import AirtableManager
from utils.content_cleaner import ContentCleaner

# Configure tests logger
logger = logging.getLogger(__name__)


@pytest.fixture
def test_config():
    """Test configuration with mock values"""
    os.environ["AIRTABLE_PAT"] = "test_pat"
    os.environ["AIRTABLE_BASE_ID"] = "test_base"
    return Config


@pytest.fixture
def mock_airtable():
    """Mock Airtable manager with proper table method mocking"""
    with mock.patch("pyairtable.Api") as mock_api:
        mock_table = mock.Mock()
        mock_table.all.return_value = []
        mock_table.create.return_value = {"id": "rec_test"}

        mock_api_instance = mock_api.return_value
        mock_api_instance.table.return_value = mock_table

        manager = AirtableManager("test_key", "test_base", "test_table")
        manager.table = mock_table
        yield manager


def test_job_processing_and_cleaning(test_config, mock_airtable):
    """Test job data preparation, cleaning, and record creation"""
    content_cleaner = ContentCleaner(test_config.MAX_DESCRIPTION_LENGTH)

    raw_job = {
        "title": "Senior Python Developer",
        "description": "<p>Python, Django, REST APIs <script>alert(1)</script></p>",
        "url": "https://example.com/job/123",
        "published": "2024-01-01",
    }

    cleaned_desc = content_cleaner.clean_html(raw_job["description"])
    assert "alert(1)" not in cleaned_desc
    assert "Python, Django, REST APIs" in cleaned_desc

    # Create job record
    assert mock_airtable.create_job_record({**raw_job, "description": cleaned_desc})


def test_content_cleaning():
    """Test HTML cleaning and truncation"""
    cleaner = ContentCleaner(100)
    dirty_html = """
    <html>
        <header>Test</header>
        <body>
            <p>Python developer <a href="#">learn more</a></p>
            <script>alert()</script>
        </body>
    </html>
    """

    cleaned = cleaner.clean_html(dirty_html)
    assert "Python developer" in cleaned
    assert "alert()" not in cleaned
    assert "<a>" not in cleaned
    assert len(cleaned) <= 100


def test_error_handling(test_config, mock_airtable):
    """Test error scenarios"""
    mock_table = mock_airtable.table
    mock_table.create.side_effect = Exception("DB error")
    assert mock_airtable.create_job_record({}) is None
