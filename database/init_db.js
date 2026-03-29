// =============================================================================
// ShareSphere — MongoDB Initialization Script
// Run with: mongosh sharesphere_db database/init_db.js
// =============================================================================

print("🚀 Starting ShareSphere database initialization...\n");

// ── DROP EXISTING COLLECTIONS (clean slate) ───────────────────────────────────
const existing = db.getCollectionNames();
["users", "files", "access_control", "activity_logs", "backup_records"].forEach(col => {
  if (existing.includes(col)) {
    db[col].drop();
    print(`🗑️  Dropped existing collection: ${col}`);
  }
});

// =============================================================================
// STEP 1 — CREATE COLLECTIONS WITH VALIDATORS
// =============================================================================
print("\n📦 Creating collections with schema validators...");

db.createCollection("users", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["username", "email", "password_hash", "role"],
      properties: {
        username:      { bsonType: "string" },
        email:         { bsonType: "string" },
        password_hash: { bsonType: "string" },
        role:          { bsonType: "string", enum: ["admin", "user", "viewer"] },
        storage_used:  { bsonType: "long" },
        storage_quota: { bsonType: "long" },
        is_active:     { bsonType: "bool" },
        created_at:    { bsonType: "date" },
        updated_at:    { bsonType: "date" },
        last_login:    { bsonType: ["date", "null"] }
      }
    }
  }
});
print("  ✅ users");

db.createCollection("files", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["filename", "owner_id", "file_size", "mime_type", "status"],
      properties: {
        filename:       { bsonType: "string" },
        stored_name:    { bsonType: "string" },
        owner_id:       { bsonType: "objectId" },
        file_size:      { bsonType: "long" },
        mime_type:      { bsonType: "string" },
        file_extension: { bsonType: "string" },
        tags:           { bsonType: "array" },
        is_public:      { bsonType: "bool" },
        shared_with:    { bsonType: "array" },
        download_count: { bsonType: "int" },
        version:        { bsonType: "int" },
        status:         { bsonType: "string", enum: ["active", "deleted", "archived"] }
      }
    }
  }
});
print("  ✅ files");

db.createCollection("access_control", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["file_id", "user_id", "permission", "granted_by"],
      properties: {
        file_id:    { bsonType: "objectId" },
        user_id:    { bsonType: "objectId" },
        permission: { bsonType: "string", enum: ["read", "write", "delete", "share"] },
        granted_by: { bsonType: "objectId" },
        expires_at: { bsonType: ["date", "null"] },
        created_at: { bsonType: "date" }
      }
    }
  }
});
print("  ✅ access_control");

db.createCollection("activity_logs", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["event_type", "user_id", "status", "timestamp"],
      properties: {
        event_type: { bsonType: "string", enum: ["upload","download","delete","share","login","logout"] },
        user_id:    { bsonType: "objectId" },
        file_id:    { bsonType: ["objectId", "null"] },
        ip_address: { bsonType: "string" },
        user_agent: { bsonType: "string" },
        details:    { bsonType: "object" },
        status:     { bsonType: "string", enum: ["success", "failure", "denied"] },
        timestamp:  { bsonType: "date" }
      }
    }
  }
});
print("  ✅ activity_logs");

db.createCollection("backup_records", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["backup_type", "initiated_by", "status", "started_at"],
      properties: {
        backup_type:   { bsonType: "string", enum: ["full", "incremental", "differential"] },
        initiated_by:  { bsonType: "objectId" },
        collections:   { bsonType: "array" },
        output_path:   { bsonType: "string" },
        file_count:    { bsonType: "int" },
        size_bytes:    { bsonType: "long" },
        status:        { bsonType: "string", enum: ["running", "completed", "failed"] },
        error_message: { bsonType: ["string", "null"] },
        started_at:    { bsonType: "date" },
        completed_at:  { bsonType: ["date", "null"] },
        duration_secs: { bsonType: "int" }
      }
    }
  }
});
print("  ✅ backup_records");

// =============================================================================
// STEP 2 — CREATE INDEXES
// =============================================================================
print("\n🔍 Creating indexes...");

// users
db.users.createIndex({ "username": 1 }, { unique: true });
db.users.createIndex({ "email": 1 }, { unique: true });
print("  ✅ users: username (unique), email (unique)");

// files
db.files.createIndex({ "owner_id": 1 });
db.files.createIndex({ "filename": "text", "description": "text", "tags": "text" });
db.files.createIndex({ "owner_id": 1, "status": 1, "created_at": -1 });
db.files.createIndex({ "shared_with": 1 });
db.files.createIndex({ "mime_type": 1 });
print("  ✅ files: owner_id, text search, compound, shared_with, mime_type");

// access_control
db.access_control.createIndex({ "file_id": 1, "user_id": 1, "permission": 1 });
db.access_control.createIndex({ "expires_at": 1 }, { expireAfterSeconds: 0 });
print("  ✅ access_control: compound ACL, TTL expiry");

