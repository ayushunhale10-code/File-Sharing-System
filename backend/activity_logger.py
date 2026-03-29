"""
backend/activity_logger.py
Exposes monitoring and audit functions for dashboards.
All raw DB queries live in database/queries.py.
"""

from database.queries import (
    get_db,
    get_user_activity,
    get_file_audit_trail,
    get_event_summary,
    detect_suspicious_logins,
    get_top_downloaded_files,
    get_storage_report,
)


def my_activity(user_id: str, limit: int = 50) -> dict:
    """
    Fetch a user's recent activity (for their personal dashboard).
    Returns: { "success": True, "events": [...] }
    """
    db = get_db()
    events = get_user_activity(db, user_id=user_id, limit=limit)

    for e in events:
        e["_id"]     = str(e["_id"])
        e["user_id"] = str(e.get("user_id", ""))
        if e.get("file_id"):
            e["file_id"] = str(e["file_id"])

    return {"success": True, "events": events}


def file_audit(file_id: str) -> dict:
    """
    Full audit trail for a specific file (admin use).
    Returns: { "success": True, "trail": [...] }
    """
    db = get_db()
    trail = get_file_audit_trail(db, file_id=file_id)

    for e in trail:
        e["_id"]     = str(e["_id"])
        e["user_id"] = str(e.get("user_id", ""))
        if e.get("file_id"):
            e["file_id"] = str(e["file_id"])

    return {"success": True, "trail": trail}


def event_summary(days: int = 30) -> dict:
    """
    Count of each event type over the last N days (for admin dashboard).
    Returns: { "success": True, "summary": [{ "event": "upload", "count": 89 }, ...] }
    """
    db = get_db()
    raw = get_event_summary(db, days=days)

    summary = [{"event": item["_id"], "count": item["count"]} for item in raw]
    return {"success": True, "summary": summary}


def suspicious_logins(threshold: int = 5, window_minutes: int = 15) -> dict:
    """
    Detect IPs with multiple failed login attempts (brute-force detection).
    Returns: { "success": True, "suspicious": [{ "ip": "x.x.x.x", "attempts": 8 }, ...] }
    """
    db = get_db()
    raw = detect_suspicious_logins(db, threshold=threshold, window_minutes=window_minutes)

    result = [{"ip": item["_id"], "attempts": item["attempts"]} for item in raw]
    return {"success": True, "suspicious": result}


def top_downloads(limit: int = 10) -> dict:
    """
    Top N most downloaded files (for admin dashboard).
    Returns: { "success": True, "files": [{ "filename": "...", "downloads": N }, ...] }
    """
    db = get_db()
    raw = get_top_downloaded_files(db, limit=limit)

    files = [{"filename": item.get("filename", "Unknown"),
              "downloads": item["downloads"]} for item in raw]
    return {"success": True, "files": files}


def storage_report() -> dict:
    """
    Per-user storage usage (for admin dashboard).
    Returns: { "success": True, "report": [{ "username": "...", "total_bytes": N, "file_count": N }, ...] }
    """
    db = get_db()
    raw = get_storage_report(db)

    report = [{
        "username":    item.get("username", "Unknown"),
        "total_bytes": item.get("total_bytes", 0),
        "file_count":  item.get("file_count", 0)
    } for item in raw]

    return {"success": True, "report": report}