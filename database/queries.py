import os
import bcrypt
from datetime import datetime, timezone
from bson import ObjectId, Int64
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError
from dotenv import load_dotenv

# ── LOAD ENV ────────────────────────────────────────────────────────────────
load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")
print("MONGO_URI:", MONGO_URI)

# ── CONNECTION ───────────────────────────────────────────────────────────────
from pymongo import MongoClient

def get_db():
    client = MongoClient(
        "mongodb://sharesphere_app:sharesphere%40123@127.0.0.1:27017/?authSource=sharesphere_db",
        serverSelectionTimeoutMS=5000
    )

    client.admin.command("ping")  # force auth

    return client["sharesphere_db"]

# ── UTILITY ──────────────────────────────────────────────────────────────────
def now():
    return datetime.now(timezone.utc)

def to_object_id(id_value):
    if isinstance(id_value, ObjectId):
        return id_value
    return ObjectId(str(id_value))

# ── USERS ─────────────────────────────────────────────────────────────────────
def create_user(db, username: str, email: str, password: str, role: str = "user") -> dict:
    password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")
    try:
        result = db.users.insert_one({
            "username":      username,
            "email":         email,
            "password_hash": password_hash,
            "role":          role,
            "storage_used":  Int64(0),
            "storage_quota": Int64(5368709120),
            "is_active":     True,
            "created_at":    now(),
            "updated_at":    now(),
            "last_login":    None
        })
        log_event(db, "login", result.inserted_id, status="success", details={"action": "register"})
        return {"success": True, "user_id": str(result.inserted_id)}
    except DuplicateKeyError as e:
        field = "username" if "username" in str(e) else "email"
        return {"success": False, "error": f"{field} already exists"}


def find_user_by_email(db, email: str) -> dict | None:
    return db.users.find_one(
        {"email": email, "is_active": True},
        {"password_hash": 1, "username": 1, "role": 1, "storage_used": 1, "storage_quota": 1}
    )


def find_user_by_id(db, user_id: str) -> dict | None:
    return db.users.find_one(
        {"_id": to_object_id(user_id), "is_active": True},
        {"password_hash": 0}
    )


def verify_password(plain_password: str, stored_hash: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), stored_hash.encode("utf-8"))


def update_last_login(db, user_id: str):
    db.users.update_one(
        {"_id": to_object_id(user_id)},
        {"$set": {"last_login": now(), "updated_at": now()}}
    )


def update_storage_used(db, user_id: str, delta_bytes: int):
    db.users.update_one(
        {"_id": to_object_id(user_id)},
        {"$inc": {"storage_used": Int64(delta_bytes)}, "$set": {"updated_at": now()}}
    )


def get_storage_info(db, user_id: str) -> dict:
    doc = db.users.find_one(
        {"_id": to_object_id(user_id)},
        {"storage_used": 1, "storage_quota": 1}
    )
    return {"storage_used": doc["storage_used"], "storage_quota": doc["storage_quota"]} if doc else {}


def deactivate_user(db, user_id: str):
    db.users.update_one(
        {"_id": to_object_id(user_id)},
        {"$set": {"is_active": False, "updated_at": now()}}
    )

# ── FILES ─────────────────────────────────────────────────────────────────────
def insert_file(db, owner_id: str, filename: str, stored_name: str,
                file_size: int, mime_type: str, file_extension: str,
                gridfs_id=None, tags: list = None, description: str = "",
                is_public: bool = False) -> str:
    result = db.files.insert_one({
        "filename":       filename,
        "stored_name":    stored_name,
        "owner_id":       to_object_id(owner_id),
        "file_size":      Int64(file_size),
        "mime_type":      mime_type,
        "file_extension": file_extension,
        "gridfs_id":      to_object_id(gridfs_id) if gridfs_id else None,
        "tags":           tags or [],
        "description":    description,
        "is_public":      is_public,
        "shared_with":    [],
        "download_count": 0,
        "version":        1,
        "status":         "active",
        "created_at":     now(),
        "updated_at":     now()
    })
    file_id = str(result.inserted_id)
    update_storage_used(db, owner_id, file_size)
    log_event(db, "upload", owner_id, file_id=file_id,
              details={"file_size": file_size, "filename": filename})
    return file_id


def get_user_files(db, user_id: str, page: int = 1, per_page: int = 20) -> list:
    skip = (page - 1) * per_page
    cursor = db.files.find(
        {"owner_id": to_object_id(user_id), "status": "active"},
        {"filename": 1, "file_size": 1, "mime_type": 1,
         "created_at": 1, "download_count": 1, "is_public": 1, "tags": 1}
    ).sort("created_at", -1).skip(skip).limit(per_page)
    return list(cursor)


