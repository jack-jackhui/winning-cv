# ui/job_search_ui.py
import streamlit as st
import math
import uuid
from pathlib import Path
# from utils.logger import setup_logger
from utils.utils import Struct
import logging
from data_store.airtable_manager import AirtableManager
from job_processing.core import JobProcessor
from config.settings import Config
from urllib.parse import urlencode, quote

logger = logging.getLogger(__name__)

LINKEDIN_GEOID_MAP = {
    "Australia": "101452733",
    "Greater Sydney": "90009524",
    "Greater Melbourne": "90009521",
    "United State": "103644278",
    "United Kindom": "101165590",
    "Canada": "101174742",
    "Hong Kong": "103291313",
    "Singapore": "102454443"
    # add more as needed
}

def build_linkedin_search_url(keywords, location, posted_hours=None, country=None, max_jobs=None, geoId_map=None):
    if geoId_map is None:
        geoId_map = LINKEDIN_GEOID_MAP  # Use global mapping
    base = "https://www.linkedin.com/jobs/search/"
    params = {}
    if keywords:
        params['keywords'] = keywords.replace(",", " OR ")
    if location:
        geoId = geoId_map.get(location, "")
        if geoId:
            params['geoId'] = geoId
        # Optionally, still set 'location' param for UI, but geoId does the work
        params['location'] = location
    if posted_hours:
        # LinkedIn uses f_TPR=rXXXXXX where XXXXXX is seconds
        try:
            seconds = int(posted_hours) * 3600
            params['f_TPR'] = f"r{seconds}"
        except:
            pass
    return f"{base}?{urlencode(params)}"

def build_seek_url(keywords, category, location, daterange=None, salaryrange=None, salarytype="annual"):
    """
    Build a SEEK job search URL from user inputs.
    """
    # Convert spaces to dashes and lowercase for URL path parts
    keywords_path = quote(keywords.replace(" ", "-"))
    category_path = quote(category.strip().replace(" ", "-").lower())
    location_path = quote(location.strip().replace(" ", "-").lower())
    base = f"https://www.seek.com.au/{keywords_path}-jobs-in-{category_path}/in-{location_path}"
    params = {}
    if daterange:
        params['daterange'] = str(daterange)
    if salaryrange:
        params['salaryrange'] = salaryrange
    if salarytype:
        params['salarytype'] = salarytype
    if params:
        return f"{base}?{urlencode(params)}"
    else:
        return base

# Helper for pretty field labels ===
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

# Create a Config INSTANCE
config = Config()

