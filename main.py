import logging
import os
from datetime import datetime
import uuid
from typing import List, Dict

from config.settings import Config
from job_processing.core import JobProcessor
from utils.logger import setup_logger
from utils.notifications import notify_all
"""
from data_store.airtable_manager import AirtableManager
from job_sources.linkedin_job_scraper import LinkedInJobScraper
from job_sources.additional_job_search import AdditionalJobProcessor
from job_sources.seek_job_scraper import SeekJobScraper
from utils.content_cleaner import ContentCleaner
from utils.cv_loader import load_cv_content
from utils.utils import create_pdf
from utils.matcher import JobMatcher
from cv.cv_generator import CVGenerator
"""

def main(config_data: dict = None):
    # ----------------------------------------------------------------------
    # Set up Logging in a "logs" folder
    # ----------------------------------------------------------------------
    os.makedirs("logs", exist_ok=True)
    log_path = os.path.join("logs", "job_monitor.log")
    setup_logger(log_file=log_path, level=logging.DEBUG)
    logger = logging.getLogger(__name__)
    logging.info("Initializing SINGLE-RUN Job Monitor Application")

    # ----------------------------------------------------------------------
    # Initialize Application Components
    # ----------------------------------------------------------------------
    # Use passed config or load default
    config = Config() if config_data is None else Struct(**config_data)

    # ----------------------------------------------------------------------
    # Main Execution (Single Run, No Scheduler)
    # ----------------------------------------------------------------------
    try:
        processor = JobProcessor(config)
        results = processor.process_jobs()

        # CLI notifications
        if config_data is None:
            notify_all(len(results), results, config.AIRTABLE_UI_URL)

        return results
    except Exception as e:
        logger.error(f"Main execution failed: {str(e)}")
        return []

class Struct:
    """Convert dict to object for config"""
    def __init__(self, **entries):
        self.__dict__.update(entries)

if __name__ == "__main__":
    # CLI mode with default config
    main()
