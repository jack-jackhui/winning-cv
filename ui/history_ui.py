import streamlit as st
from data_store.airtable_manager import AirtableManager
from config.settings import Config

def show_history_ui(user_email: str):
    st.title("📂 Your CV Generation History")

    cfg       = Config()
    historyAT = AirtableManager(cfg.AIRTABLE_API_KEY,
                                cfg.AIRTABLE_BASE_ID,
                                cfg.AIRTABLE_TABLE_ID_HISTORY)

    records = historyAT.get_history_by_user(user_email)
    if not records:
        st.info("No history found. Generate a CV first!")
        return

    for r in records:
        f = r["fields"]
        title   = f.get("job_title", "–")
        created = f.get("created_at", "")
        cv_url  = f.get("cv_pdf_url", "")

        c1, c2, c3 = st.columns([4,1,1])
        c1.markdown(f"**{title}**")
        c2.markdown(created)
        c3.markdown(f"[Download CV]({cv_url})" if cv_url else "–")
