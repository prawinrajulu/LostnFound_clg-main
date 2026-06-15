-- =============================================================================
-- Campus Lost & Found — Supabase PostgreSQL Schema
-- Generated from server.py field usage
-- Run this in the Supabase SQL Editor (Dashboard → SQL Editor → New Query)
-- =============================================================================

-- Enable UUID extension (already enabled in Supabase by default)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =============================================================================
-- 1. admins
-- =============================================================================
CREATE TABLE IF NOT EXISTS admins (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username      TEXT NOT NULL UNIQUE,
    password      TEXT NOT NULL,                          -- bcrypt hash
    full_name     TEXT NOT NULL,
    role          TEXT NOT NULL DEFAULT 'admin'
                      CHECK (role IN ('admin', 'super_admin')),
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by    UUID REFERENCES admins(id) ON DELETE SET NULL  -- NULL for super_admin (self-seeded)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_admins_username    ON admins (username);
CREATE INDEX IF NOT EXISTS idx_admins_role        ON admins (role);
CREATE INDEX IF NOT EXISTS idx_admins_created_at  ON admins (created_at ASC);

-- =============================================================================
-- 2. students
-- =============================================================================
CREATE TABLE IF NOT EXISTS students (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    roll_number     TEXT NOT NULL UNIQUE,
    full_name       TEXT NOT NULL,
    department      TEXT NOT NULL,
    year            TEXT NOT NULL,
    dob             TEXT NOT NULL,                        -- stored as DD-MM-YYYY string
    email           TEXT NOT NULL,
    phone_number    TEXT NOT NULL,
    profile_picture TEXT,                                 -- relative URL e.g. /uploads/profiles/...
    admin_notes     JSONB NOT NULL DEFAULT '[]'::JSONB,   -- array of {id, note, added_by, added_at}
    is_deleted      BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_date    DATE,                                 -- YYYY-MM-DD (redundant convenience column)
    created_time    TIME                                  -- HH:MM:SS  (redundant convenience column)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_students_roll_number  ON students (roll_number);
CREATE INDEX IF NOT EXISTS idx_students_is_deleted   ON students (is_deleted);
CREATE INDEX IF NOT EXISTS idx_students_created_at   ON students (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_students_department   ON students (department);

-- =============================================================================
-- 3. items
-- =============================================================================
CREATE TABLE IF NOT EXISTS items (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    item_type     TEXT NOT NULL CHECK (item_type IN ('lost', 'found')),
    description   TEXT NOT NULL,
    location      TEXT NOT NULL,
    image_url     TEXT NOT NULL,                          -- relative URL e.g. /uploads/items/...
    student_id    UUID NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    status        TEXT NOT NULL DEFAULT 'active'
                      CHECK (status IN ('active', 'claimed', 'resolved')),
    is_deleted    BOOLEAN NOT NULL DEFAULT FALSE,
    delete_reason TEXT,
    deleted_at    TIMESTAMPTZ,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_date  DATE,                                   -- redundant convenience column
    created_time  TIME,                                   -- redundant convenience column
    likes         INTEGER NOT NULL DEFAULT 0 CHECK (likes >= 0),
    dislikes      INTEGER NOT NULL DEFAULT 0 CHECK (dislikes >= 0),
    liked_by      JSONB NOT NULL DEFAULT '[]'::JSONB,     -- array of student UUIDs
    disliked_by   JSONB NOT NULL DEFAULT '[]'::JSONB      -- array of student UUIDs
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_items_student_id   ON items (student_id);
CREATE INDEX IF NOT EXISTS idx_items_item_type    ON items (item_type);
CREATE INDEX IF NOT EXISTS idx_items_status       ON items (status);
CREATE INDEX IF NOT EXISTS idx_items_is_deleted   ON items (is_deleted);
CREATE INDEX IF NOT EXISTS idx_items_created_at   ON items (created_at DESC);
-- Composite: most common admin query
CREATE INDEX IF NOT EXISTS idx_items_type_deleted ON items (item_type, is_deleted);
CREATE INDEX IF NOT EXISTS idx_items_deleted_at   ON items (deleted_at DESC) WHERE is_deleted = TRUE;

-- =============================================================================
-- 4. claims
-- =============================================================================
CREATE TABLE IF NOT EXISTS claims (
    id                     UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    item_id                UUID NOT NULL REFERENCES items(id) ON DELETE CASCADE,
    claimant_id            UUID NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    message                TEXT NOT NULL DEFAULT '',
    status                 TEXT NOT NULL DEFAULT 'pending'
                               CHECK (status IN ('pending', 'under_review', 'approved', 'rejected')),
    verification_questions JSONB NOT NULL DEFAULT '[]'::JSONB,  -- [{id, question, asked_by, asked_at}]
    verification_answers   JSONB NOT NULL DEFAULT '[]'::JSONB,  -- [{id, answer, answered_at}]
    admin_notes            TEXT NOT NULL DEFAULT '',
    created_at             TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_claims_item_id      ON claims (item_id);
CREATE INDEX IF NOT EXISTS idx_claims_claimant_id  ON claims (claimant_id);
CREATE INDEX IF NOT EXISTS idx_claims_status       ON claims (status);
CREATE INDEX IF NOT EXISTS idx_claims_created_at   ON claims (created_at DESC);
-- Prevent duplicate active claims per (item, claimant):
CREATE UNIQUE INDEX IF NOT EXISTS idx_claims_unique_active
    ON claims (item_id, claimant_id)
    WHERE status IN ('pending', 'under_review');

-- =============================================================================
-- 5. messages
-- =============================================================================
CREATE TABLE IF NOT EXISTS messages (
    id             UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    sender_id      UUID NOT NULL,                         -- admin.id or student.id (polymorphic)
    sender_type    TEXT NOT NULL CHECK (sender_type IN ('admin', 'super_admin', 'student')),
    recipient_id   UUID NOT NULL,                         -- admin.id or student.id (polymorphic)
    recipient_type TEXT NOT NULL CHECK (recipient_type IN ('admin', 'super_admin', 'student')),
    content        TEXT NOT NULL,
    item_id        UUID REFERENCES items(id) ON DELETE SET NULL,
    claim_id       UUID REFERENCES claims(id) ON DELETE SET NULL,
    is_read        BOOLEAN NOT NULL DEFAULT FALSE,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_messages_recipient_id    ON messages (recipient_id);
CREATE INDEX IF NOT EXISTS idx_messages_sender_id       ON messages (sender_id);
CREATE INDEX IF NOT EXISTS idx_messages_item_id         ON messages (item_id);
CREATE INDEX IF NOT EXISTS idx_messages_claim_id        ON messages (claim_id);
CREATE INDEX IF NOT EXISTS idx_messages_created_at      ON messages (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_messages_recipient_unread
    ON messages (recipient_id, is_read)
    WHERE is_read = FALSE;

-- =============================================================================
-- 6. audit_logs
-- =============================================================================
CREATE TABLE IF NOT EXISTS audit_logs (
    id        UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    action    TEXT NOT NULL,            -- e.g. 'item_created', 'item_soft_deleted', 'item_restored', 'item_permanent_deleted'
    item_id   UUID REFERENCES items(id) ON DELETE SET NULL,
    user_id   UUID NOT NULL,           -- admin.id or student.id (polymorphic)
    user_role TEXT NOT NULL,           -- 'admin', 'super_admin', 'student'
    reason    TEXT,                    -- populated for soft-delete actions
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_audit_logs_item_id   ON audit_logs (item_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id   ON audit_logs (user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_action    ON audit_logs (action);
CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp ON audit_logs (timestamp DESC);

-- =============================================================================
-- Row Level Security (RLS)
-- Supabase enables RLS by default. The backend uses the service-role key
-- which bypasses RLS. The policies below lock down direct client access.
-- =============================================================================

ALTER TABLE admins      ENABLE ROW LEVEL SECURITY;
ALTER TABLE students    ENABLE ROW LEVEL SECURITY;
ALTER TABLE items       ENABLE ROW LEVEL SECURITY;
ALTER TABLE claims      ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages    ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs  ENABLE ROW LEVEL SECURITY;

-- Service role bypasses all RLS — no additional policies needed for backend.
-- If you ever expose these tables directly via the anon/authenticated Supabase
-- client, add fine-grained policies here.
