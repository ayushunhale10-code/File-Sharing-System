"""
backend/access_control.py
Handles file sharing, permission checks, and access revocation.
All DB operations use database/queries.py.
"""

from database.queries import (
    get_db,
    share_file,
    check_permission,
    revoke_access,
    get_files_shared_with_me,
    find_user_by_email,
    log_event,
)


def share_with_user(file_id: str, owner_id: str, target_email: str,
                    permission: str = "read", expires_at=None,
                    ip_address: str = "0.0.0.0") -> dict:
    """
    Share a file with another user (looked up by email).
    Permission can be: 'read' | 'write' | 'delete' | 'share'
    Returns: { "success": True }
          or { "success": False, "error": str }
    """
    db = get_db()

    valid_permissions = {"read", "write", "delete", "share"}
    if permission not in valid_permissions:
        return {"success": False, "error": f"Invalid permission. Choose from: {valid_permissions}"}

    # Look up the target user by email
    target_user = find_user_by_email(db, target_email)
    if not target_user:
        return {"success": False, "error": "No active user found with that email."}

    target_user_id = str(target_user["_id"])

    # Owner cannot share with themselves
    if target_user_id == owner_id:
        return {"success": False, "error": "You cannot share a file with yourself."}

    # Verify the sharer actually owns or has 'share' permission
    if not check_permission(db, file_id, owner_id, required_permission="share"):
        log_event(db, "share", user_id=owner_id, file_id=file_id,
                  ip_address=ip_address, status="denied",
                  details={"reason": "no share permission"})
        return {"success": False, "error": "You do not have permission to share this file."}

    share_file(
        db,
        file_id=file_id,
        owner_id=owner_id,
        target_user_id=target_user_id,
        permission=permission,
        expires_at=expires_at
    )

    return {
        "success": True,
        "message": f"File shared with {target_email} ({permission} access)."
    }


def remove_access(file_id: str, owner_id: str, target_email: str,
                  ip_address: str = "0.0.0.0") -> dict:
    """
    Revoke a user's access to a file (by their email).
    Only the owner can revoke.
    Returns: { "success": True }
          or { "success": False, "error": str }
    """
    db = get_db()

    # Verify owner has 'share' permission (i.e., they are the owner)
    if not check_permission(db, file_id, owner_id, required_permission="share"):
        return {"success": False, "error": "You do not have permission to revoke access."}

    target_user = find_user_by_email(db, target_email)
    if not target_user:
        return {"success": False, "error": "No active user found with that email."}

    target_user_id = str(target_user["_id"])

    revoke_access(db, file_id=file_id, user_id=target_user_id)

    log_event(db, "share", user_id=owner_id, file_id=file_id,
              ip_address=ip_address, status="success",
              details={"action": "revoke", "revoked_from": target_user_id})

    return {"success": True, "message": f"Access revoked for {target_email}."}


def can_access(file_id: str, user_id: str, permission: str = "read") -> bool:
    """
    Simple True/False permission check.
    Used by other backend modules before performing actions.
    """
    db = get_db()
    return check_permission(db, file_id, user_id, required_permission=permission)


def get_shared_with_me(user_id: str) -> dict:
    """
    Get all files shared with the current user.
    Returns: { "success": True, "files": [...] }
    """
    db = get_db()
    files = get_files_shared_with_me(db, user_id=user_id)

    for f in files:
        f["_id"]      = str(f["_id"])
        f["owner_id"] = str(f["owner_id"])

    return {"success": True, "files": files}