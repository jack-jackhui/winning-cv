from pyairtable import Api
from pyairtable.formulas import AND, Field, EQ, NE
from utils.logger import setup_logger
from datetime import datetime
import os
import logging

class AirtableManager:
    def __init__(self, api_key, base_id, table_id):
        self.api = Api(api_key)
        self.table = self.api.table(base_id, table_id)
        self.logger = setup_logger(__name__)

        self._history_field_map = {
            "user_email": "user_email",
            "job_title": "job_title",
            "job_description": "job_description",
            "instructions": "Instructions",
            "cv_markdown": "cv_markdown",
            "cv_pdf_url": "cv_pdf_url",
            # "created_at" is auto‐populated in Airtable as a "Created Time" field
        }

    def get_existing_job_links(self):
        """Get all existing job links to prevent duplicates"""
        try:
            records = self.table.all()
            return {rec['fields'].get('Job Link') for rec in records}
        except Exception as e:
            self.logger.error(f"Failed to fetch existing jobs: {str(e)}")
            return set()

    def create_job_record(self, job_data):
        """Create new job record with proper column mapping"""
        try:
            record = self.table.create({
                'Job Title': job_data.get('Job Title'),
                'Job Description': job_data.get('Job Description'),
                'Job Date': self._format_date(job_data.get('Job Date')),
                'Job Link': job_data.get('Job Link'),
                'Matching Score': job_data.get('score', 0),
                'CV Link': job_data.get('cv_url', '')
            })
            self.logger.info(f"Created job: {record['id']}")
            return record
        except Exception as e:
            self.logger.error(f"Create failed: {str(e)}")
            return None

    def update_cv_info(self, job_link, score, cv_url):
        """Update matching score and CV link for existing job"""
        try:
            record = self.table.first(
                formula=f"FIND('{job_link}', {{Job Link}})",
                fields=["Job Link"]
            )
            if record:
                return self.table.update(
                    record['id'],
                    {'Matching Score': score, 'CV Link': cv_url}
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
                fields=["Job Title", "Job Description", "Job Link"]
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