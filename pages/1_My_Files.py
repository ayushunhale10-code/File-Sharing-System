"""
pages/1_My_Files.py
Upload, list, download, delete, and search your files.
"""

import streamlit as st
import math
from utils.sidebar import render_sidebar
from backend.file_handler import (
    upload_file,
    list_my_files,
    download_file,
    delete_file,
    search,
)

# ── PAGE CONFIG ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="My Files — ShareSphere",
    page_icon="📁",
    layout="wide"
)

# ── SIDEBAR ───────────────────────────────────────────────────────────────────
render_sidebar()

user_id  = st.session_state.user_id
username = st.session_state.username

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
    .file-name  { font-weight: 600; font-size: 0.95rem; color: #111827; }
    .file-meta  { font-size: 0.78rem; color: #6b7280; margin-top: 0.15rem; }
    .badge {
        display: inline-block;
        background: #eff6ff;
        color: #3b82f6;
        border-radius: 999px;
        padding: 0.1rem 0.55rem;
        font-size: 0.72rem;
        font-weight: 600;
        margin-right: 0.25rem;
    }
    footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ── HEADER ────────────────────────────────────────────────────────────────────
st.markdown("## 📁 My Files")
st.divider()

# ── UPLOAD SECTION ────────────────────────────────────────────────────────────
with st.expander("⬆️  Upload a File", expanded=False):
    uploaded = st.file_uploader(
        "Choose a file",
        help="Supports any file type."
    )

    col1, col2 = st.columns(2)
    with col1:
        tags_input  = st.text_input("Tags (comma-separated)", placeholder="report, 2024, finance")
    with col2:
        is_public   = st.checkbox("Make this file public (anyone with link can access)")

    description = st.text_input("Description (optional)", placeholder="Brief description of the file")

    if st.button("Upload", type="primary", disabled=uploaded is None):
        tags = [t.strip() for t in tags_input.split(",") if t.strip()] if tags_input else []

        with st.spinner("Uploading..."):
            result = upload_file(
                user_id=user_id,
                file_bytes=uploaded.read(),
                filename=uploaded.name,
                mime_type=uploaded.type or "application/octet-stream",
                tags=tags,
                description=description,
                is_public=is_public
            )

        if result["success"]:
            st.success(f"✅ '{uploaded.name}' uploaded successfully.")
            st.rerun()
        else:
            st.error(result["error"])

st.markdown("")

# ── SEARCH BAR ────────────────────────────────────────────────────────────────
search_query = st.text_input(
    "🔍 Search files",
    placeholder="Search by filename, description, or tag...",
    label_visibility="collapsed"
)

# ── FILE LIST ─────────────────────────────────────────────────────────────────
PER_PAGE = 10

if search_query.strip():
    # Search mode
    with st.spinner("Searching..."):
        result = search(query=search_query, user_id=user_id, limit=50)

    files = result.get("results", []) if result["success"] else []
    st.caption(f"{len(files)} result(s) for **\"{search_query}\"**")
else:
    # Normal paginated list
    page = st.session_state.get("files_page", 1)

    with st.spinner("Loading files..."):
        result = list_my_files(user_id=user_id, page=page, per_page=PER_PAGE)

    files = result.get("files", []) if result["success"] else []

if not files:
    st.info("No files found. Upload something to get started." if not search_query else "No files match your search.")
else:
    for f in files:
        file_id   = f["_id"]
        fname     = f.get("filename", "Untitled")
        fsize     = f.get("file_size", 0)
        mime      = f.get("mime_type", "")
        downloads = f.get("download_count", 0)
        tags      = f.get("tags", [])
        public    = f.get("is_public", False)

        size_str = (
            f"{fsize / 1_048_576:.1f} MB" if fsize >= 1_048_576
            else f"{fsize / 1024:.1f} KB" if fsize >= 1024
            else f"{fsize} B"
        )

        tag_html = "".join(f"<span class='badge'>{t}</span>" for t in tags)
        pub_html = "<span class='badge' style='background:#f0fdf4;color:#16a34a;'>public</span>" if public else ""

        st.markdown(f"""
        <div class='file-card'>
            <div class='file-name'>{fname}</div>
            <div class='file-meta'>{size_str} &nbsp;·&nbsp; {mime} &nbsp;·&nbsp; {downloads} downloads</div>
            <div style='margin-top:0.4rem;'>{pub_html}{tag_html}</div>
        </div>
        """, unsafe_allow_html=True)

        col_dl, col_del, _ = st.columns([1, 1, 6])

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

        with col_del:
            if st.button("🗑 Delete", key=f"del_{file_id}"):
                with st.spinner("Deleting..."):
                    dr = delete_file(file_id=file_id, owner_id=user_id)

                if dr["success"]:
                    st.success("File deleted.")
                    st.rerun()
                else:
                    st.error(dr["error"])

    # Pagination controls (only in list mode, not search mode)
    if not search_query.strip():
        st.divider()
        col_prev, col_info, col_next = st.columns([1, 2, 1])

        with col_prev:
            if page > 1:
                if st.button("← Previous"):
                    st.session_state.files_page = page - 1
                    st.rerun()

        with col_info:
            st.caption(f"Page {page}")

        with col_next:
            if len(files) == PER_PAGE:
                if st.button("Next →"):
                    st.session_state.files_page = page + 1
                    st.rerun()