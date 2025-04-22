# tests/test_workflow_steps.py
import os, sys
# Add parent directory to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import logging
from config.settings import Config
from data_store.airtable_manager import AirtableManager
from feed.linkedin_feed import LinkedInFeedProcessor
from job_sources.linkedin_job_scraper import LinkedInJobScraper
from utils.content_cleaner import ContentCleaner
from utils.matcher import JobMatcher
from utils.cv_loader import load_cv_content
from utils.logger import setup_logger


def test_real_workflow_steps_1_to_3():
    """Test actual workflow execution for steps 1-3"""
    # Initialize logging
    setup_logger(log_file="real_run.log")
    logger = logging.getLogger(__name__)

    logger.info("Starting REAL WORKFLOW TEST (Steps 1-3)")

    # Load real configuration
    config = Config()

    # Initialize components with real connections
    matcher = JobMatcher()

    airtable = AirtableManager(
        config.AIRTABLE_API_KEY,
        config.AIRTABLE_BASE_ID,
        config.AIRTABLE_TABLE_ID
    )
    # feed_processor = LinkedInFeedProcessor(config.RSS_FEED_URL)
    content_cleaner = ContentCleaner(config.MAX_DESCRIPTION_LENGTH)

    # Step 1: Fetch jobs
    logger.info("Step 1: Fetching LinkedIn jobs")

    scraper = LinkedInJobScraper()

    # Ensure your .env (or environment) has a valid LINKEDIN_JOB_URL
    # and MAX_JOBS_FOR_DESCRIPTION set if needed
    linkedin_url = config.LINKEDIN_JOB_URL
    # Scrape the LinkedIn job page
    jobs = scraper.scrape_job_page(linkedin_url)
    if not jobs:
        logger.error("No jobs returned by LinkedInJobScraper. Aborting.")
        return

    logger.info(f"Fetched {len(jobs)} jobs")

    # Step 2: Save to Airtable
    logger.info("Step 2: Saving to Airtable")
    existing_links = airtable.get_existing_job_links()
    new_jobs = 0

    for job in jobs:
        try:
            # LinkedInJobScraper returns a dict with these keys:
            #  "title", "company", "location", "posted_date", "job_url", "description"
            job_url = job.get("job_url")
            if not job_url or job_url in existing_links:
                continue  # skip invalid or duplicate entry
            # Convert to the structure needed by your Airtable table
            job_data = {
                "title": job.get("title"),
                "description": content_cleaner.clean_html(job.get("description", "")),
                "published": job.get("posted_date"),  # or map to "Job Date"
                "url": job_url,
                # extra fields if needed, e.g. company or location
            }
            # Basic validation to ensure we have minimal required fields
            if not job_data["title"] or not job_data["url"]:
                logger.warning(f"Skipping invalid LinkedIn job data: {job_data}")
                continue
            # Create record in Airtable
            record = airtable.create_job_record(job_data)
            if record:
                new_jobs += 1
        except Exception as e:
            logger.error(f"Failed to process LinkedIn job: {str(e)}")
            continue

    logger.info(f"Added {new_jobs} new jobs to Airtable")

    # Step 3: Analyze matches
    logger.info("Step 3: Calculating match scores")
    unprocessed_jobs = airtable.get_unprocessed_jobs()
    logger.info(f"Found {len(unprocessed_jobs)} unprocessed jobs")

    # Load actual CV content
    cv_text = load_cv_content("user_cv/CV_Jack_HUI_08042025_EL.docx")

    if not cv_text:
        logger.error("Failed to load CV content")
        return

    for record in unprocessed_jobs:
        job_desc = record['fields']['Job Description']
        job_link = record['fields']['Job Link']

        if not job_desc:
            continue

        # Use hybrid scoring
        score, analysis = matcher.calculate_match_score(job_desc, cv_text)
        logger.info(f"""
                Match analysis for {job_link}:
                - Final Score: {score:.2f}/10
                - Key Reasons: {analysis.get('reasons', [])[:3]}
                - Suggestions: {analysis.get('suggestions', [])[:3]}
                """)

        # Explicitly prevent CV generation
        if score >= 7:
            logger.warning(f"Score threshold met ({score}), but CV generation skipped per test config")

    logger.info("Real workflow test completed (Steps 1-3)")

if __name__ == "__main__":
    test_real_workflow_steps_1_to_3()
