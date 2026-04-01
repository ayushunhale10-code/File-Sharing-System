# 🌐 ShareSphere – File Sharing System

## 📌 Overview
ShareSphere is a scalable file sharing system built using Streamlit, Python, and MongoDB (NoSQL). It allows users to upload, store, share, and access files securely with role-based access control and activity monitoring.

## 🚀 Features
- 📂 File Upload & Download (via MongoDB GridFS)
- 🔐 Secure Authentication (bcrypt password hashing)
- 🔑 Role-Based Access Control (Admin / User / Viewer)
- 🤝 File Sharing with Granular Permissions (read / write / delete / share)
- 📊 Monitoring Dashboard (activity logs, top downloads, storage reports)
- 🛡️ Security (ACL, suspicious login detection)
- 💾 Backup & Recovery (mongodump integration)
- ⚡ Optimized MongoDB Queries (12 strategic indexes)
- 🌍 Scalable Architecture (GridFS, Replica Set ready)

## 🛠 Tech Stack
- **Frontend:** Streamlit
- **Backend:** Python
- **Database:** MongoDB (NoSQL) + GridFS
- **Auth:** bcrypt (cost factor 12)
- **Libraries:** PyMongo, python-dotenv

## 📁 Project Structure
```
File-Sharing-System/
├── app.py
│
├── pages/
│   ├── 1_My_Files.py            ← upload, list, download, delete, search
│   ├── 2_Shared_With_Me.py      ← files others shared with you
│   ├── 3_Share_File.py          ← share + revoke access
│   ├── 4_My_Activity.py         ← personal event feed
│   ├── 5_Admin_Monitoring.py    ← event stats, storage, suspicious logins
│   └── 6_Admin_Backup.py        ← run mongodump, view backup history
│
├── utils/
│   └── sidebar.py 
│ 
├── backend/
│   ├── __init__.py
│   ├── auth.py                 # Register, login, logout, profile
│   ├── file_handler.py         # Upload, download, delete, search
│   ├── access_control.py       # Share, revoke, permission checks
│   ├── activity_logger.py      # Monitoring & audit logs
│   └── backup.py               # Backup & recovery (admin only)
│
├── database/
│   ├── queries.py              # All MongoDB queries & DB functions
│   ├── init_db.js              # DB initialization & indexes
│   └── schema.md               # Schema reference document
│
├── uploads/                    # Temporary file storage
├── .env                        # Environment variables (not committed)
├── requirements.txt
└── README.md
```

## ⚙️ Setup Instructions

### 1. Clone the repo
```
git clone https://github.com/ayushunhale10-code/File-Sharing-System.git
cd File-Sharing-System
```

### 2. Install dependencies
```
pip install -r requirements.txt
```

### 3. Create a `.env` file in the root folder
```
MONGO_URI=mongodb://sharesphere_app:sharesphere%40123@localhost:27017/sharesphere_db
BACKUP_DIR=/backups/sharesphere
```

### 4. Initialize the database
```
mongosh "mongodb://localhost:27017/sharesphere_db" database/init_db.js
```

### 5. Create MongoDB user
```
mongosh
use sharesphere_db
db.createUser({ user: "sharesphere_app", pwd: "sharesphere@123", roles: [{ role: "readWrite", db: "sharesphere_db" }] })
exit
```

### 6. Run the app
```
streamlit run app.py
```

## 🗄️ Database Collections
| Collection | Purpose |
|---|---|
| `users` | User accounts & authentication |
| `files` | File metadata & ownership |
| `access_control` | Per-file, per-user ACL permissions |
| `activity_logs` | Audit trail & monitoring |
| `backup_records` | Backup job history |

## 👥 Team
| Role | Name |
|---|---|
| Backend | Ayush Unhale |
| Database | Somesh Singh |
| Frontend |  Riddhi|