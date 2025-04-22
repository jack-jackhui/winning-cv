# ui/generate_ui.py
import streamlit as st
import re
from datetime import datetime
from utils.utils import extract_text_from_file, create_pdf
from cv.cv_generator import CVGenerator
from data_store.airtable_manager import AirtableManager
from config.settings import Config
from ui.helpers import upload_pdf_to_wordpress, extract_title_from_jd, extract_contact_info

def show_generate_ui(user_email: str):
    st.title("🔍 Generate a Tailored CV")
    # 1) Job Description input
    st.subheader("Job Description")
    job_desc = st.text_area("Paste job description here", height=200)
    jd_file = st.file_uploader("…or upload job description (PDF/DOCX/TXT)",
                               type=["pdf", "docx", "txt"])
    if jd_file:
        job_desc = extract_text_from_file(jd_file)
    # 2) CV upload & instructions
    st.subheader("Your Current CV & Instructions")
    cv_file = st.file_uploader("Upload your CV (PDF/DOCX/TXT)",
                               type=["pdf", "docx", "txt"])
    instructions = st.text_area("Any special instructions?",
                                placeholder="e.g. Emphasize Python skills…")
    # Validate presence of both JD and CV
    if st.button("Generate CV"):
        if not job_desc:
            st.warning("Please provide a job description.")
            return
        if not cv_file:
            st.warning("Please upload your current CV.")
            return
        # Extract text from the CV
        orig_cv = extract_text_from_file(cv_file)
        if len(orig_cv.strip()) < 30:
            st.error("Could not parse your CV. Try another format.")
            return

        # 3) Pull contact info from original CV (if any)
        # contact = extract_contact_info(orig_cv)

        # 4) Call your LLM to get the tailored markdown
        with st.spinner("Customizing your CV…"):
            try:
                raw_md = CVGenerator().generate_cv(orig_cv, job_desc, instructions)
            except Exception as e:
                st.error(f"CV generation failed: {e}")
                return
        """
        # 5) Clean & normalize that markdown
        # md = clean_llm_output(raw_md)
        # md = strip_llm_contact_block(md, contact)
        # 6) Build a contact block only if we found at least the name
        contact_lines = []
        if contact.get("name"):
            contact_lines.append(f"# {contact['name']}")
        if contact.get("address"):
            contact_lines.append(f"**Address:** {contact['address']}")
        if contact.get("phone"):
            contact_lines.append(f"**Phone:** {contact['phone']}")
        email_to_use = contact.get("email", user_email)
        contact_lines.append(f"**Email:** {email_to_use}")
        if contact.get("github"):
            contact_lines.append(f"**GitHub:** {contact['github']}")

        # Join with double newlines to force Markdown separation
        contact_block = "\n\n".join(contact_lines) + "\n\n"

        # 7) Combine contact + body
        # final_md = contact_block + md
        # Remove duplicate contact info lines (e.g. "Email: ...")
        # final_md = re.sub(r'\n?Email:[^\n]+\n?', '\n', final_md, flags=re.IGNORECASE)
        """
        # 8) Show a live preview
        st.subheader("Live Preview")
        #st.markdown(final_md)
        st.markdown(raw_md)

        # 9) Render to PDF
        pdf_path = create_pdf(raw_md)
        if not pdf_path:
            st.error("Failed to generate PDF.")
            return

        # 10) Compute a filename: YYYY‑MM‑DD_<job‑title>.pdf
        #    Take the first line of the job desc, slugify lightly
        job_title = extract_title_from_jd(job_desc)
        safe_title = re.sub(r'[^\w]+', '_', job_title)[:30].strip('_')
        today = datetime.now().strftime("%Y-%m-%d")
        download_name = f"{today}_{safe_title}.pdf"

        # 11.a) Download button
        with open(pdf_path, "rb") as f:
            st.download_button(
                label="📥 Download Your Tailored CV",
                data=f,
                file_name=download_name,
                mime="application/pdf"
            )

        # 11.b) upload to web server
        try:
            cv_pdf_url = upload_pdf_to_wordpress(
                file_path=pdf_path,
                filename=download_name,
                wp_site=Config.WORDPRESS_SITE,
                wp_user=Config.WORDPRESS_USERNAME,
                wp_app_password=Config.WORDPRESS_APP_PASSWORD
            )
        except Exception as e:
            st.error(f"Failed to push PDF to WordPress: {e}")
            return

        # 12) Persist into History table
        cfg = Config()
        history_at = AirtableManager(
            cfg.AIRTABLE_API_KEY,
            cfg.AIRTABLE_BASE_ID,
            cfg.AIRTABLE_TABLE_ID_HISTORY
        )
        history_data = {
            "user_email": user_email,
            "job_title": job_title,
            "job_description": job_desc,
            "instructions": instructions,
            "cv_markdown": raw_md,
            "cv_pdf_url": cv_pdf_url,
        }
        history_at.create_history_record(history_data)