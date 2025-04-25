import streamlit as st
import pandas as pd
from data_store.airtable_manager import AirtableManager
from config.settings import Config
from datetime import datetime
from streamlit_extras.great_tables import great_tables
from great_tables import GT, style, loc

def show_history_ui(user_email: str):
    st.title("📂 Your CV Generation History")

    cfg = Config()
    historyAT = AirtableManager(
        cfg.AIRTABLE_API_KEY,
        cfg.AIRTABLE_BASE_ID,
        cfg.AIRTABLE_TABLE_ID_HISTORY
    )

    records = historyAT.get_history_by_user(user_email)
    if not records:
        st.info("No history found. Generate a CV first!")
        return

    # Transform records to DataFrame
    history_data = []
    for r in records:
        fields = r["fields"]
        cv_url = fields.get("cv_pdf_url", "")
        history_data.append({
            "Position": fields.get("job_title", "–"),
            "Generated Date": fields.get("created_at", ""),
            "CV": f'[Download CV]({cv_url})' if cv_url else "–"
        })

    df = pd.DataFrame(history_data)

    # Create and format table
    try:
        table = (
            GT(df)
            .tab_header(title="User Name", subtitle=f"{user_email}")
            .fmt_date(columns="Generated Date", date_style="iso")
            .fmt_markdown(columns="CV")
            .opt_vertical_padding(scale=2)
            .tab_options(
                container_width="100%",
                table_width="100%",
                heading_background_color="transparent",
                # heading_border_bottom_color="var(--secondary-background-color)",
                table_background_color="transparent",
                # table_border_top_color="var(--secondary-background-color)",
                # table_border_bottom_color="var(--secondary-background-color)",
                # table_body_border_bottom_color="var(--secondary-background-color)",
                # column_labels_border_bottom_color="var(--secondary-background-color)",
            )
            .tab_style(
                style=style.text(color="var(--text-color)", size="30", weight="bold"),
                locations=loc.title()
            )
            .tab_style(
                style=style.text(color="var(--primary-color)", size="20", weight="bold"),
                locations=loc.subtitle()
            )
            .tab_style(
                style=style.text(color="var(--text-color)", size="16"),
                locations=loc.column_header()
            )
            .tab_style(
                style=style.text(color="var(--text-color)", size="16"),
                locations=loc.body()
            )
        )

        great_tables(table, width="stretch")

    except Exception as e:
        st.error(f"Error displaying table: {str(e)}")
        # Fallback to original display
        for r in records:
            f = r["fields"]
            title = f.get("job_title", "–")
            created = f.get("created_at", "")
            cv_url = f.get("cv_pdf_url", "")

            c1, c2, c3 = st.columns([4, 1, 1])
            c1.markdown(f"<span style='color:var(--text-color);font-weight:bold'>{title}</span>",
                        unsafe_allow_html=True)
            c2.markdown(f"<span style='color:var(--text-color);'>{created}</span>", unsafe_allow_html=True)
            c3.markdown(
                f"<a style='color:var(--primary-color);' href='{cv_url}' target='_blank'>📥 Download</a>" if cv_url else "–",
                unsafe_allow_html=True
            )


