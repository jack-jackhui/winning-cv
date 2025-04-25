# ui/job_search_ui.py
import streamlit as st
import os
import uuid
from pathlib import Path
from utils.logger import setup_logger
from utils.utils import Struct
import logging
from data_store.airtable_manager import AirtableManager
from job_processing.core import JobProcessor
from config.settings import Config

logger = logging.getLogger(__name__)

# === UPDATE: Helper for pretty field labels ===
FIELD_LABELS = {
    'user_email': 'User Email',
    'base_cv_path': 'Base CV Path',
    'linkedin_job_url': 'LinkedIn Jobs URL',
    'seek_job_url': 'Seek.com.au URL',
    'max_jobs_to_scrape': 'Max Jobs to Scrape',
    'additional_search_term': 'Indeed/Glassdoor Search Terms',
    'google_search_term': 'Google Custom Search',
    'location': 'Location',
    'hours_old': 'Time Since Post (hours)',
    'results_wanted': 'Results Wanted',
    'country': 'Country'
}

# === Readonly form display ===
def show_readonly_config(config: dict, field_labels: dict = None):
    """Display a config dictionary as a read-only form with two fields per row, excluding user_email."""
    field_labels = field_labels or {}
    # Exclude 'user_email'
    keys = [k for k in config.keys() if k in FIELD_LABELS and k != "user_email"]
    # Group keys into pairs for 2 per row
    pairs = [keys[i:i+2] for i in range(0, len(keys), 2)]

    for pair in pairs:
        cols = st.columns(len(pair))
        for i, k in enumerate(pair):
            label = field_labels.get(k, k.replace("_", " ").title())
            cols[i].text_input(label, value=str(config[k]), disabled=True)


def show_job_search_ui(user_email: str, airtable: AirtableManager):
    """UI for configuring and triggering job searches"""
    st.title("🔍 Configure Job Search")
    st.markdown(f"**Configured for:** {user_email}")

    # Get user config from "User Config" table
    user_config = airtable.get_user_config(user_email)
    edit_mode = st.session_state.get("edit_config", False)

    if user_config and not edit_mode:
        # Show config summary
        st.subheader("Your Current Configuration")
        # st.json(user_config)
        show_readonly_config(user_config, FIELD_LABELS)

        col1, col2, _ = st.columns([0.2, 0.3, 0.5])
        with col1:
            edit_clicked = st.button("✏️ Edit Configuration", key="edit_config_btn")
        with col2:
            run_clicked = st.button("🚀 Run Job Search With This Configuration", key="run_search_btn")
        if edit_clicked:
            st.session_state.edit_config = True
            st.rerun()
        if run_clicked:
            run_job_search(user_email, user_config)
    else:
        # Show form to create config
        with st.form(key="job_search_config"):
            # Section 1: Base CV
            st.subheader("1. Base CV Configuration")
            cv_file = st.file_uploader(
                "Upload your base CV (PDF/DOCX)",
                type=["pdf", "docx"],
                help="This will be used for matching and CV generation"
            )

            # Section 2: LinkedIn/Seek URL Configuration
            st.subheader("2. Job Board URLs")
            col1, col2 = st.columns(2)
            with col1:
                linkedin_url = st.text_input(
                    "LinkedIn Jobs URL",
                    value=user_config.get("LINKEDIN_JOB_URL", ""),
                    help="Paste a LinkedIn jobs search URL"
                )
            with col2:
                seek_url = st.text_input(
                    "Seek.com.au URL",
                    value=user_config.get("SEEK_JOB_URL", ""),
                    help="Paste a Seek job search URL"
                )

            # Section 3: Additional Search Parameters
            st.subheader("3. Additional Job Sources")
            search_term = st.text_input(
                "Indeed/Glassdoor Search Terms",
                value=user_config.get("ADDITIONAL_SEARCH_TERM",
                                          'software engineering'),
                help="Boolean search terms for Indeed/Glassdoor"
            )
            google_term = st.text_area(
                "Google Custom Search",
                value=user_config.get("GOOGLE_SEARCH_TERM",
                                          'software engineering or AI jobs near Melbourne, VIC since last week'),
                help="Natural language search terms for Google Jobs"
            )

            # Section 4: Search Parameters
            st.subheader("4. Search Parameters")
            col1, col2, col3 = st.columns(3)
            with col1:
                location = st.text_input(
                    "Location",
                    value=user_config.get("LOCATION", "Melbourne, VIC")
                )
                max_jobs = st.number_input(
                    "Max Jobs to Scrape",
                    min_value=5,
                    max_value=200,
                    value=int(user_config.get("MAX_JOBS_TO_SCRAPE", 10))
                )
            with col2:
                hours_old = st.number_input(
                    "Time Since Post (hours)",
                    min_value=24,
                    max_value=720,
                    value=int(user_config.get("HOURS_OLD", 168))
                )
                results_wanted = st.number_input(
                    "Results Wanted",
                    min_value=5,
                    max_value=50,
                    value=int(user_config.get("RESULTS_WANTED", 10))
                )
            with col3:
                country = st.selectbox(
                    "Country",
                    ["Australia", "USA", "Canada", "UK", "New Zealand"],
                    index=["Australia", "USA", "Canada", "UK", "New Zealand"].index(
                        user_config.get("COUNTRY", "Australia"))
                )

            # Form submission
            if st.form_submit_button("💾 Save & Run Search"):
                # Validate inputs
                if not all([linkedin_url, seek_url, search_term]):
                    st.error("Please fill all required fields")
                    st.stop()

                if not cv_file:
                    if not user_config.get("BASE_CV_PATH"):
                        st.error("Please upload a CV file")
                        st.stop()
                    else:
                        cv_path = user_config["BASE_CV_PATH"]
                        cv_wp_url = user_config.get("BASE_CV_LINK", "")  # Fetch existing link if present
                else:
                    # Save uploaded CV
                    cv_dir = Path(f"user_cv/{user_email}")
                    cv_dir.mkdir(parents=True, exist_ok=True)
                    cv_path = cv_dir / f"base_cv_{uuid.uuid4()}{Path(cv_file.name).suffix}"

                    with open(cv_path, "wb") as f:
                        f.write(cv_file.getbuffer())

                    # ---- upload to wordpress ----
                    from ui.helpers import upload_pdf_to_wordpress
                    cv_wp_url = upload_pdf_to_wordpress(
                        file_path=str(cv_path),
                        filename=cv_path.name,
                        wp_site=Config.wordpress_site,
                        wp_user=Config.wordpress_username,
                        wp_app_password=Config.wordpress_app_password
                    )

                    st.success(f"CV saved to: {cv_path}")

                # Build config dictionary
                config_data = {
                    "user_email": user_email,
                    "base_cv_path": str(cv_path),
                    "base_cv_link": cv_wp_url,
                    "linkedin_job_url": linkedin_url,
                    "seek_job_url": seek_url,
                    "max_jobs_to_scrape": max_jobs,
                    "additional_search_term": search_term,
                    "google_search_term": google_term,
                    "location": location,
                    "hours_old": hours_old,
                    "results_wanted": results_wanted,
                    "country": country
                }

                # Save to Airtable
                if airtable.save_user_config(config_data):
                    st.session_state.current_config = config_data
                    st.success("Configuration saved!")

                    # Trigger job search
                    with st.spinner("🚀 Launching job search..."):
                        try:
                            # Merge config with defaults, giving precedence to user config
                            defaults = {k.lower(): v for k, v in Config.__dict__.items() if not k.startswith("_")}
                            merged_config = {**defaults, **config_data}
                            processor = JobProcessor(
                                config=Struct(**merged_config),
                                airtable=airtable  # Pass through existing instance
                            )
                            results = processor.process_jobs()
                            st.session_state.search_results = results
                            st.rerun()
                        except Exception as e:
                            logger.error(f"Job search failed: {str(e)}")
                            st.error("Job search failed - check logs for details")
                else:
                    st.error("Failed to save configuration")

    # Always show job results table
    display_search_results(user_email=user_email)

