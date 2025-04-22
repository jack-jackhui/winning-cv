import logging
import os
from datetime import datetime
import uuid
from typing import List, Dict

from config.settings import Config
from data_store.airtable_manager import AirtableManager
from job_sources.linkedin_job_scraper import LinkedInJobScraper
from job_sources.additional_job_search import AdditionalJobProcessor
from job_sources.seek_job_scraper import SeekJobScraper
from utils.content_cleaner import ContentCleaner
from utils.cv_loader import load_cv_content
from utils.utils import create_pdf
from utils.matcher import JobMatcher
from utils.logger import setup_logger
from utils.notifications import notify_all
from cv.cv_generator import CVGenerator

def main():
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
    config = Config()

    # Airtable manager for storing job data
    airtable = AirtableManager(
        config.AIRTABLE_API_KEY,
        config.AIRTABLE_BASE_ID,
        config.AIRTABLE_TABLE_ID
    )

    # LinkedIn scraper for job postings
    scraper = LinkedInJobScraper()

    # Seek scraper for job postings
    seek_scraper = SeekJobScraper()

    # Clean HTML in job descriptions
    content_cleaner = ContentCleaner(config.MAX_DESCRIPTION_LENGTH)

    # Matcher for calculating job fit scores
    matcher = JobMatcher()

    # Initialize additional job processor
    additional_processor = AdditionalJobProcessor(
        content_cleaner=content_cleaner,
        config=config
    )

    def process_additional_sources() -> int:
        """Handle other job sources (Indeed, Glassdoor, Google)"""
        logger.info("Processing additional job sources...")
        try:
            processed_jobs = additional_processor.scrape_and_process_jobs()
            if not processed_jobs:
                return 0
            existing_links = airtable.get_existing_job_links()
            new_jobs_added = 0
            for job in processed_jobs:
                if job['link'] in existing_links:
                    continue
                if airtable.create_job_record(job):
                    new_jobs_added += 1
                    logger.info(f"Added job from additional source: {job['title']}")
            logger.info(f"Added {new_jobs_added} jobs from additional sources")
            return new_jobs_added
        except Exception as e:
            logger.error(f"Additional job processing failed: {str(e)}")
            return 0

    # ----------------------------------------------------------------------
    # Helper Functions
    # ----------------------------------------------------------------------
    def get_target_urls() -> List[str]:
        """
        Return URLs to scrape from config or from a database.
        Adjust or extend this logic as needed.
        """
        return [
            config.LINKEDIN_JOB_URL  # e.g. "https://www.linkedin.com/jobs/search?..."
        ]

    def generate_targeted_cv(cv_text: str, job_data: Dict, analysis: Dict) -> str:
        """
        Generate a custom CV using GPT-based approach in CVGenerator.
        Returns a local or remote link to the new CV.
        """
        generator = CVGenerator()

        instructions = (
            "Focus on highlighting the strengths relevant to this job. "
            "Incorporate industry keywords identified in the analysis."
        )

        job_desc = job_data.get("Job Description", "")
        new_cv_markdown = generator.generate_cv(
            cv_content=cv_text,
            job_desc=job_desc,
            instructions=instructions
        )

        today = datetime.today().strftime("%Y%m%d")
        unique_id = uuid.uuid4().hex
        raw_title = job_data.get("Job Title", "untitled")
        clean_title = "".join(
            c if c.isalnum() or c in ('_', '-', '.') else '_'
            for c in raw_title
        ).replace(" ", "_")[:50]
        output_dir = "customised_cv"
        os.makedirs(output_dir, exist_ok=True)

        # Generate PDF version
        pdf_filename = f"{output_dir}/{today}_{clean_title}_{unique_id}_cv.pdf"
        pdf_path = create_pdf(new_cv_markdown, pdf_filename)

        if not pdf_path:
            logger.error("PDF creation failed, falling back to Markdown")
            # Fallback to Markdown version
            md_filename = f"{output_dir}/{today}_{clean_title}_{unique_id}_cv.md"
            with open(md_filename, "w", encoding="utf-8") as f:
                f.write(new_cv_markdown)
            return f"file://{os.path.abspath(md_filename)}"
        logger.info(f"Generated PDF CV: {pdf_path}")
        return f"file://{os.path.abspath(pdf_path)}"

    def normalize_job_data(scraped_data: Dict) -> Dict:
        """
        Map scraped data from LinkedInJobScraper to Airtable schema.
        """
        return {
            "Job Title": scraped_data.get("title", "No Title"),
            "Job Link": scraped_data.get("job_url", ""),
            "Job Date": scraped_data.get("posted_date", ""),
            "Company": scraped_data.get("company", "Unknown Company"),
            "Location": scraped_data.get("location", "Remote"),
            "Job Description": scraped_data.get("description", ""),
        }

    def normalize_seek_job_data(scraped_data: Dict) -> Dict:
        """
        Map scraped data from SeekJobScraper to Airtable schema.
        """
        return {
            "Job Title": scraped_data.get("title", "No Title"),
            "Job Link": scraped_data.get("job_url", ""),
            "Job Date": scraped_data.get("posted_date", ""),
            "Company": scraped_data.get("company", "Unknown Company"),
            "Location": scraped_data.get("location", "Remote"),
            "Job Description": scraped_data.get("full_description") or scraped_data.get("description", ""),
        }

    def process_seek_jobs() -> int:
        """Handle Seek.com.au-specific scraping"""
        logger.info("Processing Seek jobs...")
        try:
            # Scrape jobs from Seek
            job_list = seek_scraper.scrape_jobs()
            if not job_list:
                logger.warning("No jobs returned from Seek scraper.")
                return 0
            existing_links = airtable.get_existing_job_links()
            new_jobs = 0
            for job_data in job_list:
                job_url = job_data.get("job_url")
                if not job_url or job_url in existing_links:
                    continue
                normalized = normalize_seek_job_data(job_data)
                cleaned_desc = content_cleaner.clean_html(normalized["Job Description"])
                normalized["Job Description"] = cleaned_desc
                if airtable.create_job_record(normalized):
                    new_jobs += 1
                    logger.info(f"Added Seek job: {normalized['Job Title']} [{job_url}]")
            logger.info(f"Added {new_jobs} new Seek jobs")
            return new_jobs
        except Exception as e:
            logger.error(f"Seek job processing failed: {str(e)}")
            return 0

    def process_jobs() -> List[dict]:
        """
        1) Scrape job listings from LinkedIn and additional sources
        2) Save new job info to Airtable
        """
        logger.info("Starting job scraping cycle...")
        try:
            total_new_jobs = 0

            # Process LinkedIn jobs first
            linkedin_jobs = process_linkedin_jobs()
            total_new_jobs += linkedin_jobs

            # Seek
            seek_jobs = process_seek_jobs()
            total_new_jobs += seek_jobs

            # Process additional job sources
            additional_jobs = process_additional_sources()
            total_new_jobs += additional_jobs

            jobs_with_cv = []
            if total_new_jobs > 0:
                logger.info(f"Total new jobs from all sources: {total_new_jobs}")
                jobs_with_cv = process_job_matches()
            else:
                logger.info("No new jobs found from any sources")
            return jobs_with_cv

        except Exception as e:
            logger.error(f"Job scraping failed: {str(e)}")
            raise

    def process_linkedin_jobs() -> int:
        """Handle LinkedIn-specific scraping"""
        logger.info("Processing LinkedIn jobs...")
        try:
            target_urls = get_target_urls()
            existing_links = airtable.get_existing_job_links()
            new_jobs = 0
            for url in target_urls:
                logger.info(f"Scraping LinkedIn jobs from URL: {url}")
                job_list = scraper.scrape_job_page(url)
                if not job_list:
                    logger.warning(f"No jobs returned from scraper for URL = {url}")
                    continue
                for job_data in job_list:
                    job_url = job_data.get("job_url")
                    if not job_url or job_url in existing_links:
                        continue
                    normalized = normalize_job_data(job_data)
                    logger.debug(f"Normalized data: {normalized}")
                    cleaned_desc = content_cleaner.clean_html(normalized["Job Description"])
                    normalized["Job Description"] = cleaned_desc
                    if airtable.create_job_record(normalized):
                        new_jobs += 1
                        logger.info(f"Added LinkedIn job: {normalized['Job Title']} [{job_url}]")
            logger.info(f"Added {new_jobs} new LinkedIn jobs")
            return new_jobs
        except Exception as e:
            logger.error(f"LinkedIn job processing failed: {str(e)}")
            return 0

    def process_job_matches() -> List[dict]:
        """
        3) Load CV and produce match scores for each unprocessed job
        4) If score is above threshold => generate CV and store link
        """
        logger.info("Starting job matching process with detailed analysis")
        jobs_with_cv = []

        try:
            # Load your CV content
            cv_path = "user_cv/CV_Jack_HUI_08042025_EL.docx"
            logger.debug(f"Attempting to load CV from {cv_path}")
            cv_text = load_cv_content(cv_path)

            if not cv_text:
                logger.error("Failed to load CV content.")
                return jobs_with_cv

            # Fetch unprocessed jobs (no CV Link & has job desc)
            unprocessed_jobs = airtable.get_unprocessed_jobs()
            logger.info(f"Found {len(unprocessed_jobs)} unprocessed jobs in Airtable.")

            for record in unprocessed_jobs:
                fields = record['fields']
                job_desc = fields.get('Job Description', '')
                job_link = fields.get('Job Link', '')
                job_title = fields.get('Job Title', 'Unknown Position')

                if not job_desc:
                    logger.warning(f"Skipping match calculation for {job_link} - missing description.")
                    continue

                # Calculate match score
                try:
                    score, analysis = matcher.calculate_match_score(job_desc, cv_text)
                except ValueError as err:
                    logger.error(f"Score calculation failed for {job_link}: {str(err)}")
                    continue

                logger.info(f"Match analysis for '{job_title}' [{job_link}]: Score={score:.2f}/10")
                logger.debug(f"Key reasons: {analysis.get('reasons', [])}")
                logger.debug(f"Suggestions: {analysis.get('suggestions', [])}")

                # 3A) Always store the match score
                updated_record = airtable.update_cv_info(job_link=job_link, score=score, cv_url=None)
                if not updated_record:
                    logger.warning(f"Failed to update job with match score for {job_link}.")

                # 4) Generate customized CV if score >= threshold

                # debug logging
                # logger.debug(
                #    f"Current JOB_MATCH_THRESHOLD: {config.JOB_MATCH_THRESHOLD} (Type: {type(config.JOB_MATCH_THRESHOLD)})")
                # logger.debug(f"Job Score: {score} (Type: {type(score)})")

                if score >= config.JOB_MATCH_THRESHOLD:
                    logger.info(f"Threshold met ({score:.2f} >= {config.JOB_MATCH_THRESHOLD}). Generating CV.")

                    try:
                        cv_url = generate_targeted_cv(cv_text, fields, analysis)
                        updated_record = airtable.update_cv_info(
                            job_link=job_link,
                            score=score,
                            cv_url=cv_url
                        )
                        if updated_record:
                            logger.info(f"Generated targeted CV for '{job_title}' -> {cv_url}")
                            jobs_with_cv.append({
                                'Job Title': job_title,
                                'Job Link': job_link,
                                'CV URL': cv_url,
                                'Score': score
                            })
                        else:
                            logger.warning(f"Failed to attach CV link for {job_link}.")
                    except Exception as e:
                        logger.error(f"CV generation failed for {job_link}: {str(e)}")
                else:
                    logger.info(f"Score below threshold ({score:.2f} < {config.JOB_MATCH_THRESHOLD}) - no CV generated.")

            return jobs_with_cv

        except Exception as e:
            logger.error(f"Job matching process failed: {str(e)}")
            raise

    # ----------------------------------------------------------------------
    # Main Execution (Single Run, No Scheduler)
    # ----------------------------------------------------------------------
    try:
        # Perform one scraping+matching cycle
        jobs_with_cv = process_jobs()
        logger.info("Process complete. Exiting normally.")
        # --- Send notification ---
        matching_job_titles = [f"[{j.get('Job Title', 'Untitled Position')}]({j['Job Link']})" for j in jobs_with_cv]
        job_count = len(matching_job_titles)
        airtable_link = config.AIRTABLE_UI_URL
        notify_all(job_count, matching_job_titles, airtable_link)
    except KeyboardInterrupt:
        logger.info("Received shutdown signal (CTRL+C). Stopping...")
    except Exception as e:
        logger.error(f"Unexpected error caused exit: {str(e)}")

if __name__ == "__main__":
    main()
