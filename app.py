"""
app.py — ShareSphere entry point
Handles login and registration. All other pages are in /pages/.
Run with: streamlit run app.py
"""

import streamlit as st
from backend.auth import login, register

# ── PAGE CONFIG ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="ShareSphere",
    page_icon="🔷",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# ── GLOBAL STYLES ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* Hide sidebar on login page */
    [data-testid="stSidebar"] { display: none; }

    /* Clean card look */
    .auth-card {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 12px;
        padding: 2rem 2.5rem;
        margin-top: 2rem;
    }

    /* Muted label above form */
    .page-label {
        font-size: 0.78rem;
        font-weight: 600;
        letter-spacing: 0.08em;
        color: #9ca3af;
        text-transform: uppercase;
        margin-bottom: 0.25rem;
    }

    /* Hide Streamlit default top padding */
    .block-container { padding-top: 3rem !important; }

    /* Remove "Made with Streamlit" footer */
    footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ── SESSION STATE INIT ────────────────────────────────────────────────────────
for key in ["user_id", "username", "role", "logged_in"]:
    if key not in st.session_state:
        st.session_state[key] = None

# ── REDIRECT IF ALREADY LOGGED IN ─────────────────────────────────────────────
if st.session_state.logged_in:
    st.switch_page("pages/1_My_Files.py")

# ── HEADER ────────────────────────────────────────────────────────────────────
st.markdown("## 🔷 ShareSphere")
st.markdown("A secure file sharing system.")
st.divider()

# ── TABS: LOGIN / REGISTER ────────────────────────────────────────────────────
tab_login, tab_register = st.tabs(["Sign In", "Create Account"])

# ── LOGIN TAB ─────────────────────────────────────────────────────────────────
with tab_login:
    st.markdown("<div class='page-label'>Sign in to your account</div>", unsafe_allow_html=True)

    with st.form("login_form"):
        email    = st.text_input("Email", placeholder="you@example.com")
        password = st.text_input("Password", type="password", placeholder="••••••••")
        submit   = st.form_submit_button("Sign In", use_container_width=True, type="primary")

    if submit:
        if not email or not password:
            st.error("Please fill in all fields.")
        else:
            with st.spinner("Signing in..."):
                result = login(email=email, password=password)

            if result["success"]:
                st.session_state.logged_in = True
                st.session_state.user_id   = result["user"]["user_id"]
                st.session_state.username  = result["user"]["username"]
                st.session_state.role      = result["user"]["role"]
                st.success(f"Welcome back, {result['user']['username']}!")
                st.switch_page("pages/1_My_Files.py")
            else:
                st.error(result["error"])

# ── REGISTER TAB ──────────────────────────────────────────────────────────────
with tab_register:
    st.markdown("<div class='page-label'>Create a new account</div>", unsafe_allow_html=True)

    with st.form("register_form"):
        reg_username = st.text_input("Username", placeholder="somesh_dev")
        reg_email    = st.text_input("Email", placeholder="you@example.com")
        reg_password = st.text_input("Password", type="password", placeholder="Min. 6 characters")
        reg_confirm  = st.text_input("Confirm Password", type="password", placeholder="Re-enter password")
        reg_submit   = st.form_submit_button("Create Account", use_container_width=True, type="primary")

    if reg_submit:
        if not reg_username or not reg_email or not reg_password or not reg_confirm:
            st.error("All fields are required.")
        elif len(reg_password) < 6:
            st.error("Password must be at least 6 characters.")
        elif reg_password != reg_confirm:
            st.error("Passwords do not match.")
        else:
            with st.spinner("Creating account..."):
                result = register(username=reg_username, email=reg_email, password=reg_password)

            if result["success"]:
                st.success("Account created! Please sign in.")
            else:
                st.error(result["error"])