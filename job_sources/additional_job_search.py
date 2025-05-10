# job_sources/additional_job_search.py
import pandas as pd
from jobspy import scrape_jobs
from typing import Optional, List, Dict
import logging

logger = logging.getLogger(__name__)

class AdditionalJobProcessor:
    def __init__(self, content_cleaner, config):
        self.content_cleaner = content_cleaner
        self.config = config

    def scrape_and_process_jobs(self) -> List[Dict]:
        """Main method to handle full additional job processing"""
        try:
            jobs_df = self._scrape_jobs()
            if jobs_df.empty:
                return []

            raw_jobs = self._prepare_for_airtable(jobs_df)
            return self._process_jobs(raw_jobs)

        except Exception as e:
            logger.error(f"Additional job processing failed: {str(e)}")
            return []

    def _scrape_jobs(self) -> pd.DataFrame:
        """Core scraping functionality"""
        return scrape_jobs(
            site_name=["indeed", "glassdoor", "google"],
            search_term=self.config.additional_search_term,
            google_search_term=self.config.google_search_term or self.config.additional_search_term,
            location=self.config.location,
            job_type="fulltime",
            results_wanted=self.config.results_wanted,
            hours_old=self.config.hours_old,
            country_indeed=self.config.country
        )

    def _prepare_for_airtable(self, jobs_df: pd.DataFrame) -> List[Dict]:
        """Transform scraped data to raw job dicts"""
        if jobs_df.empty:
            return []

        # Remove duplicate columns
        jobs_df = jobs_df.loc[:, ~jobs_df.columns.duplicated()]

        # Ensure expected columns exist
        for col in ['salary', 'employment_type', 'description']:
            if col not in jobs_df.columns:
                jobs_df[col] = None

        jobs_df = jobs_df.rename(columns={
            'job_url': 'url',
            'date_posted': 'posted_date',
            'job_type': 'employment_type'
        })

        return jobs_df[[
            'title', 'company', 'location', 'url',
            'posted_date', 'employment_type',
            'salary', 'description'
        ]].to_dict('records')

    def _process_jobs(self, raw_jobs: List[Dict]) -> List[Dict]:
        """Clean and normalize job data"""
        processed_jobs = []

        for job in raw_jobs:
            normalized = self._normalize_job(job)
            if not normalized:
                continue

            # clean the one‐and‐only “Job Description” field
            raw_html = normalized.get("Job Description", "")
            normalized["Job Description"] = self.content_cleaner.clean_html(raw_html)
            processed_jobs.append(normalized)

        return processed_jobs

    def _normalize_job(self, job: Dict) -> Dict:
        """Ensure consistent Airtable schema"""
        try:
            return {
                "Job Title": job.get("title", "No Title"),
                "Job Link": job.get("url", ""),
                "Job Date": job.get("posted_date", ""),
                "Company": job.get("company", "Unknown Company"),
                "Location": job.get("location", ""),
                "Job Description": job.get("description", ""),
                "Salary": job.get("salary", ""),
                "Employment Type": job.get("employment_type", "")
            }
        except KeyError as e:
            logger.warning(f"Invalid job format: {str(e)}")
            return None
