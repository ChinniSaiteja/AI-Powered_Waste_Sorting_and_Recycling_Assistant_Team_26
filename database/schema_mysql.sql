-- =====================================================================
-- AI-Powered Waste Sorting & Recycling Assistant - Team 26
-- Subsystem 4: Data Management & AI Guidance (owner: Ha Le Thu)
-- Database schema (MySQL 8)
-- Run:  created automatically by DatabaseManager.initialize()
-- =====================================================================

-- (the database itself is created by DatabaseManager from DB_NAME in .env)

-- ---------------------------------------------------------------------
-- 1. admin_users : municipal staff who log in to the dashboard
--                  and edit disposal rules
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS admin_users (
  id             INT AUTO_INCREMENT PRIMARY KEY,
  username       VARCHAR(50)  NOT NULL UNIQUE,
  password_hash  VARCHAR(255) NOT NULL,          -- never store plain passwords
  region         VARCHAR(50)  NOT NULL DEFAULT 'Dortmund',
  created_at     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ---------------------------------------------------------------------
-- 2. waste_categories : the 3 classifier categories
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS waste_categories (
  id           INT AUTO_INCREMENT PRIMARY KEY,
  name         VARCHAR(20)  NOT NULL UNIQUE,      -- recyclable | compostable | landfill
  description  VARCHAR(255)
);

-- ---------------------------------------------------------------------
-- 3. waste_items : every label the classifier can return
--    label MUST be identical to the classifier output (lowercase)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS waste_items (
  id           INT AUTO_INCREMENT PRIMARY KEY,
  category_id  INT          NOT NULL,
  label        VARCHAR(100) NOT NULL UNIQUE,      -- e.g. 'glass jar'
  is_deposit   BOOLEAN      NOT NULL DEFAULT FALSE, -- Pfand: return to store
  FOREIGN KEY (category_id) REFERENCES waste_categories(id)
);

-- ---------------------------------------------------------------------
-- 4. disposal_rules : which bin + instruction, per item and region
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS disposal_rules (
  id           INT AUTO_INCREMENT PRIMARY KEY,
  item_id      INT          NOT NULL,
  region       VARCHAR(50)  NOT NULL DEFAULT 'Dortmund',
  bin_type     VARCHAR(100) NOT NULL,             -- e.g. 'Glass container'
  instruction  TEXT         NOT NULL,
  updated_by   INT          NULL,                 -- admin who last edited
  updated_at   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP
                            ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uq_rule_item_region (item_id, region), -- one rule per item per region
  FOREIGN KEY (item_id)    REFERENCES waste_items(id),
  FOREIGN KEY (updated_by) REFERENCES admin_users(id) ON DELETE SET NULL
);

-- ---------------------------------------------------------------------
-- 5. classifications : one row per photo analysed (no image stored!)
--    -> main source for the dashboard
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS classifications (
  id               INT AUTO_INCREMENT PRIMARY KEY,
  item_id          INT          NULL,             -- NULL if label unknown to DB
  predicted_label  VARCHAR(100) NOT NULL,         -- raw classifier label
  confidence       DECIMAL(5,4) NULL,             -- 0.0000 - 1.0000, NULL if not available
  status           VARCHAR(20)  NOT NULL DEFAULT 'completed', -- completed | uncertain | failed
  region           VARCHAR(50)  NOT NULL DEFAULT 'Dortmund',
  created_at       DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_class_region_date (region, created_at),
  FOREIGN KEY (item_id) REFERENCES waste_items(id)
);

-- ---------------------------------------------------------------------
-- 6. user_feedback : "Wrong result?" button (max 1 per classification)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS user_feedback (
  id                 INT AUTO_INCREMENT PRIMARY KEY,
  classification_id  INT          NOT NULL UNIQUE,
  is_correct         BOOLEAN      NOT NULL,
  correct_label      VARCHAR(100) NULL,           -- what the user says it really is
  created_at         DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (classification_id) REFERENCES classifications(id) ON DELETE CASCADE
);

-- ---------------------------------------------------------------------
-- 7. ai_guidance : cache of OpenAI answers (saves cost + time)
--    question = NULL  -> default explanation for the item
--    question = text  -> user follow-up question
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ai_guidance (
  id          INT AUTO_INCREMENT PRIMARY KEY,
  item_id     INT          NOT NULL,
  question    VARCHAR(500) NULL,
  answer      TEXT         NOT NULL,
  created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (item_id) REFERENCES waste_items(id)
);

-- ---------------------------------------------------------------------
-- 8. ai_usage_log : OpenAI calls per day (daily limit = cost control)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ai_usage_log (
  id             INT AUTO_INCREMENT PRIMARY KEY,
  usage_date     DATE NOT NULL UNIQUE,
  request_count  INT  NOT NULL DEFAULT 0
);
