import streamlit as st
import re
from utils.utils import extract_text_from_file, create_pdf
from utils.logger import setup_logger
from utils.matcher import JobMatcher
from cv.cv_generator import CVGenerator
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize logger
logger = setup_logger(__name__)

def st_normal():
    """Create a centered container for normal-width content"""
    _, col, _ = st.columns([1, 4, 1])  # Adjust middle number for width (4 = wider than 2)
    return col

def main():
    st.set_page_config(layout="wide")

    # Add markdown css
    st.markdown("""
        <style>
            div[data-testid="stMarkdown"] {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
                line-height: 1.6;
            }
            h2 {
                color: #2e7d32;
                margin-top: 1.5rem !important;
                border-bottom: 2px solid #eee;
                padding-bottom: 0.3rem;
            }
            strong {
                color: #1a237e;
            }
        </style>
        """, unsafe_allow_html=True)

    with st_normal():
        st.title("Winning CV - Your AI CV Builder")

        # Add welcome section
        st.markdown("""
        ## Welcome to CV Helper! 
        **I'll help you create a job-winning resume by:**
        - 🔍 Analyzing your target job description
        - ✨ Highlighting your most relevant qualifications
        - 📈 Optimizing for applicant tracking systems (ATS)
        - 🎯 Tailoring content to specific industries
    
        Let's get started by understanding your background and career goals!
        """)

    cv_generator = CVGenerator()

    # Initialize session state
    if 'modified_cv' not in st.session_state:
        st.session_state.modified_cv = None

    # Step 1: Job Description Input
    with st_normal():
        with st.expander("1. Provide Job Description", expanded=True):
            job_desc = st.text_area("Paste job description here", height=200)
            job_file = st.file_uploader("Or upload job description (PDF/DOCX/TXT)",
                                        type=["pdf", "docx", "txt"])

    # Step 2: CV and Instructions
    with st_normal():
        with st.expander("2. Upload Your CV", expanded=True):
            cv_file = st.file_uploader("Upload your CV (PDF/DOCX/TXT)",
                                       type=["pdf", "docx", "txt"])
            instructions = st.text_area("Additional customization instructions",
                                        placeholder="e.g. Emphasize Python skills, reduce focus on retail experience")

    # Process inputs
    if job_file:
        job_desc = extract_text_from_file(job_file)

    original_cv = ""
    if cv_file:
        original_cv = extract_text_from_file(cv_file)
        with st_normal():

            # Debug preview
            # with st.expander("Debug: View Extracted Content", expanded=False):
            #    st.code(original_cv[:2000] + "...")  # Show first 2000 characters

            # Validate extracted content
            if len(original_cv.strip()) < 50:  # Minimum 50 characters
                st.error("""
            Extraction failed. Common fixes:
            1. For DOCX: Save as 'Word 97-2003 Document (.doc)' and reupload
            2. For PDF: Use text-based PDFs, not scanned documents
            3. Avoid password protection
            """)
                st.stop()

    # Step 3: Generate Custom CV
    with st_normal():
        if st.button("Generate Custom CV"):
            if not cv_file:
                st.warning("Please upload your CV first")
            elif not job_desc:
                st.warning("Please provide a job description")
            else:
                if len(original_cv.strip()) < 50:
                    st.error("The uploaded CV appears empty or could not be parsed")
                    st.stop()

                with st.spinner("Customizing your CV..."):
                    try:
                        st.session_state.modified_cv = cv_generator.generate_cv(
                            original_cv, job_desc, instructions
                        )
                    except Exception as e:
                        st.error(str(e))

    # Step 4: Review and Preview
    if st.session_state.modified_cv:
        st.subheader("Live Preview")
        with st.expander("3. Review & Finalize", expanded=True):
            cleaned_preview = clean_llm_output(st.session_state.modified_cv)
            # Create tabs for different views
            tab1, tab2 = st.tabs(["Formatted Preview", "Raw Text"])

            with tab1:
                st.markdown(cleaned_preview)

            with tab2:
                st.code(cleaned_preview)

        with st_normal():
            st.subheader("Request Modifications")
            modification_instructions = st.text_area(
                "Enter your modification requests:",
                placeholder="e.g. 'Add more metrics to project section', 'Emphasize leadership experience'",
                height=100
            )
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Apply Modifications"):
                    if modification_instructions:
                        with st.spinner("Updating CV..."):
                            try:
                                # Combine original instructions with new modifications
                                updated_instructions = f"{instructions}. {modification_instructions}"

                                st.session_state.modified_cv = cv_generator.generate_cv(
                                    st.session_state.modified_cv,  # Use current CV as base
                                    job_desc,
                                    updated_instructions
                                )
                                st.rerun()
                            except Exception as e:
                                st.error(str(e))
                    else:
                        st.warning("Please enter modification instructions")
            with col2:
                if st.button("Generate Final PDF"):
                    with st.spinner("Creating PDF..."):
                        cleaned_content = clean_llm_output(st.session_state.modified_cv)
                        if cleaned_content:
                            pdf_path = create_pdf(cleaned_content)
                            if pdf_path:
                                with open(pdf_path, "rb") as f:
                                    st.download_button(
                                        label="Download CV",
                                        data=f,
                                        file_name="customised_cv/customized_cv.pdf",
                                        mime="application/octet-stream",
                                        key="download_pdf"
                                    )
                            else:
                                st.error("Failed to generate PDF")
                        else:
                            st.warning("No content to generate PDF from")

# Clean the output before preview
def clean_llm_output(content):
    # Remove any leading non-markdown text
    cleaned = re.sub(r'^.*?(?=# )', '', content, flags=re.DOTALL | re.IGNORECASE)

    # Fix markdown syntax
    cleaned = re.sub(r'-\s*\*\*([A-Za-z]+):\*\*\s*', r'**\1:** ', cleaned)  # Fix contact info formatting
    cleaned = re.sub(r'\*{2}([A-Za-z ]+?)\*{2}', r'**\1**', cleaned)  # Fix bold formatting
    cleaned = re.sub(r'##\s+([A-Z& ]+?)\*', r'## \1', cleaned)  # Remove asterisks in headers

    # Remove code blocks if any
    cleaned = re.sub(r'```markdown', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'```', '', cleaned)

    # Standardize line breaks
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)

    return cleaned.strip()

if __name__ == "__main__":
    main()