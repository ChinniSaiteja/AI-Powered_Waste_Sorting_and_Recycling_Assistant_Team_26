# Database Design – Team 26 (Waste Sorting & Recycling Assistant)

**Owner:** Ha Le Thu – Subsystem 4: Data Management & AI Guidance
**DBMS:** SQLite (file `database/waste.db`, created automatically, nothing to install)
**Schema:** `database/schema_sqlite.sql` (applied automatically by `DatabaseManager.initialize()`)
**Rule:** all SQL lives in `database/db.py` (`DatabaseManager`). Other subsystems never write SQL – they call `DatabaseManager` methods.

Kept deliberately simple: no admin accounts, no "wrong result" feedback and no AI chat
box, because nobody on the team uses those yet. Less for everyone to read and explain.

---

## 1. Overview (6 tables)

```
waste_categories 1 ──< waste_items 1 ──< disposal_rules
                            │
                            ├──< classifications
                            │
                            └──< ai_guidance

ai_usage_log  (stand-alone, one row per day)
```

| # | Table | What it stores | Written by | Read by |
|---|-------|----------------|------------|---------|
| 1 | `waste_categories` | recyclable / compostable / landfill | Ha Le Thu (seed, fixed) | Everyone |
| 2 | `waste_items` | Every label the classifier can return | Ha Le Thu (seed) | Backend |
| 3 | `disposal_rules` | Bin + instruction per item and region | Ha Le Thu (seed) | Backend → Web |
| 4 | `classifications` | One row per analysed photo (no image!) | Backend | Dashboard |
| 5 | `ai_guidance` | Cached AI explanations | Ha Le Thu (GuidanceService) | Backend → Web |
| 6 | `ai_usage_log` | AI calls per day | Ha Le Thu (GuidanceService) | Ha Le Thu (daily limit) |

---

## 2. Tables in detail

### 1. `waste_categories`
| Column | Type | Notes |
|---|---|---|
| id | INT PK | |
| name | VARCHAR(20) UNIQUE | **only** `recyclable`, `compostable`, `landfill` |
| description | VARCHAR(255) | |

### 2. `waste_items`
| Column | Type | Notes |
|---|---|---|
| id | INT PK | |
| category_id | INT FK → waste_categories | |
| label | VARCHAR(100) UNIQUE | **must match the classifier label exactly** (lowercase, e.g. `glass jar`) |
| is_deposit | BOOLEAN | `TRUE` = Pfand bottle → return to store |

### 3. `disposal_rules`
| Column | Type | Notes |
|---|---|---|
| id | INT PK | |
| item_id | INT FK → waste_items | |
| region | VARCHAR(50) | MVP: only `Dortmund`; more cities = more rows, no code change |
| bin_type | VARCHAR(100) | e.g. `Glass container`, `Biotonne (brown bin)` |
| instruction | TEXT | short text shown to the user |
| updated_at | DATETIME | auto-updated |

Constraint: `UNIQUE (item_id, region)` → one rule per item per region.

### 4. `classifications`
| Column | Type | Notes |
|---|---|---|
| id | INT PK | |
| item_id | INT FK → waste_items, NULL | NULL when the label is not in our DB |
| predicted_label | VARCHAR(100) | raw label from the classifier |
| confidence | DECIMAL(5,4), NULL | 0–1 (e.g. `0.9200`), NULL if not available |
| status | VARCHAR(20) | `completed` / `uncertain` / `failed` |
| region | VARCHAR(50) | region selected by the user |
| created_at | DATETIME | |

Privacy: **no image or image path is stored**, only the result.

### 5. `ai_guidance`
| Column | Type | Notes |
|---|---|---|
| id | INT PK | |
| item_id | INT FK → waste_items | |
| answer | TEXT | AI explanation for that item (shown as "AI-generated") |
| created_at | DATETIME | |

Before calling the AI we check this table first (cache) → lower cost and faster.

### `ai_usage_log`
| Column | Type | Notes |
|---|---|---|
| id | INT PK | |
| usage_date | DATE UNIQUE | |
| request_count | INT | +1 per AI call; stop when the daily limit is reached |

---

## 3. How other subsystems use the database

All access goes through `DatabaseManager` (and `GuidanceService` for AI).

| Who | Method | Returns |
|---|---|---|
| **Backend (Sai Teja)** | `get_rule(label, region="Dortmund")` | `{"label", "category", "is_deposit", "region", "bin_type", "instruction"}` or `None` |
| **Backend** | `save_classification(label, confidence, status, region)` | new `classification_id` |
| **Backend** | `GuidanceService.explain(label, region, rule=None)` | `{"explanation", "source": "cache"/"ai"/"fallback", "ai_generated"}` |
| **Dashboard (Kanika)** | `get_stats(region, date_from=None, date_to=None, top_n=5)` | see below; `region=None` = all regions |
| **Dashboard (Kanika)** | `get_classification_records(region, limit=50)` | latest results, newest first (see below) |
| **Classifier (Azam)** | `get_all_items()` | list of the 72 known labels → classifier labels must match these |

