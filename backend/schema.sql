-- =====================================================================
-- LostnFound Campus App — PostgreSQL Schema for Supabase
-- Run this in Supabase SQL Editor (Project → SQL Editor → New query)
-- =====================================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =====================================================================
-- TABLE: admins
-- =====================================================================
CREATE TABLE IF NOT EXISTS admins (
    id           TEXT        PRIMARY KEY DEFAULT gen_random_uuid()::TEXT,
    username     TEXT        NOT NULL UNIQUE,
    password     TEXT        NOT NULL,
    full_name    TEXT        NOT NULL,
    role         TEXT        NOT NULL DEFAULT 'admin'
                             CHECK (role IN ('admin', 'super_admin')),
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by   TEXT        REFERENCES admins(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_admins_username ON admins(username);
CREATE INDEX IF NOT EXISTS idx_admins_role     ON admins(role);

-- =====================================================================
-- TABLE: students
-- =====================================================================
CREATE TABLE IF NOT EXISTS students (
    id              TEXT        PRIMARY KEY DEFAULT gen_random_uuid()::TEXT,
    roll_number     TEXT        NOT NULL UNIQUE,
    full_name       TEXT        NOT NULL,
    department      TEXT        NOT NULL,
    year            TEXT        NOT NULL,
    dob             TEXT        NOT NULL,   -- stored as DD-MM-YYYY
    email           TEXT        NOT NULL,
    phone_number    TEXT        NOT NULL,
    profile_picture TEXT,
    admin_notes     JSONB       NOT NULL DEFAULT '[]'::JSONB,
    is_deleted      BOOLEAN     NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_date    TEXT,                   -- YYYY-MM-DD
    created_time    TEXT                    -- HH:MM:SS
);

CREATE INDEX IF NOT EXISTS idx_students_roll_number ON students(roll_number);
CREATE INDEX IF NOT EXISTS idx_students_is_deleted  ON students(is_deleted);

-- =====================================================================
-- TABLE: items
-- =====================================================================
CREATE TABLE IF NOT EXISTS items (
    id            TEXT        PRIMARY KEY DEFAULT gen_random_uuid()::TEXT,
    item_type     TEXT        NOT NULL CHECK (item_type IN ('lost', 'found')),
    description   TEXT        NOT NULL,
    location      TEXT        NOT NULL,
    image_url     TEXT,
    student_id    TEXT        NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    status        TEXT        NOT NULL DEFAULT 'active'
                              CHECK (status IN ('active', 'claimed', 'resolved')),
    is_deleted    BOOLEAN     NOT NULL DEFAULT FALSE,
    delete_reason TEXT,
    deleted_at    TIMESTAMPTZ,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_date  TEXT,                   -- YYYY-MM-DD
    created_time  TEXT,                   -- HH:MM:SS
    likes         INTEGER     NOT NULL DEFAULT 0,
    dislikes      INTEGER     NOT NULL DEFAULT 0,
    liked_by      JSONB       NOT NULL DEFAULT '[]'::JSONB,
    disliked_by   JSONB       NOT NULL DEFAULT '[]'::JSONB
);

CREATE INDEX IF NOT EXISTS idx_items_student_id  ON items(student_id);
CREATE INDEX IF NOT EXISTS idx_items_item_type   ON items(item_type);
CREATE INDEX IF NOT EXISTS idx_items_status      ON items(status);
CREATE INDEX IF NOT EXISTS idx_items_is_deleted  ON items(is_deleted);
CREATE INDEX IF NOT EXISTS idx_items_created_at  ON items(created_at DESC);

-- =====================================================================
-- TABLE: claims
-- =====================================================================
CREATE TABLE IF NOT EXISTS claims (
    id                      TEXT        PRIMARY KEY DEFAULT gen_random_uuid()::TEXT,
    item_id                 TEXT        NOT NULL REFERENCES items(id) ON DELETE CASCADE,
    claimant_id             TEXT        NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    message                 TEXT        NOT NULL DEFAULT '',
    status                  TEXT        NOT NULL DEFAULT 'pending'
                                        CHECK (status IN ('pending', 'under_review', 'approved', 'rejected')),
    verification_questions  JSONB       NOT NULL DEFAULT '[]'::JSONB,
    verification_answers    JSONB       NOT NULL DEFAULT '[]'::JSONB,
    admin_notes             TEXT        NOT NULL DEFAULT '',
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_claims_item_id     ON claims(item_id);
CREATE INDEX IF NOT EXISTS idx_claims_claimant_id ON claims(claimant_id);
CREATE INDEX IF NOT EXISTS idx_claims_status      ON claims(status);

-- =====================================================================
-- TABLE: messages
-- =====================================================================
CREATE TABLE IF NOT EXISTS messages (
    id             TEXT        PRIMARY KEY DEFAULT gen_random_uuid()::TEXT,
    sender_id      TEXT        NOT NULL,
    sender_type    TEXT        NOT NULL CHECK (sender_type IN ('admin', 'super_admin', 'student')),
    recipient_id   TEXT        NOT NULL,
    recipient_type TEXT        NOT NULL CHECK (recipient_type IN ('admin', 'super_admin', 'student')),
    content        TEXT        NOT NULL,
    item_id        TEXT,
    claim_id       TEXT,
    is_read        BOOLEAN     NOT NULL DEFAULT FALSE,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_messages_recipient_id   ON messages(recipient_id);
CREATE INDEX IF NOT EXISTS idx_messages_sender_id      ON messages(sender_id);
CREATE INDEX IF NOT EXISTS idx_messages_is_read        ON messages(is_read);
CREATE INDEX IF NOT EXISTS idx_messages_created_at     ON messages(created_at DESC);

-- =====================================================================
-- TABLE: audit_logs
-- =====================================================================
CREATE TABLE IF NOT EXISTS audit_logs (
    id        TEXT        PRIMARY KEY DEFAULT gen_random_uuid()::TEXT,
    action    TEXT        NOT NULL,
    item_id   TEXT,
    user_id   TEXT,
    user_role TEXT,
    reason    TEXT,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_logs_item_id   ON audit_logs(item_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id   ON audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp ON audit_logs(timestamp DESC);

-- =====================================================================
-- ROW LEVEL SECURITY (RLS)
-- All tables: enable RLS but grant full access via service_role key only.
-- The backend uses the service_role key so all operations go through.
-- =====================================================================

ALTER TABLE admins     ENABLE ROW LEVEL SECURITY;
ALTER TABLE students   ENABLE ROW LEVEL SECURITY;
ALTER TABLE items      ENABLE ROW LEVEL SECURITY;
ALTER TABLE claims     ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages   ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;

-- Allow the service role (used by backend) full access to every table
CREATE POLICY "service_role_all_admins"     ON admins     FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "service_role_all_students"   ON students   FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "service_role_all_items"      ON items      FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "service_role_all_claims"     ON claims     FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "service_role_all_messages"   ON messages   FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "service_role_all_audit_logs" ON audit_logs FOR ALL USING (true) WITH CHECK (true);
