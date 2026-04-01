"""
utils/sidebar.py
Renders the shared sidebar navigation and handles logout.
Import and call render_sidebar() at the top of every page.
"""

import streamlit as st
from backend.auth import logout


def require_login():
    """Redirect to login if not authenticated. Call at top of every page."""
    if not st.session_state.get("logged_in"):
        st.switch_page("app.py")


def render_sidebar():
    """
    Renders the navigation sidebar.
    Returns the current user's role (for conditional rendering in pages).
    """
    require_login()

    role     = st.session_state.get("role", "user")
    username = st.session_state.get("username", "User")

    with st.sidebar:
        st.markdown(f"### 🔷 ShareSphere")
        st.markdown(f"Signed in as **{username}**")
        st.caption(f"Role: `{role}`")
        st.divider()

        # ── Navigation ────────────────────────────────────────────────────────
        st.markdown("**Files**")
        st.page_link("pages/1_My_Files.py",        label="📁  My Files")
        st.page_link("pages/2_Shared_With_Me.py",  label="📨  Shared With Me")
        st.page_link("pages/3_Share_File.py",       label="🔗  Share a File")

        st.markdown("**Account**")
        st.page_link("pages/4_My_Activity.py",     label="📋  My Activity")

        # Admin-only pages
        if role == "admin":
            st.markdown("**Admin**")
            st.page_link("pages/5_Admin_Monitoring.py", label="📊  Monitoring")
            st.page_link("pages/6_Admin_Backup.py",     label="🗄️  Backup & Recovery")

        st.divider()

        # ── Logout ────────────────────────────────────────────────────────────
        if st.button("Sign Out", use_container_width=True):
            logout(user_id=st.session_state.user_id)
            for key in ["logged_in", "user_id", "username", "role"]:
                st.session_state[key] = None
            st.switch_page("app.py")

    return role