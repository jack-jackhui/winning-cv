import os
import sys
import time
import logging

# Make sure we can import from one directory up
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config.settings import Config
from job_sources.linkedin_job_scraper import LinkedInJobScraper
from utils.logger import setup_logger

def test_real_linkedin_scraping():
    """Live test of LinkedIn scraping with real job URLs, respecting MAX_JOBS_TO_SCRAPE."""
    # Call setup_logger with the current module name and set it to DEBUG level
    logger = setup_logger(name=__name__, log_file="logs/job_monitor.log")
    logger.setLevel(logging.DEBUG)

    scraper = None

    try:
        scraper = LinkedInJobScraper()
        test_url = Config.LINKEDIN_JOB_URL  # from your .env
        logger.info(f"Using MAX_JOBS_TO_SCRAPE={Config.MAX_JOBS_TO_SCRAPE}")

        if not scraper.validate_url(test_url):
            logger.error(f"Invalid or missing LinkedIn URL: {test_url}")
            return

        start_time = time.time()
        job_listings = scraper.scrape_job_page(test_url)
        elapsed = time.time() - start_time

        if not job_listings:
            logger.error("Scraping returned no data.")
            return

        for i, job in enumerate(job_listings, start=1):
            logger.info(f"\nJob {i}/{len(job_listings)}:")
            logger.info(f"Title: {job['title']}")
            logger.info(f"Company: {job['company']}")
            logger.info(f"Location: {job['location']}")
            logger.info(f"Posted: {job['posted_date']}")
            logger.info(f"URL: {job['job_url']}")
            # desc_snippet = job['description'][:100]
            logger.debug(f"Job Description:\n {job['description']}...")

        logger.info(f"\nScraping completed in {elapsed:.2f} seconds.")
        logger.info(f"Total job listings extracted: {len(job_listings)}")

    except Exception as e:
        logger.error(f"Scraping test failed: {str(e)}")
        if scraper and scraper.browser:
            logger.info("Capturing screenshot of failure...")
            scraper.browser.latest_tab.screenshot('test_failure.png')
    finally:
        if scraper and scraper.browser:
            logger.info("Closing Drission browser...")
            scraper.browser.quit()
        logger.info("Test completed.")

if __name__ == "__main__":
    test_real_linkedin_scraping()
