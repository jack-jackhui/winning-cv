import streamlit as st
from ui.sidebar     import render_sidebar
from ui.generate_ui import show_generate_ui
from ui.history_ui  import show_history_ui

def main():
    st.set_page_config(
        page_title="Winning CV - Powered by AI",
        page_icon="⚡",
        menu_items={
            "About": "https://jackhui.com.au"
        }
    )

    user_email, mode = render_sidebar()
    if mode == "Generate New CV":
        show_generate_ui(user_email)
    else:
        show_history_ui(user_email)

if __name__ == "__main__":
    main()
