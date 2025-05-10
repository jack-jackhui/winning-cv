import streamlit as st

def render_sidebar() -> str:
    """Draw the left sidebar. Returns (user_email, mode)."""
    # Main content first
    st.sidebar.image("imgs/Series1-19.jpg", use_container_width=True)
    st.sidebar.markdown("---")


    # Email input
    # email = st.sidebar.text_input("Your email", "")
    # if not email:
    #    st.sidebar.warning("Enter your email to continue")
        # Add footer before stopping
    #    st.sidebar.markdown("---")
    #    st.sidebar.markdown("""
        # <div class="sidebar-footer" align="center">
        #    Powered by <strong>Winning CV AI</strong><br>
        #    Built with 🚀 by <a href="https://jackhui.com.au" target="_blank">@jackhui</a><br>
        #    <a href="https://jackhui.com.au" target="_blank">jackhui.com.au</a>
        # </div>
        # """, unsafe_allow_html=True)
        # st.stop()

    # Show logged-in user
    if st.user.is_logged_in:
        # safely grab name if it exists, else fall back to email
        user_email = st.user.email
        user_name = getattr(st.user, "name", None)
        if user_name:
            label = f"**Logged in as:** {user_name}  \n<{user_email}>"
        else:
            label = f"**Logged in as:** <{user_email}>"
        st.sidebar.markdown(label)
    else:
        st.sidebar.info("🔒 Not logged in")
    # User options
    st.sidebar.markdown("---")
    mode = st.sidebar.radio(
        "What would you like to do?",
        ["Generate New CV", "Run Job Search", "View History"]
    )

    # Add footer after user options
    st.sidebar.markdown("---")
    st.sidebar.markdown("""
    <style>
    .sidebar-footer {
        font-size: 0.8rem;
        color: #666;
        line-height: 1.4;
        padding: 10px 0;
    }
    .sidebar-footer a {
        color: #2e7d32 !important;
        text-decoration: none;
    }
    </style>
    <div class="sidebar-footer" align="center">
        Powered by <strong>Winning CV AI</strong><br>
        Built with 🗳️ by <a href="https://jackhui.com.au" target="_blank">@jackhui</a><br>        
    </div>
    """, unsafe_allow_html=True)

    return mode
