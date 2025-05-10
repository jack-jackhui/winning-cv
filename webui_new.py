import streamlit as st
from ui.sidebar     import render_sidebar
from ui.generate_ui import show_generate_ui
from ui.history_ui  import show_history_ui
from data_store.airtable_manager import AirtableManager
from config.settings import Config
from ui.job_search_ui import show_job_search_ui, display_search_results
from utils.logger import setup_logger
import logging

# Add login dialog decorator
@st.dialog("Login Required", width="large")
def login_dialog():
    st.write("Please log in with your Google or Microsoft account to continue.")
    col1, col2 = st.columns(2, gap="small")
    with col1:
        icon_col, btn_col = st.columns([1, 5], gap="small")
        icon_col.image("imgs/google.png", width=40)
        if btn_col.button("Log in with Google", key="login_google"):
            st.login("google")
            st.rerun()
    with col2:
        icon_col, btn_col = st.columns([1, 5], gap="small")
        icon_col.image("imgs/microsoft.png", width=40)
        if btn_col.button("Log in with Microsoft", key="login_ms"):
            st.login("microsoft")
            st.rerun()

def main():
    # Initialize logging FIRST THING
    setup_logger(
        log_file="logs/web_app.log",  # Central log file path
        level=logging.DEBUG
    )
    st.set_page_config(
        page_title="Winning CV - Powered by AI",
        page_icon="⚡",
        layout="wide",
        menu_items={
            "About": "https://jackhui.com.au"
        }
    )

    # Always show sidebar
    mode = render_sidebar()

    # Add custom CSS for footer
    st.markdown("""
            <style>
            footer {
                position: fixed;
                bottom: 0;
                left: 0;
                right: 0;
                background: var(--background-color);
                color: var(--text-color);
                padding: 1rem;
                text-align: center;
                border-top: 1px solid var(--secondary-background-color);
                z-index: 1000;
            }
            footer a {
                color: var(--text-color) !important;
                text-decoration: none;
                margin: 0 0.5rem;
            }
        </style>
        """, unsafe_allow_html=True)

    # Initialize Airtable manager
    airtable = AirtableManager(
        Config.AIRTABLE_API_KEY,
        Config.AIRTABLE_BASE_ID,
        Config.AIRTABLE_TABLE_ID
    )

    # Check for protected actions
    if not st.user.is_logged_in:
        if mode in ["Generate New CV", "Run Job Search", "History"]:
            login_dialog()
            st.stop()  # Prevent further execution until logged in
        elif mode == "Run Job Search" and "search_results" in st.session_state:
            login_dialog()
            st.stop()

    # Show logout button only when logged in
    if st.user.is_logged_in:
        with st.sidebar:
            st.button("🔓 Log out", on_click=st.logout)

    user_email = st.user.email if st.user.is_logged_in else None
    # never assume name exists
    user_name = getattr(st.user, "name", None)
    if mode == "Generate New CV":
        show_generate_ui(user_email)
    elif mode == "Run Job Search":
        if "search_results" in st.session_state:
            display_search_results(user_email)
        else:
            show_job_search_ui(user_email, airtable)
    else:
        show_history_ui(user_email)

    # Add footer content
    st.markdown("""
        <footer>
            ⭐ Winning CV Powered by AI | 
            <a href="https://jackhui.com.au/" target="_blank">About</a> |
            <a href="https://jackhui.com.au/" target="_blank">Contact</a>
        </footer>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
