"""
pages/4_My_Activity.py
Personal activity feed showing uploads, downloads, shares, logins.
"""

import streamlit as st
from utils.sidebar import render_sidebar
from backend.activity_logger import my_activity

# ── PAGE CONFIG ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="My Activity — ShareSphere",
    page_icon="📋",
    layout="wide"
)

# ── SIDEBAR ───────────────────────────────────────────────────────────────────
render_sidebar()

user_id = st.session_state.user_id

# ── STYLES ────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .event-row {
        display: flex;
        align-items: center;
        gap: 1rem;
        padding: 0.65rem 0;
        border-bottom: 1px solid #f3f4f6;
        font-size: 0.88rem;
        color: #374151;
    }
    .event-icon { font-size: 1.1rem; width: 1.5rem; text-align: center; }
    .event-type { font-weight: 600; min-width: 90px; }
    .event-time { color: #9ca3af; font-size: 0.78rem; min-width: 160px; }
    .status-success { color: #16a34a; font-weight: 600; }
    .status-failure { color: #dc2626; font-weight: 600; }
    .status-denied  { color: #d97706; font-weight: 600; }
    footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ── ICON MAP ──────────────────────────────────────────────────────────────────
ICON = {
    "upload":   "⬆️",
    "download": "⬇️",
    "delete":   "🗑️",
    "share":    "🔗",
    "login":    "🔐",
    "logout":   "🚪",
}

# ── HEADER ────────────────────────────────────────────────────────────────────
st.markdown("## 📋 My Activity")
st.caption("Your recent actions across ShareSphere.")
st.divider()

limit = st.slider("Show last N events", min_value=10, max_value=100, value=50, step=10)

# ── FETCH EVENTS ──────────────────────────────────────────────────────────────
with st.spinner("Loading activity..."):
    result = my_activity(user_id=user_id, limit=limit)

events = result.get("events", []) if result["success"] else []

if not events:
    st.info("No activity recorded yet.")
else:
    st.caption(f"Showing {len(events)} events")
    st.markdown("")

    # Column headers
    hcol1, hcol2, hcol3, hcol4 = st.columns([1, 2, 3, 2])
    with hcol1: st.caption("Type")
    with hcol2: st.caption("Status")
    with hcol3: st.caption("Details")
    with hcol4: st.caption("Time")

    st.divider()

    for e in events:
        event_type = e.get("event_type", "—")
        status     = e.get("status", "—")
        timestamp  = e.get("timestamp")
        details    = e.get("details", {})
        file_id    = e.get("file_id")

        icon     = ICON.get(event_type, "•")
        time_str = timestamp.strftime("%d %b %Y, %H:%M") if timestamp else "—"

        # Build a details string
        detail_parts = []
        if details.get("filename"):
            detail_parts.append(f"File: {details['filename']}")
        if details.get("file_size"):
            sz = details["file_size"]
            detail_parts.append(
                f"Size: {sz/1_048_576:.1f}MB" if sz >= 1_048_576
                else f"Size: {sz/1024:.1f}KB"
            )
        if details.get("shared_with"):
            detail_parts.append(f"Shared with: {details['shared_with']}")
        if details.get("reason"):
            detail_parts.append(f"Reason: {details['reason']}")
        if file_id and not detail_parts:
            detail_parts.append(f"File ID: {str(file_id)[:12]}...")

        detail_str = "  ·  ".join(detail_parts) if detail_parts else "—"

        status_class = f"status-{status}"

        col1, col2, col3, col4 = st.columns([1, 2, 3, 2])
        with col1:
            st.markdown(f"{icon} **{event_type}**")
        with col2:
            st.markdown(f"<span class='{status_class}'>{status}</span>", unsafe_allow_html=True)
        with col3:
            st.caption(detail_str)
        with col4:
            st.caption(time_str)