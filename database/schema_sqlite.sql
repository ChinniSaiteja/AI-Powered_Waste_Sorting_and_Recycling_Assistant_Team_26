-- =====================================================================
-- AI-Powered Waste Sorting & Recycling Assistant - Team 26
-- Subsystem 4: Data Management & AI Guidance (owner: Ha Le Thu)
-- Database schema (SQLite) - same 8 tables as schema_mysql.sql
-- Created automatically by DatabaseManager.initialize()
-- =====================================================================

CREATE TABLE IF NOT EXISTS admin_users (
  id             INTEGER PRIMARY KEY AUTOINCREMENT,
  username       TEXT     NOT NULL UNIQUE,
  password_hash  TEXT     NOT NULL,
  region         TEXT     NOT NULL DEFAULT 'Dortmund',
  created_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS waste_categories (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  name         TEXT NOT NULL UNIQUE,
  description  TEXT
);

CREATE TABLE IF NOT EXISTS waste_items (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  category_id  INTEGER NOT NULL REFERENCES waste_categories(id),
  label        TEXT    NOT NULL UNIQUE,
  is_deposit   BOOLEAN NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS disposal_rules (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  item_id      INTEGER  NOT NULL REFERENCES waste_items(id),
  region       TEXT     NOT NULL DEFAULT 'Dortmund',
  bin_type     TEXT     NOT NULL,
  instruction  TEXT     NOT NULL,
  updated_by   INTEGER  NULL REFERENCES admin_users(id) ON DELETE SET NULL,
  updated_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (item_id, region)
);

CREATE TABLE IF NOT EXISTS classifications (
  id               INTEGER PRIMARY KEY AUTOINCREMENT,
  item_id          INTEGER  NULL REFERENCES waste_items(id),
  predicted_label  TEXT     NOT NULL,
  confidence       REAL     NULL,
  status           TEXT     NOT NULL DEFAULT 'completed',
  region           TEXT     NOT NULL DEFAULT 'Dortmund',
  created_at       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_class_region_date ON classifications (region, created_at);

CREATE TABLE IF NOT EXISTS user_feedback (
  id                 INTEGER PRIMARY KEY AUTOINCREMENT,
  classification_id  INTEGER  NOT NULL UNIQUE REFERENCES classifications(id) ON DELETE CASCADE,
  is_correct         BOOLEAN  NOT NULL,
  correct_label      TEXT     NULL,
  created_at         DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ai_guidance (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  item_id     INTEGER  NOT NULL REFERENCES waste_items(id),
  question    TEXT     NULL,
  answer      TEXT     NOT NULL,
  created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ai_usage_log (
  id             INTEGER PRIMARY KEY AUTOINCREMENT,
  usage_date     DATE    NOT NULL UNIQUE,
  request_count  INTEGER NOT NULL DEFAULT 0
);