def get_file_by_id(db, file_id: str) -> dict | None:
    return db.files.find_one({"_id": to_object_id(file_id), "status": "active"})


def search_files(db, query: str, user_id: str = None, limit: int = 20) -> list:
    match = {"$text": {"$search": query}, "status": "active"}
    if user_id:
        match["owner_id"] = to_object_id(user_id)
    cursor = db.files.find(
        match,
        {"score": {"$meta": "textScore"}}
    ).sort("score", {"$meta": "textScore"}).limit(limit)
    return list(cursor)


def increment_download_count(db, file_id: str):
    db.files.update_one(
        {"_id": to_object_id(file_id)},
        {"$inc": {"download_count": 1}, "$set": {"updated_at": now()}}
    )


def soft_delete_file(db, file_id: str, owner_id: str) -> bool:
    file_doc = db.files.find_one({"_id": to_object_id(file_id)})
    if not file_doc:
        return False
    result = db.files.update_one(
        {"_id": to_object_id(file_id), "owner_id": to_object_id(owner_id)},
        {"$set": {"status": "deleted", "updated_at": now()}}
    )
    if result.modified_count > 0:
        update_storage_used(db, owner_id, -file_doc["file_size"])
        log_event(db, "delete", owner_id, file_id=file_id,
                  details={"filename": file_doc["filename"]})
        return True
    return False


def share_file(db, file_id: str, owner_id: str, target_user_id: str,
               permission: str = "read", expires_at=None) -> bool:
    db.files.update_one(
        {"_id": to_object_id(file_id), "owner_id": to_object_id(owner_id)},
        {
            "$addToSet": {"shared_with": to_object_id(target_user_id)},
            "$set": {"updated_at": now()}
        }
    )
    grant_access(db, file_id, target_user_id, permission, owner_id, expires_at)
    log_event(db, "share", owner_id, file_id=file_id,
              details={"shared_with": target_user_id, "permission": permission})
    return True


def get_files_shared_with_me(db, user_id: str) -> list:
    cursor = db.files.find(
        {"shared_with": to_object_id(user_id), "status": "active"},
        {"filename": 1, "owner_id": 1, "file_size": 1, "mime_type": 1, "created_at": 1}
    ).sort("created_at", -1)
    return list(cursor)

# ── ACCESS CONTROL ────────────────────────────────────────────────────────────
def check_permission(db, file_id: str, user_id: str, required_permission: str = "read") -> bool:
    file_doc = db.files.find_one(
        {
            "_id": to_object_id(file_id),
            "$or": [
                {"owner_id": to_object_id(user_id)},
                {"is_public": True},
                {"shared_with": to_object_id(user_id)}
            ],
            "status": "active"
        },
        {"_id": 1}
    )
    if file_doc:
        return True

    permission_hierarchy = {
        "read":   ["read", "write", "delete", "share"],
        "write":  ["write", "delete", "share"],
        "delete": ["delete", "share"],
        "share":  ["share"]
    }
    allowed = permission_hierarchy.get(required_permission, [required_permission])

    acl = db.access_control.find_one({
        "file_id":    to_object_id(file_id),
        "user_id":    to_object_id(user_id),
        "permission": {"$in": allowed},
        "$or": [
            {"expires_at": None},
            {"expires_at": {"$gt": now()}}
        ]
    })
    return acl is not None


def grant_access(db, file_id: str, user_id: str, permission: str,
                 granted_by: str, expires_at=None):
    db.access_control.insert_one({
        "file_id":    to_object_id(file_id),
        "user_id":    to_object_id(user_id),
        "permission": permission,
        "granted_by": to_object_id(granted_by),
        "expires_at": expires_at,
        "created_at": now()
    })


def revoke_access(db, file_id: str, user_id: str):
    db.access_control.delete_many({
        "file_id": to_object_id(file_id),
        "user_id": to_object_id(user_id)
    })
    db.files.update_one(
        {"_id": to_object_id(file_id)},
        {"$pull": {"shared_with": to_object_id(user_id)}}
    )

# ── ACTIVITY LOGS ─────────────────────────────────────────────────────────────
def log_event(db, event_type: str, user_id, file_id=None,
              ip_address: str = "0.0.0.0", user_agent: str = "",
              status: str = "success", details: dict = None):
    db.activity_logs.insert_one({
        "event_type": event_type,
        "user_id":    to_object_id(user_id) if user_id else None,
        "file_id":    to_object_id(file_id) if file_id else None,
        "ip_address": ip_address,
        "user_agent": user_agent,
        "details":    details or {},
        "status":     status,
        "timestamp":  now()
    })


