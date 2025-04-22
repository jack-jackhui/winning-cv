import feedparser
import hashlib
from utils.logger import setup_logger
from datetime import datetime

class LinkedInFeedProcessor:
    def __init__(self, feed_url):
        self.feed_url = feed_url
        self.logger = setup_logger(__name__)

    def fetch_jobs(self):
        try:
            feed = feedparser.parse(self.feed_url)
            self.logger.info(f"Fetched {len(feed.entries)} jobs from RSS feed")
            return feed.entries
        except Exception as e:
            self.logger.error(f"Failed to fetch feed: {str(e)}")
            return []

    @staticmethod
    def hash_job_id(url):
        return hashlib.md5(url.encode()).hexdigest()

    def process_entry(self, entry):
        """Map RSS entry to Airtable columns"""
        try:
            published = entry.get('published', entry.get('updated', ''))
            if published:
                published = self._format_date(published)
            else:
                published = datetime.now().strftime('%Y-%m-%d')  # Fallback to current date
            return {
                'title': entry.get('title', 'No Title'),
                'description': entry.get('description', ''),
                'url': entry.get('link', ''),
                'published': published
            }
        except Exception as e:
            self.logger.error(f"Failed to process entry: {str(e)}")
            return {}

    def _format_date(self, date_str):
        """Ensure Airtable-compatible ISO format without microseconds"""
        formats = [
            '%a, %d %b %Y %H:%M:%S %Z',
            '%Y-%m-%dT%H:%M:%S.%fZ',
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d'
        ]
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime('%Y-%m-%d')  # Ensure ISO format
            except (ValueError, TypeError):
                continue
        return datetime.now().strftime('%Y-%m-%d')