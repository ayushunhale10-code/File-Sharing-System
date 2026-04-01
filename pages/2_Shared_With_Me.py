"""
pages/2_Shared_With_Me.py
View and download files that other users have shared with you.
"""

import streamlit as st
from utils.sidebar import render_sidebar
from backend.access_control import get_shared_with_me
from backend.file_handler import download_file

# ── PAGE CONFIG ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Shared With Me — ShareSphere",
    page_icon="📨",
    layout="wide"
)

# ── SIDEBAR ───────────────────────────────────────────────────────────────────
render_sidebar()

user_id = st.session_state.user_id

# ── STYLES ────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .file-card {
        background: #f9fafb;
        border: 1px solid #e5e7eb;
        border-radius: 10px;
        padding: 1rem 1.25rem;
        margin-bottom: 0.6rem;
    }
    .file-name { font-weight: 600; font-size: 0.95rem; color: #111827; }
    .file-meta { font-size: 0.78rem; color: #6b7280; margin-top: 0.15rem; }
    footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ── HEADER ────────────────────────────────────────────────────────────────────
st.markdown("## 📨 Shared With Me")
st.caption("Files other users have shared with you.")
st.divider()

# ── FETCH FILES ───────────────────────────────────────────────────────────────
with st.spinner("Loading shared files..."):
    result = get_shared_with_me(user_id=user_id)

files = result.get("files", []) if result["success"] else []

if not files:
    st.info("No files have been shared with you yet.")
else:
    st.caption(f"{len(files)} file(s) shared with you")
    st.markdown("")

    for f in files:
        file_id  = f["_id"]
        fname    = f.get("filename", "Untitled")
        fsize    = f.get("file_size", 0)
        mime     = f.get("mime_type", "")
        owner_id = f.get("owner_id", "")

        size_str = (
            f"{fsize / 1_048_576:.1f} MB" if fsize >= 1_048_576
            else f"{fsize / 1024:.1f} KB" if fsize >= 1024
            else f"{fsize} B"
        )

        st.markdown(f"""
        <div class='file-card'>
            <div class='file-name'>{fname}</div>
            <div class='file-meta'>{size_str} &nbsp;·&nbsp; {mime}</div>
        </div>
        """, unsafe_allow_html=True)

        col_dl, _ = st.columns([1, 7])

        with col_dl:
            if st.button("⬇ Download", key=f"dl_{file_id}"):
                with st.spinner("Preparing download..."):
                    dl = download_file(file_id=file_id, requesting_user_id=user_id)

                if dl["success"]:
                    st.download_button(
                        label="Save file",
                        data=dl["data"],
                        file_name=dl["filename"],
                        mime=dl["mime_type"],
                        key=f"save_{file_id}"
                    )
                else:
                    st.error(dl["error"])