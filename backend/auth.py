"""
backend/auth.py
Handles user registration, login, and session helpers.
All DB operations are delegated to database/queries.py.
"""

from database.queries import (
    get_db,
    create_user,
    find_user_by_email,
    find_user_by_id,
    verify_password,
    update_last_login,
    get_storage_info,
    deactivate_user,
    log_event,
)


def register(username: str, email: str, password: str, role: str = "user") -> dict:
    """
    Register a new user.
    Returns: { "success": True, "user_id": str }
          or { "success": False, "error": str }
    """
    if not username or not email or not password:
        return {"success": False, "error": "All fields are required."}

    if len(password) < 6:
        return {"success": False, "error": "Password must be at least 6 characters."}

    db = get_db()
    return create_user(db, username=username, email=email, password=password, role=role)


def login(email: str, password: str, ip_address: str = "0.0.0.0", user_agent: str = "") -> dict:
    """
    Authenticate a user by email and password.
    Returns: { "success": True, "user": { _id, username, role, ... } }
          or { "success": False, "error": str }
    """
    db = get_db()

    if not email or not password:
        return {"success": False, "error": "Email and password are required."}

    user = find_user_by_email(db, email)

    if not user:
        log_event(db, "login", user_id=None, ip_address=ip_address,
                  user_agent=user_agent, status="failure",
                  details={"reason": "user not found", "email": email})
        return {"success": False, "error": "Invalid email or password."}

    if not verify_password(password, user["password_hash"]):
        log_event(db, "login", user_id=user["_id"], ip_address=ip_address,
                  user_agent=user_agent, status="failure",
                  details={"reason": "wrong password"})
        return {"success": False, "error": "Invalid email or password."}

    # Success — update last login and log the event
    update_last_login(db, str(user["_id"]))
    log_event(db, "login", user_id=user["_id"], ip_address=ip_address,
              user_agent=user_agent, status="success")

    return {
        "success": True,
        "user": {
            "user_id":  str(user["_id"]),
            "username": user["username"],
            "role":     user["role"],
        }
    }


def logout(user_id: str, ip_address: str = "0.0.0.0", user_agent: str = "") -> dict:
    """
    Log a logout event.
    Returns: { "success": True }
    """
    db = get_db()
    log_event(db, "logout", user_id=user_id, ip_address=ip_address,
              user_agent=user_agent, status="success")
    return {"success": True}


def get_profile(user_id: str) -> dict:
    """
    Fetch user profile + storage info.
    Returns: { "success": True, "profile": {...} }
          or { "success": False, "error": str }
    """
    db = get_db()
    user = find_user_by_id(db, user_id)

    if not user:
        return {"success": False, "error": "User not found."}

    storage = get_storage_info(db, user_id)

    return {
        "success": True,
        "profile": {
            "user_id":       str(user["_id"]),
            "username":      user["username"],
            "email":         user["email"],
            "role":          user["role"],
            "storage_used":  storage.get("storage_used", 0),
            "storage_quota": storage.get("storage_quota", 0),
            "created_at":    user.get("created_at"),
            "last_login":    user.get("last_login"),
        }
    }


def delete_account(user_id: str) -> dict:
    """
    Soft-delete (deactivate) a user account.
    Returns: { "success": True }
    """
    db = get_db()
    deactivate_user(db, user_id)
    return {"success": True}