def get_user_activity(db, user_id: str, limit: int = 50) -> list:
    cursor = db.activity_logs.find(
        {"user_id": to_object_id(user_id)},
        {"event_type": 1, "file_id": 1, "status": 1, "timestamp": 1, "details": 1}
    ).sort("timestamp", -1).limit(limit)
    return list(cursor)


def get_file_audit_trail(db, file_id: str) -> list:
    cursor = db.activity_logs.find(
        {"file_id": to_object_id(file_id)}
    ).sort("timestamp", -1)
    return list(cursor)


def get_event_summary(db, days: int = 30) -> list:
    from_date = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0)
    pipeline = [
        {"$match": {"timestamp": {"$gte": from_date}}},
        {"$group": {"_id": "$event_type", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
    return list(db.activity_logs.aggregate(pipeline))


def detect_suspicious_logins(db, threshold: int = 5, window_minutes: int = 15) -> list:
    from datetime import timedelta
    since = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)
    pipeline = [
        {"$match": {"event_type": "login", "status": "failure", "timestamp": {"$gte": since}}},
        {"$group": {"_id": "$ip_address", "attempts": {"$sum": 1}}},
        {"$match": {"attempts": {"$gte": threshold}}}
    ]
    return list(db.activity_logs.aggregate(pipeline))


def get_top_downloaded_files(db, limit: int = 10) -> list:
    pipeline = [
        {"$match": {"event_type": "download", "status": "success"}},
        {"$group": {"_id": "$file_id", "downloads": {"$sum": 1}}},
        {"$sort": {"downloads": -1}},
        {"$limit": limit},
        {"$lookup": {
            "from":         "files",
            "localField":   "_id",
            "foreignField": "_id",
            "as":           "file_info"
        }},
        {"$unwind": "$file_info"},
        {"$project": {"filename": "$file_info.filename", "downloads": 1}}
    ]
    return list(db.activity_logs.aggregate(pipeline))


def get_storage_report(db) -> list:
    pipeline = [
        {"$match": {"status": "active"}},
        {"$group": {
            "_id":         "$owner_id",
            "total_bytes": {"$sum": "$file_size"},
            "file_count":  {"$sum": 1}
        }},
        {"$sort": {"total_bytes": -1}},
        {"$lookup": {
            "from":         "users",
            "localField":   "_id",
            "foreignField": "_id",
            "as":           "user"
        }},
        {"$unwind": "$user"},
        {"$project": {
            "username":    "$user.username",
            "total_bytes": 1,
            "file_count":  1
        }}
    ]
    return list(db.files.aggregate(pipeline))

# ── BACKUP RECORDS ────────────────────────────────────────────────────────────
def start_backup_record(db, admin_user_id: str, backup_type: str = "full") -> str:
    result = db.backup_records.insert_one({
        "backup_type":   backup_type,
        "initiated_by":  to_object_id(admin_user_id),
        "collections":   ["users", "files", "access_control", "activity_logs"],
        "output_path":   "",
        "file_count":    0,
        "size_bytes":    0,
        "status":        "running",
        "error_message": None,
        "started_at":    now(),
        "completed_at":  None,
        "duration_secs": 0
    })
    return str(result.inserted_id)


def complete_backup_record(db, record_id: str, output_path: str,
                           size_bytes: int, file_count: int):
    started = db.backup_records.find_one(
        {"_id": to_object_id(record_id)},
        {"started_at": 1}
    )
    duration = int((now() - started["started_at"]).total_seconds()) if started else 0
    db.backup_records.update_one(
        {"_id": to_object_id(record_id)},
        {"$set": {
            "status":        "completed",
            "output_path":   output_path,
            "size_bytes":    size_bytes,
            "file_count":    file_count,
            "completed_at":  now(),
            "duration_secs": duration
        }}
    )


def fail_backup_record(db, record_id: str, error_message: str):
    db.backup_records.update_one(
        {"_id": to_object_id(record_id)},
        {"$set": {
            "status":        "failed",
            "error_message": error_message,
            "completed_at":  now()
        }}
    )


def get_latest_backup(db) -> dict | None:
    return db.backup_records.find_one({}, sort=[("started_at", -1)])


def get_failed_backups(db, days: int = 7) -> list:
    from datetime import timedelta
    since = datetime.now(timezone.utc) - timedelta(days=days)
    cursor = db.backup_records.find(
        {"status": "failed", "started_at": {"$gte": since}}
    ).sort("started_at", -1)
    return list(cursor)