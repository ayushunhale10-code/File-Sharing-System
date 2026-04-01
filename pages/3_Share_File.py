"""
pages/3_Share_File.py
Share your files with other users or revoke their access.
"""

import streamlit as st
from utils.sidebar import render_sidebar
from backend.access_control import share_with_user, remove_access
from backend.file_handler import list_my_files

# ── PAGE CONFIG ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Share a File — ShareSphere",
    page_icon="🔗",
    layout="centered"
)

# ── SIDEBAR ───────────────────────────────────────────────────────────────────
render_sidebar()

user_id = st.session_state.user_id

# ── STYLES ────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ── HEADER ────────────────────────────────────────────────────────────────────
st.markdown("## 🔗 Share a File")
st.divider()

# ── FETCH USER'S FILES FOR DROPDOWN ──────────────────────────────────────────
with st.spinner("Loading your files..."):
    result = list_my_files(user_id=user_id, page=1, per_page=100)

files = result.get("files", []) if result["success"] else []

if not files:
    st.info("You have no files to share. Upload a file first.")
    st.stop()

file_options = {f["filename"]: f["_id"] for f in files}

# ── SHARE SECTION ─────────────────────────────────────────────────────────────
st.markdown("#### Grant Access")

with st.form("share_form"):
    selected_file = st.selectbox(
        "Select a file to share",
        options=list(file_options.keys())
    )
    target_email = st.text_input(
        "Recipient's email address",
        placeholder="colleague@example.com"
    )
    permission = st.selectbox(
        "Permission level",
        options=["read", "write", "delete", "share"],
        help=(
            "read — download only  |  "
            "write — download + re-upload  |  "
            "delete — includes read & write  |  "
            "share — can also share with others"
        )
    )
    share_submit = st.form_submit_button("Share File", type="primary", use_container_width=True)

if share_submit:
    if not target_email:
        st.error("Please enter the recipient's email.")
    else:
        file_id = file_options[selected_file]
        with st.spinner("Sharing..."):
            result = share_with_user(
                file_id=file_id,
                owner_id=user_id,
                target_email=target_email,
                permission=permission
            )

        if result["success"]:
            st.success(result["message"])
        else:
            st.error(result["error"])

st.divider()

# ── REVOKE SECTION ────────────────────────────────────────────────────────────
st.markdown("#### Revoke Access")

with st.form("revoke_form"):
    revoke_file = st.selectbox(
        "Select a file",
        options=list(file_options.keys()),
        key="revoke_file_select"
    )
    revoke_email = st.text_input(
        "Email of user to remove",
        placeholder="colleague@example.com"
    )
    revoke_submit = st.form_submit_button("Revoke Access", use_container_width=True)

if revoke_submit:
    if not revoke_email:
        st.error("Please enter the user's email.")
    else:
        file_id = file_options[revoke_file]
        with st.spinner("Revoking..."):
            result = remove_access(
                file_id=file_id,
                owner_id=user_id,
                target_email=revoke_email
            )

        if result["success"]:
            st.success(result["message"])
        else:
            st.error(result["error"])