def run_job_search(user_email, config_from_airtable):
    # Merge config_from_airtable (lowercase keys) with defaults
    defaults = {k.lower(): v for k, v in Config.__dict__.items() if not k.startswith("_")}
    # Convert all keys to lowercase
    config_lower = {k.lower(): v for k, v in config_from_airtable.items()}
    merged_config = {**defaults, **config_lower}
    # Create AirtableManager for "Job List" table
    joblist_manager = AirtableManager(
        Config.AIRTABLE_API_KEY,
        Config.AIRTABLE_BASE_ID,
        Config.AIRTABLE_TABLE_ID
    )
    processor = JobProcessor(
        config=Struct(**merged_config),
        airtable=joblist_manager
    )
    processor.process_jobs()
    st.success("Job search complete. Results updated!")

def display_search_results(user_email):
    """Show results after search completes"""
    # Create AirtableManager for "Job List" table

    from ui.helpers import format_job_description

    joblist_manager = AirtableManager(
        Config.AIRTABLE_API_KEY,
        Config.AIRTABLE_BASE_ID,
        Config.AIRTABLE_TABLE_ID
    )

    st.subheader("🔎 Search Results")

    records = joblist_manager.get_records_by_filter(f"{{User Email}} = '{user_email}'")
    if not records:
        st.info("No job results found yet. Run a search to get started!")
        return

    for rec in records:
        job = rec['fields']
        with st.expander(f"{job.get('Job Title', '')} - Score: {job.get('Matching Score', '')}/10"):
            reasons = job.get('Match Reasons', 'No analysis available')
            suggestions = job.get('Match Suggestions', 'No analysis available')

            col1, col2 = st.columns([3, 1])

            with col1:
                desc = job.get('Job Description', 'N.A.')
                st.markdown(f"**Description:**\n\n{format_job_description(desc)}")
                st.markdown(f"**Matching Score:** {job.get('Matching Score', 'N.A.')}")
                st.markdown(f"**Job Link** - [Link]({job.get('Job Link', '#')})")
                st.markdown(f"**Posted:** {job.get('Job Date', 'N.A.')}")

            with col2:
                if job.get('CV Link'):
                    st.markdown(f"[📄 Download Custom CV]({job['CV Link']})")
                else:
                    st.warning("Match score too low. No CV generated")

            st.markdown("---")
            if reasons:
                st.markdown("**Top Matching Factors:**")
                st.markdown(f"- " + "\n- ".join(reasons.splitlines()) if isinstance(reasons, str) else reasons)
            if suggestions:
                st.markdown("**Suggestions to Improve Your CV:**")
                st.markdown(
                    f"- " + "\n- ".join(suggestions.splitlines()) if isinstance(suggestions, str) else suggestions)