# ShareSphere — MongoDB Schema Reference

> **Database:** `sharesphere_db`   

---

## 📦 Collections Overview

| Collection        | Purpose                              | Key Indexes                         |
|------------------|--------------------------------------|-------------------------------------|
| `users`          | User accounts, authentication        | username (unique), email (unique)   |
| `files`          | File metadata & ownership            | owner_id, text search, compound     |
| `access_control` | File-level permissions (ACL)         | compound (file+user+permission), TTL|
| `activity_logs`  | Audit logs & monitoring              | user+time, file+time, TTL           |
| `backup_records` | Backup tracking                      | started_at, status                  |

---

## 👤 Collection: `users`

Stores all registered users. Passwords are securely hashed using **bcrypt (cost factor 12)**.

### Fields

| Field            | Type      | Required | Description |
|------------------|----------|----------|-------------|
| `_id`            | ObjectId | auto     | Primary key |
| `username`       | String   | ✅       | Unique username |
| `email`          | String   | ✅       | Unique login email |
| `password_hash`  | String   | ✅       | bcrypt hashed password |
| `role`           | String   | ✅       | `admin` / `user` / `viewer` |
| `storage_used`   | Long     | —        | Used storage (bytes) |
| `storage_quota`  | Long     | —        | Max storage (default 5GB) |
| `is_active`      | Boolean  | —        | Soft delete flag |
| `created_at`     | Date     | —        | Account creation time |
| `updated_at`     | Date     | —        | Last update |
| `last_login`     | Date/null| —        | Last login timestamp |

### Roles

- **admin** → full system access  
- **user** → upload/manage own files  
- **viewer** → read-only access  

---

## 📁 Collection: `files`

Stores metadata of uploaded files. Actual file data is stored using **MongoDB GridFS**.

### Fields

| Field            | Type            | Required | Description |
|------------------|-----------------|----------|-------------|
| `_id`            | ObjectId        | auto     | Primary key |
| `filename`       | String          | ✅       | Original filename |
| `stored_name`    | String          | —        | Unique stored name |
| `owner_id`       | ObjectId        | ✅       | Reference → users |
| `file_size`      | Long            | ✅       | File size in bytes |
| `mime_type`      | String          | ✅       | File type |
| `file_extension` | String          | —        | Extension |
| `gridfs_id`      | ObjectId        | —        | Reference to GridFS |
| `tags`           | Array[String]   | —        | Search tags |
| `description`    | String          | —        | File description |
| `is_public`      | Boolean         | —        | Public access flag |
| `shared_with`    | Array[ObjectId] | —        | Shared users |
| `download_count` | Int             | —        | Download counter |
| `version`        | Int             | —        | File version |
| `status`         | String          | ✅       | `active` / `deleted` / `archived` |
| `created_at`     | Date            | —        | Upload time |
| `updated_at`     | Date            | —        | Last update |

### Notes

- Files are **soft deleted** (`status = deleted`)
- `shared_with` improves performance for quick access

---

## 🔐 Collection: `access_control`

Manages per-file user permissions.

### Fields

| Field         | Type      | Required | Description |
|--------------|----------|----------|-------------|
| `_id`        | ObjectId | auto     | Primary key |
| `file_id`    | ObjectId | ✅       | Reference → files |
| `user_id`    | ObjectId | ✅       | Reference → users |
| `permission` | String   | ✅       | `read` / `write` / `delete` / `share` |
| `granted_by` | ObjectId | ✅       | Who granted access |
| `expires_at` | Date/null| —        | TTL expiry |
| `created_at` | Date     | —        | Created time |

### Permission Hierarchy

- `read` → download  
- `write` → modify  
- `delete` → remove  
- `share` → grant access  

### Access Logic

A user can access a file if:

1. Owner  
2. Public file  
3. In `shared_with`  
4. Valid ACL entry exists  

---

## 📊 Collection: `activity_logs`

Tracks all system activities (audit logs).

### Fields

| Field         | Type            | Required | Description |
|--------------|-----------------|----------|-------------|
| `_id`        | ObjectId        | auto     | Primary key |
| `event_type` | String          | ✅       | Event type |
| `user_id`    | ObjectId        | ✅       | User |
| `file_id`    | ObjectId/null   | —        | File |
| `ip_address` | String          | —        | Client IP |
| `user_agent` | String          | —        | Browser info |
| `details`    | Object          | —        | Extra data |
| `status`     | String          | ✅       | success/failure/denied |
| `timestamp`  | Date            | ✅       | Event time |

### Event Types

- login  
- logout  
- upload  
- download  
- delete  
- share  

> TTL: Logs auto-delete after **90 days**

---

## 💾 Collection: `backup_records`

Tracks database backup operations.

### Fields

| Field            | Type      | Required | Description |
|------------------|----------|----------|-------------|
| `_id`            | ObjectId | auto     | Primary key |
| `backup_type`    | String   | ✅       | full/incremental/differential |
| `initiated_by`   | ObjectId | ✅       | Admin user |
| `collections`    | Array    | —        | Collections backed up |
| `output_path`    | String   | —        | Backup location |
| `file_count`     | Int      | —        | Number of files |
| `size_bytes`     | Long     | —        | Backup size |
| `status`         | String   | ✅       | running/completed/failed |
| `error_message`  | String   | —        | Error details |
| `started_at`     | Date     | ✅       | Start time |
| `completed_at`   | Date     | —        | End time |
| `duration_secs`  | Int      | —        | Duration |

---

## ⚡ Index Summary

```text
users
  username (unique)
  email (unique)

files
  owner_id
  text index (filename, description, tags)
  compound (owner_id, status, created_at)
  shared_with
  mime_type

access_control
  compound (file_id, user_id, permission)
  expires_at (TTL)

activity_logs
  user_id + timestamp
  file_id + timestamp
  event_type
  timestamp (TTL 90 days)

backup_records
  started_at
  status