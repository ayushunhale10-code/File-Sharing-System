"""
backend/file_handler.py
Handles file upload, download, delete, search, and listing.
Binary files are stored in MongoDB GridFS.
All metadata operations use database/queries.py.
"""

import uuid
import os
from gridfs import GridFS
from database.queries import (
    get_db,
    insert_file,
    get_user_files,
    get_file_by_id,
    search_files,
    soft_delete_file,
    increment_download_count,
    check_permission,
    log_event,
)


def upload_file(user_id: str, file_bytes: bytes, filename: str,
                mime_type: str, tags: list = None,
                description: str = "", is_public: bool = False) -> dict:
    """
    Upload a file to GridFS and save its metadata.
    Returns: { "success": True, "file_id": str }
          or { "success": False, "error": str }
    """
    db = get_db()

    if not file_bytes:
        return {"success": False, "error": "File is empty."}

    file_size = len(file_bytes)
    file_extension = os.path.splitext(filename)[-1].lower()

    # Generate a unique stored name to avoid conflicts
    stored_name = f"{uuid.uuid4()}{file_extension}"

    # Store binary content in GridFS
    fs = GridFS(db)
    gridfs_id = fs.put(
        file_bytes,
        filename=stored_name,
        content_type=mime_type
    )

    # Save metadata to files collection
    file_id = insert_file(
        db,
        owner_id=user_id,
        filename=filename,
        stored_name=stored_name,
        file_size=file_size,
        mime_type=mime_type,
        file_extension=file_extension,
        gridfs_id=gridfs_id,
        tags=tags or [],
        description=description,
        is_public=is_public
    )

    return {"success": True, "file_id": file_id}


def download_file(file_id: str, requesting_user_id: str,
                  ip_address: str = "0.0.0.0", user_agent: str = "") -> dict:
    """
    Download a file's binary content from GridFS.
    Permission is checked before serving.
    Returns: { "success": True, "data": bytes, "filename": str, "mime_type": str }
          or { "success": False, "error": str }
    """
    db = get_db()

    # Check permission first
    if not check_permission(db, file_id, requesting_user_id, required_permission="read"):
        log_event(db, "download", user_id=requesting_user_id, file_id=file_id,
                  ip_address=ip_address, user_agent=user_agent,
                  status="denied", details={"reason": "permission denied"})
        return {"success": False, "error": "You do not have permission to download this file."}

    file_doc = get_file_by_id(db, file_id)
    if not file_doc:
        return {"success": False, "error": "File not found."}

    # Retrieve binary from GridFS
    fs = GridFS(db)
    try:
        grid_out = fs.get(file_doc["gridfs_id"])
        file_bytes = grid_out.read()
    except Exception:
        log_event(db, "download", user_id=requesting_user_id, file_id=file_id,
                  ip_address=ip_address, user_agent=user_agent,
                  status="failure", details={"reason": "GridFS read error"})
        return {"success": False, "error": "Could not retrieve file from storage."}

    # Increment download count and log
    increment_download_count(db, file_id)
    log_event(db, "download", user_id=requesting_user_id, file_id=file_id,
              ip_address=ip_address, user_agent=user_agent,
              status="success", details={"filename": file_doc["filename"]})

    return {
        "success":   True,
        "data":      file_bytes,
        "filename":  file_doc["filename"],
        "mime_type": file_doc["mime_type"]
    }


def delete_file(file_id: str, owner_id: str,
                ip_address: str = "0.0.0.0", user_agent: str = "") -> dict:
    """
    Soft-delete a file (marks as 'deleted', does not remove from GridFS).
    Only the owner can delete.
    Returns: { "success": True }
          or { "success": False, "error": str }
    """
    db = get_db()

    deleted = soft_delete_file(db, file_id=file_id, owner_id=owner_id)

    if not deleted:
        log_event(db, "delete", user_id=owner_id, file_id=file_id,
                  ip_address=ip_address, user_agent=user_agent,
                  status="denied", details={"reason": "not owner or file not found"})
        return {"success": False, "error": "File not found or you are not the owner."}

    return {"success": True}


def list_my_files(user_id: str, page: int = 1, per_page: int = 20) -> dict:
    """
    List all active files owned by a user (paginated).
    Returns: { "success": True, "files": [...], "page": int, "per_page": int }
    """
    db = get_db()
    files = get_user_files(db, user_id=user_id, page=page, per_page=per_page)

    # Convert ObjectIds to strings for JSON safety
    for f in files:
        f["_id"] = str(f["_id"])

    return {
        "success":  True,
        "files":    files,
        "page":     page,
        "per_page": per_page
    }


def search(query: str, user_id: str = None, limit: int = 20) -> dict:
    """
    Full-text search for files by filename, description, or tags.
    If user_id provided, restricts results to that user's files.
    Returns: { "success": True, "results": [...] }
    """
    db = get_db()

    if not query or not query.strip():
        return {"success": False, "error": "Search query cannot be empty."}

    results = search_files(db, query=query, user_id=user_id, limit=limit)

    for r in results:
        r["_id"] = str(r["_id"])

    return {"success": True, "results": results}


def get_file_info(file_id: str, requesting_user_id: str) -> dict:
    """
    Get full metadata for a single file (if user has read permission).
    Returns: { "success": True, "file": {...} }
          or { "success": False, "error": str }
    """
    db = get_db()

    if not check_permission(db, file_id, requesting_user_id, required_permission="read"):
        return {"success": False, "error": "Access denied."}

    file_doc = get_file_by_id(db, file_id)
    if not file_doc:
        return {"success": False, "error": "File not found."}

    file_doc["_id"]       = str(file_doc["_id"])
    file_doc["owner_id"]  = str(file_doc["owner_id"])
    file_doc["gridfs_id"] = str(file_doc["gridfs_id"])

    return {"success": True, "file": file_doc}