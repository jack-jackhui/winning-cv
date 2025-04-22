# tests/test_job_processing.py
import pytest
from unittest import mock
from config.settings import Config
from data_store.airtable_manager import AirtableManager
from feed.linkedin_feed import LinkedInFeedProcessor
from utils.content_cleaner import ContentCleaner
import logging
import os

# Configure tests logger
logger = logging.getLogger(__name__)


@pytest.fixture
def test_config():
    """Test configuration with mock values"""
    os.environ["AIRTABLE_PAT"] = "test_pat"
    os.environ["AIRTABLE_BASE_ID"] = "test_base"
    os.environ["LINKEDIN_RSS_URL"] = "https://example.com/test_feed"
    return Config()


@pytest.fixture
def mock_airtable():
    """Mock Airtable manager with proper table method mocking"""
    with mock.patch('pyairtable.Api') as mock_api:
        # Create mock table instance
        mock_table = mock.Mock()
        mock_table.all.return_value = []
        mock_table.create.return_value = {'id': 'rec_test'}

        # Configure API mock
        mock_api_instance = mock_api.return_value
        mock_api_instance.table.return_value = mock_table

        manager = AirtableManager("test_key", "test_base", "test_table")
        manager.table = mock_table  # Directly inject mock table
        yield manager


@pytest.fixture
def sample_job_entry():
    """Sample job entry for testing"""
    return type('Entry', (), {
        'title': "Senior Python Developer",
        'description': "<p>Python, Django, REST APIs</p>",
        'published': "Wed, 01 Jan 2024 00:00:00 GMT",
        'link': "https://example.com/job/123"
    })


def test_full_workflow(test_config, mock_airtable, sample_job_entry):
    """Test complete workflow from feed fetch to score calculation"""
    # Get reference to mock table
    mock_table = mock_airtable.table

    # Mock feedparser response
    with mock.patch('feedparser.parse') as mock_parse:
        mock_parse.return_value.entries = [sample_job_entry]

        # Initialize components
        feed_processor = LinkedInFeedProcessor(test_config.RSS_FEED_URL)
        content_cleaner = ContentCleaner(test_config.MAX_DESCRIPTION_LENGTH)

        # Test job processing
        entries = feed_processor.fetch_jobs()
        assert len(entries) == 1

        # Verify initial state
        assert len(mock_airtable.get_existing_job_links()) == 0

        # Process entry
        job_data = feed_processor.process_entry(entries[0])
        cleaned_desc = content_cleaner.clean_html(job_data['description'])

        # Mock score calculation
        with mock.patch('utils.matcher.JobMatcher.calculate_match_score') as mock_score:
            mock_score.return_value = (8.5, {
                'score': 8.5,
                'reasons': ["Python experience"],
                'suggestions': []
            })

            # Create job record
            assert mock_airtable.create_job_record({
                **job_data,
                'description': cleaned_desc
            })

            # Mock unprocessed jobs response
            mock_table.all.return_value = [{
                'fields': {
                    'Job Description': cleaned_desc,
                    'Job Link': job_data['url']
                }
            }]

            # Test matching process
            test_cv = "Python developer with 5 years experience..."
            score = mock_score(cleaned_desc, test_cv)
            assert score[0] >= 7


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
    # Test feed fetch failure
    with mock.patch('feedparser.parse') as mock_parse:
        mock_parse.side_effect = Exception("Feed error")
        feed_processor = LinkedInFeedProcessor(test_config.RSS_FEED_URL)
        entries = feed_processor.fetch_jobs()
        assert len(entries) == 0
    # Test Airtable create failure
    mock_table.create.side_effect = Exception("DB error")
    assert mock_airtable.create_job_record({}) is False
