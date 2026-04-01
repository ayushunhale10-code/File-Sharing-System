"""
pages/6_Admin_Backup.py
Admin-only backup and recovery management.
Trigger mongodump backups and view backup history.
"""

import streamlit as st
from utils.sidebar import render_sidebar
from backend.backup import run_backup, latest_backup_status, recent_failures

# ── PAGE CONFIG ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Backup & Recovery — ShareSphere",
    page_icon="🗄️",
    layout="wide"
)

# ── SIDEBAR + ADMIN GUARD ─────────────────────────────────────────────────────
role = render_sidebar()

if role != "admin":
    st.error("⛔ Access denied. This page is for admins only.")
    st.stop()

# ── STYLES ────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .status-completed { color: #16a34a; font-weight: 600; }
    .status-failed    { color: #dc2626; font-weight: 600; }
    .status-running   { color: #d97706; font-weight: 600; }
    .info-card {
        background: #f9fafb;
        border: 1px solid #e5e7eb;
        border-radius: 10px;
        padding: 1.1rem 1.5rem;
        margin-bottom: 1rem;
    }
    footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

user_id = st.session_state.user_id

# ── HEADER ────────────────────────────────────────────────────────────────────
st.markdown("## 🗄️ Backup & Recovery")
st.caption("Trigger database backups and view backup history. Uses mongodump under the hood.")
st.divider()

# ── LATEST BACKUP STATUS ──────────────────────────────────────────────────────
st.markdown("#### Latest Backup")

with st.spinner("Fetching backup status..."):
    latest = latest_backup_status()

backup = latest.get("backup")

if not backup:
    st.info("No backups have been run yet.")
else:
    status     = backup.get("status", "—")
    btype      = backup.get("backup_type", "—")
    started    = backup.get("started_at")
    completed  = backup.get("completed_at")
    size_bytes = backup.get("size_bytes", 0)
    file_count = backup.get("file_count", 0)
    out_path   = backup.get("output_path", "—")
    duration   = backup.get("duration_secs", 0)
    error_msg  = backup.get("error_message")

    started_str   = started.strftime("%d %b %Y, %H:%M:%S") if started else "—"
    completed_str = completed.strftime("%d %b %Y, %H:%M:%S") if completed else "—"

    size_str = (
        f"{size_bytes / 1_073_741_824:.2f} GB" if size_bytes >= 1_073_741_824
        else f"{size_bytes / 1_048_576:.1f} MB" if size_bytes >= 1_048_576
        else f"{size_bytes / 1024:.1f} KB"
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Status",    status.upper())
    c2.metric("Type",      btype.capitalize())
    c3.metric("Size",      size_str)
    c4.metric("Duration",  f"{duration}s")

    st.markdown(f"""
    <div class='info-card'>
        <div style='font-size:0.85rem; color:#374151;'>
            <strong>Output path:</strong> <code>{out_path}</code><br>
            <strong>Collections backed up:</strong> {file_count}<br>
            <strong>Started:</strong> {started_str} &nbsp;·&nbsp; <strong>Completed:</strong> {completed_str}
        </div>
        {"<div style='color:#dc2626; margin-top:0.5rem;'><strong>Error:</strong> " + error_msg + "</div>" if error_msg else ""}
    </div>
    """, unsafe_allow_html=True)

st.divider()

# ── RUN BACKUP ────────────────────────────────────────────────────────────────
st.markdown("#### Run New Backup")
st.warning("⚠️ This will run mongodump on the live database. It may take several minutes for large datasets.")

col_type, col_btn = st.columns([2, 1])

with col_type:
    backup_type = st.selectbox(
        "Backup type",
        options=["full", "incremental", "differential"],
        help="Full: entire DB. Incremental/Differential: changed data only (requires oplog config)."
    )

with col_btn:
    st.markdown("<div style='margin-top:1.85rem;'>", unsafe_allow_html=True)
    run_btn = st.button("▶️  Run Backup Now", type="primary", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

if run_btn:
    with st.spinner(f"Running {backup_type} backup... this may take a few minutes."):
        result = run_backup(admin_user_id=user_id, backup_type=backup_type)

    if result["success"]:
        size_b = result.get("size_bytes", 0)
        size_s = (
            f"{size_b/1_048_576:.1f} MB" if size_b >= 1_048_576
            else f"{size_b/1024:.1f} KB"
        )
        st.success(
            f"✅ Backup completed successfully!  "
            f"Size: **{size_s}**  ·  "
            f"Collections: **{result.get('file_count', 0)}**  ·  "
            f"Path: `{result.get('output_path')}`"
        )
        st.rerun()
    else:
        st.error(f"Backup failed: {result['error']}")

st.divider()

# ── RECENT FAILURES ────────────────────────────────────────────────────────────
st.markdown("#### Recent Failures")

days_back = st.selectbox("Show failures from last", [3, 7, 14, 30], index=1,
                          format_func=lambda x: f"{x} days")

with st.spinner("Fetching failure history..."):
    fail_result = recent_failures(days=days_back)

failures = fail_result.get("failures", []) if fail_result["success"] else []

if not failures:
    st.success(f"No backup failures in the last {days_back} days.")
else:
    st.caption(f"{len(failures)} failure(s) found")
    st.markdown("")

    for f in failures:
        started   = f.get("started_at")
        error_msg = f.get("error_message", "No error message recorded.")
        btype     = f.get("backup_type", "—")
        started_s = started.strftime("%d %b %Y, %H:%M") if started else "—"

        st.markdown(f"""
        <div class='info-card' style='border-left: 4px solid #dc2626;'>
            <div style='font-size:0.85rem; color:#374151;'>
                <strong>Type:</strong> {btype.capitalize()} &nbsp;·&nbsp;
                <strong>Started:</strong> {started_s}
            </div>
            <div style='color:#dc2626; font-size:0.83rem; margin-top:0.4rem;'>
                <strong>Error:</strong> {error_msg}
            </div>
        </div>
        """, unsafe_allow_html=True)

# ── RESTORE INSTRUCTIONS ──────────────────────────────────────────────────────
st.divider()
st.markdown("#### 🔁 Restore Instructions")
st.info(
    "To restore from a backup, run the following command on your server terminal. "
    "Replace the path with your backup folder."
)
st.code(
    "mongorestore \\\n"
    "  --uri \"mongodb://sharesphere_app:sharesphere@123@localhost:27017/sharesphere_db\" \\\n"
    "  --db sharesphere_db \\\n"
    "  --gzip \\\n"
    "  --drop \\\n"
    "  /backups/sharesphere/YYYY-MM-DD_HH-MM/sharesphere_db/",
    language="bash"
)
st.caption("--drop drops each collection before restoring. Remove it if you want to merge instead of replace.")