# job_processing/core.py
import logging
import os
import uuid
from datetime import datetime
from typing import List, Dict
from concurrent.futures import ThreadPoolExecutor, as_completed

from data_store.airtable_manager import AirtableManager
from job_sources.linkedin_job_scraper import LinkedInJobScraper
from job_sources.seek_job_scraper import SeekJobScraper
from job_sources.additional_job_search import AdditionalJobProcessor
from utils.content_cleaner import ContentCleaner
from utils.cv_loader import load_cv_content
from utils.utils import create_pdf, canonicalize_url
from utils.matcher import JobMatcher
from cv.cv_generator import CVGenerator

logger = logging.getLogger(__name__)

class JobProcessor:
    def __init__(self, config, airtable: AirtableManager = None):
        self.config = config
        self.airtable = airtable or AirtableManager(
            config.airtable_api_key,
            config.airtable_base_id,
            config.airtable_table_id
        )
        self.linkedin_scraper = LinkedInJobScraper(config.linkedin_job_url)
        self.seek_scraper = SeekJobScraper(config.seek_job_url)
        self.content_cleaner = ContentCleaner(config.max_description_length)
        self.matcher = JobMatcher()
        self.additional_processor = AdditionalJobProcessor(
            content_cleaner=self.content_cleaner,
            config=config
        )

    def process_jobs(self) -> List[dict]:
        """Main processing pipeline"""
        logger.info("Starting parallel scraping of all sources")

        """ old code for sequential run
                try:
                    total_new = (
                            self._process_linkedin_jobs() +
                            self._process_seek_jobs() +
                            self._process_additional_sources()
                    )

                    if total_new > 0:
                        return self._process_job_matches()
                    return []
                except Exception as e:
                    logger.error(f"Processing failed: {str(e)}")
                    raise
                """

        # Define a small mapping of names → methods
        sources = {
            "LinkedIn": self._process_linkedin_jobs,
            "Seek": self._process_seek_jobs,
            "Additional Sources": self._process_additional_sources
        }
        results = {}
        # Spin up a threadpool
        with ThreadPoolExecutor(max_workers=len(sources)) as pool:
            future_to_name = {
                pool.submit(fn): name for name, fn in sources.items()
            }
            for future in as_completed(future_to_name):
                name = future_to_name[future]
                try:
                    count = future.result()
                    logger.info(f"✔️ {name} added {count} new jobs")
                    results[name] = count
                except Exception as e:
                    logger.error(f"❌ {name} failed: {e}")
                    results[name] = 0
        total_new = sum(results.values())
        logger.info(f"🔢 Total new jobs from all sources: {total_new}")
        if total_new > 0:
            return self._process_job_matches()
        return []

    def _process_linkedin_jobs(self) -> int:
        """Handle LinkedIn-specific scraping"""
        logger.info("Processing LinkedIn jobs...")
        try:
            target_urls = self.get_target_urls()
            existing_links = set(canonicalize_url(link) for link in self.airtable.get_existing_job_links())
            # existing_links = self.airtable.get_existing_job_links()
            new_jobs = 0
            for url in target_urls:
                logger.info(f"Scraping LinkedIn jobs from URL: {url}")
                job_list = self.linkedin_scraper.scrape_job_page(url)
                if not job_list:
                    logger.warning(f"No jobs returned from scraper for URL = {url}")
                    continue
                for job_data in job_list:
                    job_url = canonicalize_url(job_data.get("job_url"))
                    if not job_url or job_url in existing_links:
                        continue
                    # Airtable-level check (race condition safety)
                    if self.airtable.job_exists(job_url):
                        logger.info(f"Job {job_url} already exists in Airtable, skipping.")
                        existing_links.add(job_url)
                        continue
                    normalized = self.normalize_job_data(job_data)
                    logger.debug(f"Normalized data: {normalized}")
                    cleaned_desc = self.content_cleaner.clean_html(normalized["Job Description"])
                    normalized["Job Description"] = cleaned_desc
                    if self.airtable.create_job_record(normalized, user_email=self.config.user_email):
                        new_jobs += 1
                        logger.info(f"Added LinkedIn job: {normalized['Job Title']} [{job_url}]")
            logger.info(f"Added {new_jobs} new LinkedIn jobs")
            return new_jobs
        except Exception as e:
            logger.error(f"LinkedIn job processing failed: {str(e)}")
            return 0

    def _process_seek_jobs(self) -> int:
        """Handle Seek.com.au-specific scraping"""
        logger.info("Processing Seek jobs...")
        try:
            # Scrape jobs from Seek
            job_list = self.seek_scraper.scrape_jobs()
            if not job_list:
                logger.warning("No jobs returned from Seek scraper.")
                return 0
            # existing_links = self.airtable.get_existing_job_links()
            existing_links = set(canonicalize_url(link) for link in self.airtable.get_existing_job_links())
            new_jobs = 0
            for job_data in job_list:
                job_url = canonicalize_url(job_data.get("job_url"))
                logger.debug(f"Processing job, url={job_url}")
                if not job_url:
                    logger.warning("Job missing 'job_url', skipping.")
                    continue
                if job_url in existing_links:
                    logger.info(f"Job {job_url} already exists, skipping.")
                    continue
                # Airtable-level check (race condition safety)
                if self.airtable.job_exists(job_url):
                    logger.info(f"Job {job_url} already exists in Airtable, skipping.")
                    existing_links.add(job_url)
                    continue
                normalized = self.normalize_seek_job_data(job_data)
                cleaned_desc = self.content_cleaner.clean_html(normalized["Job Description"])
                normalized["Job Description"] = cleaned_desc
                if self.airtable.create_job_record(normalized, user_email=self.config.user_email):
                    new_jobs += 1
                    logger.info(f"Added Seek job: {normalized['Job Title']} [{job_url}]")
            logger.info(f"Added {new_jobs} new Seek jobs")
            return new_jobs
        except Exception as e:
            logger.error(f"Seek job processing failed: {str(e)}")
            return 0

    def _process_additional_sources(self) -> int:
        """Handle other job sources (Indeed, Glassdoor, Google)"""
        logger.info("Processing additional job sources...")
        try:
            processed_jobs = self.additional_processor.scrape_and_process_jobs()
            if not processed_jobs:
                return 0
            # existing_links = self.airtable.get_existing_job_links()
            existing_links = set(canonicalize_url(link) for link in self.airtable.get_existing_job_links())
            new_jobs_added = 0

            for job in processed_jobs:
                job_url = canonicalize_url(job.get('Job Link'))
                if not job_url or job_url in existing_links:
                    continue
                # Airtable-level check (race condition safety)
                if self.airtable.job_exists(job_url):
                    logger.info(f"Job {job_url} already exists in Airtable, skipping.")
                    existing_links.add(job_url)
                    continue
                job['Job Link'] = job_url  # Overwrite with canonicalized link
                if self.airtable.create_job_record(job, user_email=self.config.user_email):
                    new_jobs_added += 1
                    logger.info(f"Added job from additional source: {job['Job Title']}")
            logger.info(f"Added {new_jobs_added} jobs from additional sources")
            return new_jobs_added
        except Exception as e:
            logger.error(f"Additional job processing failed: {str(e)}")
            return 0

    def _process_job_matches(self) -> List[Dict]:
        """
        3) Load CV and produce match scores for each unprocessed job
        4) If score is above threshold => generate CV and store link
        """
        logger.info("Starting job matching process with detailed analysis")
        jobs_with_cv = []

        try:
            # Load your CV content
            cv_path = self.config.base_cv_path
            logger.debug(f"Attempting to load CV from {cv_path}")
            cv_text = load_cv_content(cv_path)

            if not cv_text:
                logger.error("Failed to load CV content.")
                return jobs_with_cv

            # Fetch unprocessed jobs (no CV Link & has job desc)
            unprocessed_jobs = self.airtable.get_unprocessed_jobs()
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
                    score, analysis = self.matcher.calculate_match_score(job_desc, cv_text)
                except ValueError as err:
                    logger.error(f"Score calculation failed for {job_link}: {str(err)}")
                    continue

                logger.info(f"Match analysis for '{job_title}' [{job_link}]: Score={score:.2f}/10")
                logger.debug(f"Key reasons: {analysis.get('reasons', [])}")
                logger.debug(f"Suggestions: {analysis.get('suggestions', [])}")

                # 3) Always store the match score
                updated_record = self.airtable.update_cv_info(
                    job_link=job_link,
                    score=score,
                    cv_url=None,
                    reasons=analysis.get('reasons') if analysis else None,
                    suggestions=analysis.get('suggestions') if analysis else None,
                )
                if not updated_record:
                    logger.warning(f"Failed to update job with match score for {job_link}.")

                # 4) Generate customized CV if score >= threshold
                if score >= self.config.job_match_threshold:
                    logger.info(f"Threshold met ({score:.2f} >= {self.config.job_match_threshold}). Generating CV.")

                    try:
                        cv_url = self.generate_targeted_cv(cv_text, fields, analysis)
                        updated_record = self.airtable.update_cv_info(
                            job_link=job_link,
                            score=score,
                            cv_url=cv_url,
                            reasons=analysis.get('reasons') if analysis else None,
                            suggestions=analysis.get('suggestions') if analysis else None,
                        )
                        if updated_record:
                            logger.info(f"Generated targeted CV for '{job_title}' -> {cv_url}")
                            jobs_with_cv.append({
                                'Job Title': job_title,
                                'Company': fields.get('Company', 'Unknown Company'),
                                'Job Link': job_link,
                                'CV URL': cv_url,
                                'Score': score
                            })
                        else:
                            logger.warning(f"Failed to attach CV link for {job_link}.")
                    except Exception as e:
                        logger.error(f"CV generation failed for {job_link}: {str(e)}")
                else:
                    logger.info(
                        f"Score below threshold ({score:.2f} < {self.config.job_match_threshold}) - no CV generated.")

            return jobs_with_cv

        except Exception as e:
            logger.error(f"Job matching process failed: {str(e)}")
            raise

    # ----------------------------------------------------------------------
    # Helper Functions
    # ----------------------------------------------------------------------
    def get_target_urls(self) -> List[str]:
        """
        Return URLs to scrape from config or from a database.
        Adjust or extend this logic as needed.
        """
        linkedin_urls = [url.strip() for url in self.config.linkedin_job_url.split(",")
                         if url.strip()]
        return linkedin_urls or [os.getenv("LINKEDIN_JOB_URL")]

    def generate_targeted_cv(self, cv_text: str, job_data: Dict, analysis: Dict) -> str:
        """
        Generate a custom CV using GPT-based approach in CVGenerator.
        Returns a WordPress public URL to the new CV.
        """
        from ui.helpers import upload_pdf_to_wordpress
        from config.settings import Config

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
            return None
        logger.info(f"Generated PDF CV: {pdf_path}")

        # ---- Upload to WP ----
        try:
            wp_url = upload_pdf_to_wordpress(
                file_path=pdf_path,
                filename=os.path.basename(pdf_filename),
                wp_site=Config.WORDPRESS_SITE,
                wp_user=Config.WORDPRESS_USERNAME,
                wp_app_password=Config.WORDPRESS_APP_PASSWORD
            )
            logger.debug(f"Uploaded CV to web server: {wp_url}")
            return wp_url
        except Exception as e:
            logger.error(f"Failed to upload PDF to web server: {e}")
            return None

    def normalize_job_data(self, scraped_data: Dict) -> Dict:
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

    def normalize_seek_job_data(self, scraped_data: Dict) -> Dict:
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