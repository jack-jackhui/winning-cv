import os
import sys
import time
import logging

# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config.settings import Config
from job_sources.seek_job_scraper import SeekJobScraper
from utils.logger import setup_logger


def test_real_seek_scraping():
    """Live test of Seek.com scraping with real job URLs, respecting config limits."""
    logger = setup_logger(name=__name__, log_file="logs/seek_job_test.log")
    logger.setLevel(logging.DEBUG)

    scraper = None

    try:
        scraper = SeekJobScraper()
        test_url = Config.SEEK_JOB_URL
        logger.info(f"Testing Seek scraper with URL: {test_url}")
        logger.info(
            f"MAX_JOBS_TO_SCRAPE={Config.MAX_JOBS_TO_SCRAPE}, MAX_JOBS_FOR_DESCRIPTION={Config.MAX_JOBS_FOR_DESCRIPTION}")

        if not scraper.validate_url(test_url):
            logger.error(f"Invalid Seek URL: {test_url}")
            return

        start_time = time.time()
        job_listings = scraper.scrape_jobs()
        elapsed = time.time() - start_time

        if not job_listings:
            logger.error("No job listings found")
            return

        for i, job in enumerate(job_listings, start=1):
            logger.info(f"\nJob {i}/{len(job_listings)}:")
            logger.info(f"Title: {job['title']}")
            logger.info(f"Company: {job['company']}")
            logger.info(f"Location: {job['location']}")
            logger.info(f"Posted: {job['posted_date']}")
            logger.info(f"Salary: {job['salary']}")
            logger.info(f"Work Type: {job['work_type']}")
            logger.info(f"URL: {job['job_url']}")

            if job['full_description']:
                desc_snippet = job['full_description'][:150] + "..." if len(job['full_description']) > 150 else job[
                    'full_description']
                logger.debug(f"Full Description:\n{desc_snippet}")
            else:
                logger.debug("No full description available")

        logger.info(f"\nSeek scraping completed in {elapsed:.2f} seconds")
        logger.info(f"Total jobs found: {len(job_listings)}")
        logger.info(f"Jobs with full details: {min(Config.MAX_JOBS_FOR_DESCRIPTION, len(job_listings))}")

    except Exception as e:
        logger.error(f"Seek scraping test failed: {str(e)}")
        if scraper and scraper.browser:
            logger.info("Capturing browser state...")
            try:
                scraper.browser.latest_tab.screenshot('seek_test_failure.png')
                logger.info("Saved screenshot as seek_test_failure.png")
            except Exception as screenshot_error:
                logger.error(f"Failed to capture screenshot: {screenshot_error}")
    finally:
        if scraper and scraper.browser:
            logger.info("Closing browser instance...")
            scraper.browser.quit()
        logger.info("Seek scraping test completed")


if __name__ == "__main__":
    test_real_seek_scraping()
