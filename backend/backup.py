"""
backend/backup.py
Admin-only backup and recovery management.
Runs mongodump as a subprocess and logs results to backup_records collection.
All DB operations use database/queries.py.
"""

import subprocess
import os
from pathlib import Path
from datetime import datetime, timezone

from database.queries import (
    get_db,
    start_backup_record,
    complete_backup_record,
    fail_backup_record,
    get_latest_backup,
    get_failed_backups,
)

# Base folder where backups are stored
BACKUP_BASE_DIR = os.getenv("BACKUP_DIR", "/backups/sharesphere")
MONGO_URI       = os.getenv("MONGO_URI", "mongodb://sharesphere_app:sharesphere%40123@localhost:27017/sharesphere_db")


def run_backup(admin_user_id: str, backup_type: str = "full") -> dict:
    """
    Run a mongodump backup and record the result.
    Only admins should call this (role check done in app.py).
    Returns: { "success": True, "record_id": str, "output_path": str }
          or { "success": False, "error": str }
    """
    db = get_db()

    timestamp   = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M")
    output_path = os.path.join(BACKUP_BASE_DIR, timestamp)

    # Create a 'running' record before starting
    record_id = start_backup_record(db, admin_user_id=admin_user_id, backup_type=backup_type)

    os.makedirs(output_path, exist_ok=True)

    try:
        result = subprocess.run(
            [
                "mongodump",
                "--uri",   MONGO_URI,
                "--db",    "sharesphere_db",
                "--gzip",
                "--out",   output_path
            ],
            capture_output=True,
            timeout=600  # 10 minutes max
        )

        if result.returncode != 0:
            error_msg = result.stderr.decode("utf-8", errors="ignore")
            fail_backup_record(db, record_id=record_id, error_message=error_msg)
            return {"success": False, "error": f"mongodump failed: {error_msg}"}

        # Calculate total backup size
        size_bytes = sum(
            f.stat().st_size for f in Path(output_path).rglob("*") if f.is_file()
        )
        # Count backed-up files
        file_count = len(list(Path(output_path).rglob("*.bson.gz")))

        complete_backup_record(
            db,
            record_id=record_id,
            output_path=output_path,
            size_bytes=size_bytes,
            file_count=file_count
        )

        return {
            "success":     True,
            "record_id":   record_id,
            "output_path": output_path,
            "size_bytes":  size_bytes,
            "file_count":  file_count
        }

    except subprocess.TimeoutExpired:
        fail_backup_record(db, record_id=record_id, error_message="Backup timed out after 10 minutes.")
        return {"success": False, "error": "Backup timed out."}

    except Exception as e:
        fail_backup_record(db, record_id=record_id, error_message=str(e))
        return {"success": False, "error": str(e)}


def latest_backup_status() -> dict:
    """
    Get the most recent backup record (for admin dashboard).
    Returns: { "success": True, "backup": {...} }
          or { "success": True, "backup": None }  if no backups exist yet
    """
    db = get_db()
    record = get_latest_backup(db)

    if record:
        record["_id"]          = str(record["_id"])
        record["initiated_by"] = str(record["initiated_by"])

    return {"success": True, "backup": record}


def recent_failures(days: int = 7) -> dict:
    """
    Get all failed backup jobs in the last N days.
    Returns: { "success": True, "failures": [...] }
    """
    db = get_db()
    records = get_failed_backups(db, days=days)

    for r in records:
        r["_id"]          = str(r["_id"])
        r["initiated_by"] = str(r["initiated_by"])

    return {"success": True, "failures": records}