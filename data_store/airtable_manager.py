from pyairtable import Api
from pyairtable.formulas import AND, Field, EQ, NE
from utils.logger import setup_logger
from datetime import datetime
import os
import logging
from config.settings import Config

class AirtableManager:
    def __init__(self, api_key, base_id, table_id):
        self.api = Api(api_key)
        self.base_id = base_id
        self.table = self.api.table(base_id, table_id)
        self.logger = logging.getLogger(self.__class__.__name__)

        self.user_config_table = self.api.table(
            base_id,
            Config.AIRTABLE_TABLE_ID_USER_CONFIGS  # Get from settings
        )

        self._history_field_map = {
            "user_email": "user_email",
            "job_title": "job_title",
            "job_description": "job_description",
            "instructions": "Instructions",
            "cv_markdown": "cv_markdown",
            "cv_pdf_url": "cv_pdf_url",
            # "created_at" is auto‐populated in Airtable as a "Created Time" field
        }

    def job_exists(self, job_link):
        # Use formula helper for safety
        formula = EQ(Field("Job Link"), job_link)
        records = self.table.all(formula=str(formula))
        return len(records) > 0

    def get_existing_job_links(self):
        """Get all existing job links to prevent duplicates"""
        try:
            records = self.table.all()
            return {rec['fields']['Job Link'] for rec in records if 'Job Link' in rec['fields']}
        except Exception as e:
            self.logger.error(f"Failed to fetch existing jobs: {str(e)}")
            return set()

    def create_job_record(self, job_data, user_email: str = "system"):
        """Create new job record with proper column mapping"""
        try:
            record = self.table.create({
                'User Email': user_email,
                'Job Title': job_data.get('Job Title'),
                'Job Description': job_data.get('Job Description'),
                'Job Date': self._format_date(job_data.get('Job Date')),
                'Job Link': job_data.get('Job Link'),
                'Company': job_data.get('Company'),
                'Location': job_data.get('Location'),
                'Matching Score': job_data.get('score', 0),
                'CV Link': job_data.get('cv_url', '')
            })
            self.logger.info(f"Created job: {record['id']}")
            return record
        except Exception as e:
            self.logger.error(f"Create failed: {str(e)}")
            return None

    def update_cv_info(self, job_link, score, cv_url, reasons=None, suggestions=None):
        """Update matching score and CV link for existing job"""
        try:
            # record = self.table.first(
            #    formula=f"FIND('{job_link}', {{Job Link}})",
            #    fields=["Job Link"]
            # )
            record = self.table.first(
                formula=str(EQ(Field("Job Link"), job_link)),
                fields=["Job Link"]
            )
            if record:
                update_fields = {
                    'Matching Score': score,
                    'CV Link': cv_url
                }
                if reasons is not None:
                    update_fields['Match Reasons'] = "\n".join(reasons) if isinstance(reasons, list) else reasons
                if suggestions is not None:
                    update_fields['Match Suggestions'] = "\n".join(suggestions) if isinstance(suggestions,
                                                                                              list) else suggestions
                return self.table.update(
                    record['id'],
                    update_fields
                )
            return None
        except Exception as e:
            self.logger.error(f"Update failed: {str(e)}")
            return None

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
                return dt.strftime('%Y-%m-%d')  # Airtable's preferred format
            except (ValueError, TypeError):
                continue
        return datetime.now().strftime('%Y-%m-%d')

    def get_unprocessed_jobs(self):
        """Get unprocessed jobs with filter formula"""
        try:
            formula = AND(
                EQ(Field("CV Link"), ""),
                NE(Field("Job Description"),"")
            )
            return self.table.all(
                formula=str(formula),
                fields=["Job Title", "Job Description", "Job Link", "Company"]
            )
        except Exception as e:
            self.logger.error(f"Fetch unprocessed failed: {str(e)}")
            return []

    # ──────────────────────────────────────────────────────────
    # HISTORY TABLE METHODS
    # ──────────────────────────────────────────────────────────
    def create_history_record(self, data: dict) -> bool:
        """
        data keys (snake_case) expected:
          - user_email
          - job_title
          - job_description
          - instructions
          - cv_markdown
          - cv_pdf_url
        'created_at' is auto‐populated in Airtable as a Created Time field.
        """
        # map to actual Airtable field names
        airtable_fields = {}
        for key, val in data.items():
            field_name = self._history_field_map.get(key)
            if field_name:
                airtable_fields[field_name] = val
        try:
            rec = self.table.create(airtable_fields)
            self.logger.info("History record created: %s", rec["id"])
            return True
        except Exception as e:
            self.logger.error("create_history_record error: %s", e)
            return False

    def get_all_records(self) -> list:
        """Return all records in whichever table this instance points at."""
        try:
            return self.table.all()
        except Exception as e:
            self.logger.error("get_all_records error: %s", e)
            return []

    def get_records_by_filter(self, formula: str) -> list:
        """
        Run any Airtable formula, e.g. "{User Email} = 'joe@example.com'".
        Returns matching records.
        """
        try:
            return self.table.all(formula=formula)
        except Exception as e:
            self.logger.error("get_records_by_filter error: %s", e)
            return []

    def get_history_by_user(self, user_email: str) -> list:
        """
        Convenience wrapper to fetch only this user's history
        """
        field_name = self._history_field_map["user_email"]
        safe_email = user_email.replace("'", "\\'")
        formula = f"{{{field_name}}} = '{safe_email}'"
        return self.get_records_by_filter(formula)

    # ──────────────────────────────────────────────────────────
    # USER CONFIG TABLE METHODS
    # ──────────────────────────────────────────────────────────
    def get_user_config(self, user_email: str) -> dict:
        """Retrieve user's saved configuration"""
        try:
            formula = f"{{user_email}} = '{user_email}'"
            records = self.user_config_table.all(
                formula=formula,
                max_records=1  # Get only the first match
            )
            return records[0]['fields'] if records else {}
        except Exception as e:
            self.logger.error(f"Config fetch failed: {str(e)}")
            return {}

    def save_user_config(self, config_data: dict) -> bool:
        """Store/update user configuration"""
        try:
            existing = self.user_config_table.first(
                formula=f"{{user_email}} = '{config_data['user_email']}'"
            )

            # Map to lowercase field names expected by Airtable
            fields = {
                "user_email": config_data["user_email"],
                "base_cv_path": config_data["base_cv_path"],
                "base_cv_link": config_data.get("base_cv_link", ""),
                "linkedin_job_url": config_data["linkedin_job_url"],
                "seek_job_url": config_data["seek_job_url"],
                "max_jobs_to_scrape": config_data["max_jobs_to_scrape"],
                "additional_search_term": config_data["additional_search_term"],
                "google_search_term": config_data["google_search_term"],
                "location": config_data["location"],
                "hours_old": config_data["hours_old"],
                "results_wanted": config_data["results_wanted"],
                "country": config_data["country"]
            }

            if existing:
                self.user_config_table.update(existing['id'], fields)
            else:
                self.user_config_table.create(fields)

            return True
        except Exception as e:
            self.logger.error(f"Config save failed: {str(e)}")
            return False