@st.dialog("🚀 Running Job Search", width="large")
def _run_search_dialog(user_email, config_from_airtable):
    """
    This function runs in a modal dialog.
    It must put anything you want *inside* the dialog here.
    """
    # simple progress + status text
    progress = st.progress(0)
    status = st.empty()

    # Step 1: merge defaults + user config
    status.text("📦 Merging configuration...")
    defaults = {
        k.lower(): v
        for k, v in Config.__dict__.items()
        if not k.startswith("_")
    }
    cfg_lower = {k.lower(): v for k, v in config_from_airtable.items()}
    merged = {**defaults, **cfg_lower}
    progress.progress(15)

    # Step 2: init Airtable manager
    status.text("🔗 Initializing Airtable manager...")
    joblist_mgr = AirtableManager(
        Config.AIRTABLE_API_KEY,
        Config.AIRTABLE_BASE_ID,
        Config.AIRTABLE_TABLE_ID
    )
    progress.progress(30)

    # Step 3: build JobProcessor
    status.text("⚙️ Initializing job processor...")
    processor = JobProcessor(
        config=Struct(**merged),
        airtable=joblist_mgr
    )
    progress.progress(45)

    # Step 4: run the actual search
    status.text("🚀 Scraping jobs and matching... this may take a minute.")
    results = processor.process_jobs()
    progress.progress(80)

    # Step 5: finalize
    status.text("✅ Finalizing results...")
    st.session_state.search_results = results
    progress.progress(100)

    st.success("🎉 Job search complete! Close this dialog to view your results.")
    # on click → rerun (which will close dialog and fall back to normal UI)
    if st.button("Close"):
        st.rerun()

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
    if user_email:
        st.markdown(f"**Configured for:** {user_email}")
    else:
        st.markdown("**Preview Mode** (Log in to save configurations)")

    # Get user config from "User Config" table
    user_config = airtable.get_user_config(user_email) if user_email else {}
    edit_mode = st.session_state.get("edit_config", False)

    # PRE-SEED session_state on the first edit render
    if user_email and user_config and edit_mode and not st.session_state.get("form_initialized"):
        # map AIRTABLE keys → form keys
        mapping = {
            "linkedin_url":          user_config.get("linkedin_job_url", ""),
            "seek_url":              user_config.get("seek_job_url", ""),
            "search_term":           user_config.get("additional_search_term", ""),
            "google_term":           user_config.get("google_search_term", ""),
            "location":              user_config.get("location", "Melbourne, VIC"),
            "max_jobs":              int(user_config.get("max_jobs_to_scrape", 5)),
            "hours_old":             int(user_config.get("hours_old", 48)),
            "results_wanted":        int(user_config.get("results_wanted", 5)),
            "country":               user_config.get("country", "Australia"),
        }
        for k, v in mapping.items():
            st.session_state[k] = v
        st.session_state["form_initialized"] = True

    if user_email and user_config and not edit_mode:
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
            # open modal dialog and immediately return
            _run_search_dialog(user_email, user_config)
            return
    else:
        # Show form to create config
        with st.form(key="job_search_config"):
            # Section 1: Base CV
            st.subheader("1. Base CV Configuration")
            cv_file = st.file_uploader(
                "Upload your base CV (PDF/DOCX)",
                type=["pdf", "docx"],
                key="cv_file",
                help="This will be used for matching and CV generation"
            )

            # Section 2: LinkedIn/Seek URL Configuration
            st.subheader("2. Job Board URLs")
            """
            col1, col2 = st.columns(2)
            with col1:
                linkedin_url = st.text_input(
                    "LinkedIn Jobs URL",
                    # value=user_config.get("LINKEDIN_JOB_URL", ""),
                    key="linkedin_url",
                    help="Paste a LinkedIn jobs search URL"
                )
            with col2:
                seek_url = st.text_input(
                    "Seek.com.au URL",
                    # value=user_config.get("SEEK_JOB_URL", ""),
                    key="seek_url",
                    help="Paste a Seek job search URL"
                )
            """

            # Common keywords box, used for both LinkedIn and SEEK
            search_keywords = st.text_input(
                "Job Search Keywords (used for both LinkedIn and SEEK)",
                key="search_keywords",
                help="Keywords or job titles to search for. Example: 'Technology Head', 'Software Engineering Manager'"
            )
            # LinkedIn uses this and a shared location (if any)
            # Add any LinkedIn-specific fields here if needed
            # SEEK-specific options (apart from keywords)
            seek_category = st.text_input(
                "SEEK Category",
                value="information communication technology",
                key="seek_category",
                help="SEEK job category, e.g. 'information communication technology', 'Healthcare', etc."
            )
            seek_salaryrange = st.text_input(
                "SEEK Salary Range (e.g. 200000-)",
                value="",
                key="seek_salaryrange",
                help = "Minimum salary (leave blank for any). Format: '100000-' for minimum, '100000-150000' for a range."
            )
            seek_salarytype = st.selectbox(
                "SEEK Salary Type",
                ["annual", "hourly"],
                index=0,
                key="seek_salarytype",
                help="Choose 'annual' for yearly salaries (most jobs), or 'hourly' for contract/hourly roles."
            )

            # Section 3: Additional Search Parameters
            st.subheader("3. Additional Job Sources")
            search_term = st.text_input(
                "Indeed/Glassdoor Search Terms",
                # value=user_config.get("ADDITIONAL_SEARCH_TERM",
                #                          'software engineering'),
                key="search_term",
                help="Search terms for Indeed/Glassdoor"
            )
            google_term = st.text_input(
                "Google Custom Search",
                # value=user_config.get("GOOGLE_SEARCH_TERM",
                #                          'software engineering or AI jobs near Melbourne, VIC since last week'),
                key="google_term",
                help="Natural language search terms for Google Jobs"
            )

            # Section 4: Search Parameters
            st.subheader("4. Search Parameters")
            col1, col2, col3 = st.columns(3)
            with col1:
                location = st.text_input(
                    "Location",
                    key="location",
                    help="The city or region to search for jobs. Example: 'Melbourne, VIC' or 'Greater Sydney'."
                )
                max_jobs = st.number_input(
                    "Max Jobs to Scrape",
                    min_value=1,
                    max_value=50,
                    key="max_jobs",
                    help="Maximum number of job ads to retrieve from each board."
                )
            with col2:
                hours_old = st.number_input(
                    "Time Since Post (hours)",
                    min_value=24,
                    max_value=720,
                    key="hours_old",
                    help="Limit jobs to those posted within the last N hours (e.g. 168 = 7 days)."
                )
                results_wanted = st.number_input(
                    "Results Wanted",
                    min_value=1,
                    max_value=50,
                    key="results_wanted",
                    help="How many jobs you want to shortlist for CV matching."
                )
            with col3:
                country = st.selectbox(
                    "Country",
                    ["Australia", "USA", "Canada", "UK", "New Zealand", "Hong Kong", "Singapore"],
                    index=["Australia", "USA", "Canada", "UK", "New Zealand", "Hong Kong", "Singapore"].index(
                        user_config.get("COUNTRY", "Australia")),
                    key="country",
                    help="Primary country to search jobs in. Used by LinkedIn and other sources."
                )

            # Form submission
            if st.form_submit_button("💾 Save & Run Search"):
                if not user_email:
                    st.session_state.require_login = True
                    st.rerun()

                # Validate input: Require LinkedIn keywords, plus at least one other job source
                if not search_keywords:
                    st.error("Please enter LinkedIn/Seek search keywords.")
                    st.stop()
                if not all([search_term, google_term]):
                    st.error(
                        "Please fill at all job sources (Seek, Indeed/Glassdoor, or Google Custom Search).")
                    st.stop()

                if not cv_file and not user_config.get("BASE_CV_PATH"):
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
                        wp_site=config.wordpress_site,
                        wp_user=config.wordpress_username,
                        wp_app_password=config.wordpress_app_password
                    )

                    st.success(f"CV saved to: {cv_path}")

                # Build LinkedIn URL from search params
                linkedin_url = build_linkedin_search_url(
                    search_keywords,
                    location,
                    posted_hours=hours_old,
                    country=country,
                    max_jobs=max_jobs,
                    geoId_map=LINKEDIN_GEOID_MAP
                )

                seek_url = build_seek_url(
                    search_keywords,
                    seek_category,
                    location,
                    daterange=int(math.ceil(hours_old/24)),
                    salaryrange=seek_salaryrange,
                    salarytype=seek_salarytype,
                )

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

                    # Clean up flags & re-run
                    st.session_state.edit_config = False
                    st.session_state.pop("form_initialized", None)

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

                    st.rerun()
                else:
                    st.error("Failed to save configuration")

    # Always show job results table
    display_search_results(user_email=user_email)

"""
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
"""

def display_search_results(user_email):
    """Show results after search completes"""
    if not user_email:
        st.info("Log in to view your saved search results")
        return

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

    st.markdown("---")
    if st.button("🔄 Run a new search", key="new_search"):
        # flip into edit mode & clear the one‐time seed flag
        st.session_state.edit_config = True
        st.session_state.pop("form_initialized", None)
        # optionally clear old results so the UI isn’t confused:
        st.session_state.pop("search_results", None)
        st.rerun()