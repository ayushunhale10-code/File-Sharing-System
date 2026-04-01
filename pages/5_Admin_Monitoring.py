"""
pages/5_Admin_Monitoring.py
Admin-only monitoring dashboard: event summary, storage usage,
top downloaded files, and suspicious login detection.
"""

import streamlit as st
from utils.sidebar import render_sidebar
from backend.activity_logger import (
    event_summary,
    storage_report,
    top_downloads,
    suspicious_logins,
)

# ── PAGE CONFIG ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Monitoring — ShareSphere",
    page_icon="📊",
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
    .metric-card {
        background: #f9fafb;
        border: 1px solid #e5e7eb;
        border-radius: 10px;
        padding: 1.1rem 1.25rem;
        text-align: center;
    }
    .metric-value { font-size: 1.8rem; font-weight: 700; color: #111827; }
    .metric-label { font-size: 0.78rem; color: #6b7280; margin-top: 0.15rem; }
    .warn-row { background: #fff7ed; border-radius: 8px; padding: 0.5rem 0.75rem; margin-bottom: 0.4rem; }
    footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ── HEADER ────────────────────────────────────────────────────────────────────
st.markdown("## 📊 Monitoring Dashboard")
st.divider()

# ── CONTROLS ─────────────────────────────────────────────────────────────────
col_ctrl1, col_ctrl2 = st.columns([1, 3])
with col_ctrl1:
    days = st.selectbox("Time window", [7, 14, 30, 90], index=2, format_func=lambda x: f"Last {x} days")

if st.button("🔄 Refresh", type="secondary"):
    st.rerun()

st.markdown("")

# ── FETCH ALL DATA ────────────────────────────────────────────────────────────
with st.spinner("Loading monitoring data..."):
    ev_result   = event_summary(days=days)
    sr_result   = storage_report()
    td_result   = top_downloads(limit=10)
    sl_result   = suspicious_logins(threshold=5, window_minutes=15)

events  = ev_result.get("summary", [])   if ev_result["success"]  else []
storage = sr_result.get("report", [])    if sr_result["success"]  else []
top_dl  = td_result.get("files", [])     if td_result["success"]  else []
sus     = sl_result.get("suspicious", []) if sl_result["success"] else []

# ── ROW 1: SUMMARY METRICS ───────────────────────────────────────────────────
st.markdown("#### Event Summary")

total_events = sum(e["count"] for e in events)
event_map    = {e["event"]: e["count"] for e in events}

m1, m2, m3, m4, m5 = st.columns(5)
for col, label, key in [
    (m1, "Total Events",  None),
    (m2, "Uploads",       "upload"),
    (m3, "Downloads",     "download"),
    (m4, "Shares",        "share"),
    (m5, "Logins",        "login"),
]:
    val = total_events if key is None else event_map.get(key, 0)
    col.markdown(f"""
    <div class='metric-card'>
        <div class='metric-value'>{val}</div>
        <div class='metric-label'>{label}</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("")

# ── ROW 2: TOP DOWNLOADS + SUSPICIOUS LOGINS ─────────────────────────────────
col_left, col_right = st.columns(2)

with col_left:
    st.markdown("#### 🏆 Top Downloaded Files")
    if not top_dl:
        st.info("No download activity yet.")
    else:
        for i, f in enumerate(top_dl, 1):
            name      = f.get("filename", "Unknown")
            downloads = f.get("downloads", 0)
            bar_pct   = int((downloads / top_dl[0]["downloads"]) * 100) if top_dl[0]["downloads"] > 0 else 0
            st.markdown(f"**{i}.** {name}")
            col_bar, col_num = st.columns([5, 1])
            with col_bar:
                st.progress(bar_pct / 100)
            with col_num:
                st.caption(f"{downloads}")

with col_right:
    st.markdown("#### ⚠️ Suspicious Login Activity")
    st.caption("IPs with 5+ failed logins in the last 15 minutes")

    if not sus:
        st.success("No suspicious activity detected.")
    else:
        for item in sus:
            st.markdown(f"""
            <div class='warn-row'>
                🔴 &nbsp;<code>{item['ip']}</code> &nbsp;—&nbsp; <strong>{item['attempts']}</strong> failed attempts
            </div>
            """, unsafe_allow_html=True)

st.markdown("")
st.divider()

# ── ROW 3: STORAGE USAGE PER USER ────────────────────────────────────────────
st.markdown("#### 💾 Storage Usage by User")

if not storage:
    st.info("No storage data available.")
else:
    max_bytes = storage[0]["total_bytes"] if storage else 1

    for user in storage:
        uname      = user.get("username", "Unknown")
        total_b    = user.get("total_bytes", 0)
        file_count = user.get("file_count", 0)
        pct        = total_b / max_bytes if max_bytes > 0 else 0

        size_str = (
            f"{total_b / 1_073_741_824:.2f} GB" if total_b >= 1_073_741_824
            else f"{total_b / 1_048_576:.1f} MB" if total_b >= 1_048_576
            else f"{total_b / 1024:.1f} KB"
        )

        col_name, col_bar, col_info = st.columns([2, 5, 2])
        with col_name:
            st.markdown(f"**{uname}**")
        with col_bar:
            st.progress(pct)
        with col_info:
            st.caption(f"{size_str} · {file_count} file(s)")