### `get_stats()` result (for Plotly charts)
```json
{
  "region": "Dortmund",
  "total_items": 124,
  "by_category": {"recyclable": 80, "compostable": 30, "landfill": 14},
  "category_percentages": {"recyclable": 64.5, "compostable": 24.2, "landfill": 11.3},
  "recycling_rate": 0.645,
  "per_day": [{"date": "2026-11-04", "count": 12}],
  "top_items": [{"label": "plastic bottle", "waste_name": "Plastic bottle", "count": 22}],
  "region_counts": {"Dortmund": 124},
  "uncertain_count": 9
}
```
`recycling_rate` is 0-1. `category_percentages` (0-100) only count items with a known
category, so they add up to 100.

### `get_classification_records()` result (table on the dashboard)
```json
[{
  "id": 42, "waste_name": "Plastic bottle", "label": "plastic bottle",
  "category": "recyclable", "confidence": 0.94,
  "bin_type": "Pfand - return to store",
  "disposal_instruction": "Bottles with the Pfand logo: return to any supermarket machine ...",
  "explanation": "Most plastic bottles in Germany carry a deposit ...",
  "is_deposit": true, "status": "completed", "region": "Dortmund",
  "created_at": "2026-11-12 10:15:00"
}]
```
`explanation` is the cached AI explanation of the item (`null` if the AI has not answered
for this item yet). `category` and `bin_type` are `null` for labels that are not in the database.

### Flask routes (`web_interface_dashboard/app.py`)
| Route | Purpose |
|---|---|
| `POST /analyse` | upload image → classifier → rule + AI explanation (`GuidanceService.explain`) → saved |
| `GET /dashboard` | Kanika's HTML dashboard, built from `get_stats()` via `MunicipalityDashboard` |

There is no separate JSON API for the dashboard numbers; `get_stats()` and
`get_classification_records()` can still be called directly in Python (see below)
if a JSON endpoint is needed later.

Errors are returned as `{"status": "error", "error": "INVALID_DATA" / "NOT_FOUND", "message": ...}`
with HTTP 400 / 404 (from `database/exceptions.py`).

### Example SQL behind it
```sql
-- items per category
SELECT c.name, COUNT(*) AS total
FROM classifications cl
JOIN waste_items w      ON w.id = cl.item_id
JOIN waste_categories c ON c.id = w.category_id
WHERE cl.region = 'Dortmund'
GROUP BY c.name;

-- items per day
SELECT DATE(created_at) AS day, COUNT(*) AS total
FROM classifications
WHERE region = 'Dortmund'
GROUP BY DATE(created_at)
ORDER BY day;
```

---

## 4. Agreements we need from the team

1. **Azam:** send the final list of classifier labels (lowercase, English). Each label must exist in `waste_items`.
2. **Sai Teja:** confidence is sent as a float 0–1 (not 0–100); status is one of `completed / uncertain / failed`.
3. **Kanika:** dashboard uses the `get_stats()` and `get_classification_records()` JSON above – tell Ha if you need another chart.
4. **Classifier statuses:** `completed` and `uncertain` are saved; `invalid_image` (HTTP 400) and `error` (HTTP 503) are not saved.
5. **Everyone:** the AI key goes in `.env` (never pushed to GitHub).

### AI settings (`.env`)
| Variable | Default | Meaning |
|---|---|---|
| `AI_API_KEY` (or `OPENAI_API_KEY`) | – | no key → fallback text (official rule) |
| `AI_BASE_URL` | empty = OpenAI | e.g. `https://generativelanguage.googleapis.com/v1beta/openai/` for free Gemini |
| `AI_MODEL` | `gpt-4o-mini` | e.g. `gemini-3.5-flash-lite` |
| `AI_DAILY_LIMIT` | 200 | AI calls per day (table `ai_usage_log`) |
| `AI_TIMEOUT` | 8 | seconds; no retries, then fallback |
| `AI_MAX_TOKENS` | 1500 | room for "thinking" models |

---

## 5. Quick start for teammates

```bash
pip install -r requirements.txt
cp .env.example .env                          # nothing else to set up for SQLite
python demo_data_management.py                # creates the database and loads 72 Dortmund rules
```

In your own code:
```python
from database.db import DatabaseManager
db = DatabaseManager()
db.initialize()                                   # safe to call every start
db.get_rule("glass jar")                          # disposal guidance
db.save_classification("glass jar", 0.92)         # returns classification_id
db.get_stats("Dortmund")                          # dashboard data
```
No manual SQL import is needed - tables and data are created automatically.

---

## 6. Not built (on purpose, for the MVP)

These were considered but left out, because nobody on the team uses them yet.
Could be added later without changing the rest of the schema:

- **Admin accounts / login** to edit rules from a web page.
- **"Wrong result?" feedback** from users.
- **AI chat box** for follow-up questions on the result page.
- **MySQL support.** The team only runs SQLite, so the extra engine-switching
  code was removed to keep `database/db.py` simpler to read.
