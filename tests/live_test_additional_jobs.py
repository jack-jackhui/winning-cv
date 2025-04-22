# tests/live_test_additional_jobs.py
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import logging
from datetime import datetime
from job_sources.additional_job_search import AdditionalJobProcessor
from config.settings import Config
from utils.content_cleaner import ContentCleaner


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler("live_job_test.log"),
            logging.StreamHandler()
        ]
    )


def validate_job(job: dict) -> bool:
    """Validate job structure and content"""
    required_fields = [
        'title', 'link', 'published', 'company',
        'location', 'description'
    ]

    # Check for required fields
    for field in required_fields:
        if field not in job:
            logging.error(f"Missing required field: {field}")
            return False
        if not job[field]:
            logging.warning(f"Empty value for field: {field}")

    # Validate URL format
    if not job['link'].startswith('http'):
        logging.error(f"Invalid job URL: {job['link']}")
        return False

    # Validate date format (assuming ISO format)
    try:
        datetime.fromisoformat(job['published'])
    except (ValueError, TypeError):
        logging.warning(f"Invalid date format: {job['published']}")
        return False

    return True


def main():
    setup_logging()
    logger = logging.getLogger(__name__)

    try:
        # Initialize real components
        config = Config()
        content_cleaner = ContentCleaner(max_length=2000)
        processor = AdditionalJobProcessor(content_cleaner, config)

        logger.info("Starting LIVE job search test...")
        logger.info(f"Search Parameters: {config.ADDITIONAL_SEARCH_TERM}, {config.LOCATION}")

        # Perform actual job search
        start_time = datetime.now()
        jobs = processor.scrape_and_process_jobs()
        duration = datetime.now() - start_time

        logger.info(f"Found {len(jobs)} jobs in {duration.total_seconds():.1f} seconds")

        # Analyze results
        valid_jobs = 0
        invalid_jobs = 0

        for idx, job in enumerate(jobs, 1):
            logger.info(f"\nJob #{idx}:")
            logger.info(f"Title: {job.get('title')}")
            logger.info(f"Company: {job.get('company')}")
            logger.info(f"Location: {job.get('location')}")
            logger.info(f"Date: {job.get('published')}")
            logger.info(f"URL: {job.get('link')}")
            logger.info(f"Type: {job.get('employment_type', 'N/A')}")
            logger.info(f"Salary: {job.get('salary', 'N/A')}")
            logger.info(f"Description Length: {len(job.get('description', ''))} chars")

            if validate_job(job):
                valid_jobs += 1
            else:
                invalid_jobs += 1

        logger.info("\nTest Summary:")
        logger.info(f"Total Jobs Found: {len(jobs)}")
        logger.info(f"Valid Jobs: {valid_jobs}")
        logger.info(f"Invalid Jobs: {invalid_jobs}")
        logger.info(f"Success Rate: {(valid_jobs / len(jobs) * 100 if len(jobs) > 0 else 0):.1f}%")

    except Exception as e:
        logger.error(f"Live test failed: {str(e)}", exc_info=True)


if __name__ == "__main__":
    main()