// activity_logs
db.activity_logs.createIndex({ "user_id": 1, "timestamp": -1 });
db.activity_logs.createIndex({ "file_id": 1, "timestamp": -1 });
db.activity_logs.createIndex({ "event_type": 1 });
db.activity_logs.createIndex({ "timestamp": 1 }, { expireAfterSeconds: 7776000 }); // 90 days TTL
print("  ✅ activity_logs: user+time, file+time, event_type, TTL 90d");

// backup_records
db.backup_records.createIndex({ "started_at": -1 });
db.backup_records.createIndex({ "status": 1 });
print("  ✅ backup_records: started_at, status");

// =============================================================================
// STEP 3 — SEED DATA
// =============================================================================
print("\n🌱 Inserting seed data...");

// Admin user (password: admin@123)
const adminResult = db.users.insertOne({
  username:      "admin",
  email:         "admin@sharesphere.com",
  password_hash: "$2b$12$KIXtOy5N2O1zQv8v5e3x6.G1Y9kL0mN8pR4sT7wU2vA3bC5dE6fH",
  role:          "admin",
  storage_used:  Long(0),
  storage_quota: Long(5368709120),
  is_active:     true,
  created_at:    new Date(),
  updated_at:    new Date(),
  last_login:    null
});
const adminId = adminResult.insertedId;
print(`  ✅ admin user inserted: ${adminId}`);

// Test user (password: test@123)
const testResult = db.users.insertOne({
  username:      "testuser",
  email:         "test@sharesphere.com",
  password_hash: "$2b$12$LJYuPz6O3P2aRw9w6f4y7.H2Z0lM1nO9qS5tU8xV3wB4cD6eF7gI",
  role:          "user",
  storage_used:  Long(2048576),
  storage_quota: Long(5368709120),
  is_active:     true,
  created_at:    new Date(),
  updated_at:    new Date(),
  last_login:    new Date()
});
const testId = testResult.insertedId;
print(`  ✅ testuser inserted: ${testId}`);

// Sample file
const fileId = new ObjectId();
db.files.insertOne({
  _id:            fileId,
  filename:       "sample_report.pdf",
  stored_name:    "a1b2c3d4-sample_report.pdf",
  owner_id:       testId,
  file_size:      Long(2048576),
  mime_type:      "application/pdf",
  file_extension: ".pdf",
  gridfs_id:      new ObjectId(),
  tags:           ["report", "sample", "test"],
  description:    "A sample PDF for testing",
  is_public:      false,
  shared_with:    [],
  download_count: 0,
  version:        1,
  status:         "active",
  created_at:     new Date(),
  updated_at:     new Date()
});
print(`  ✅ sample file inserted: ${fileId}`);

// ACL: admin can read testuser's file
db.access_control.insertOne({
  file_id:    fileId,
  user_id:    adminId,
  permission: "read",
  granted_by: testId,
  expires_at: null,
  created_at: new Date()
});
print("  ✅ ACL entry inserted");

// Activity logs
db.activity_logs.insertMany([
  {
    event_type: "login",
    user_id:    testId,
    file_id:    null,
    ip_address: "127.0.0.1",
    user_agent: "Mozilla/5.0",
    details:    {},
    status:     "success",
    timestamp:  new Date()
  },
  {
    event_type: "upload",
    user_id:    testId,
    file_id:    fileId,
    ip_address: "127.0.0.1",
    user_agent: "Mozilla/5.0",
    details:    { file_size: 2048576, filename: "sample_report.pdf" },
    status:     "success",
    timestamp:  new Date()
  },
  {
    event_type: "download",
    user_id:    adminId,
    file_id:    fileId,
    ip_address: "192.168.1.10",
    user_agent: "Mozilla/5.0",
    details:    {},
    status:     "success",
    timestamp:  new Date()
  }
]);
print("  ✅ 3 activity log entries inserted");

// Backup record
db.backup_records.insertOne({
  backup_type:   "full",
  initiated_by:  adminId,
  collections:   ["users", "files", "access_control", "activity_logs"],
  output_path:   "/backups/sharesphere/init",
  file_count:    4,
  size_bytes:    Long(1048576),
  status:        "completed",
  error_message: null,
  started_at:    new Date(Date.now() - 120000),
  completed_at:  new Date(),
  duration_secs: 120
});
print("  ✅ backup record inserted");

// =============================================================================
// STEP 4 — VERIFY
// =============================================================================
print("\n📊 Verification counts:");
print(`  users:          ${db.users.countDocuments()}`);
print(`  files:          ${db.files.countDocuments()}`);
print(`  access_control: ${db.access_control.countDocuments()}`);
print(`  activity_logs:  ${db.activity_logs.countDocuments()}`);
print(`  backup_records: ${db.backup_records.countDocuments()}`);

print("\n✅ ShareSphere database initialization complete!");
print("   Connection string: mongodb://sharesphere_app:sharesphere@123@localhost:27017/sharesphere_db");