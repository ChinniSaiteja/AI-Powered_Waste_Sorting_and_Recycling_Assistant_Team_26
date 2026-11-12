# AI-Powered_Waste_Sorting_and_Recycling_Assistant_Team_26
Python Compact Course Capstone Project

## Subsystem 4: Data Management & AI Guidance (Ha Le Thu)

Stores every classification result, the Dortmund disposal rules and the AI answers,
and gives the statistics for the municipality dashboard. Full details: [docs/DATABASE.md](docs/DATABASE.md).

| File | Purpose |
|------|---------|
| `database/db.py` | `DatabaseManager`, the only file with SQL (SQLite or MySQL, 8 tables) |
| `database/models.py` | `WasteCategory`, `WasteItem`, `DisposalRule` (encapsulation, validation) |
| `database/exceptions.py` | `DataManagementError`, `InvalidDataError`, `ItemNotFoundError`, `DatabaseConnectionError` |
| `database/guidance.py` | `GuidanceService`: AI explanation and follow-up questions, with cache, daily limit and fallback |
| `database/schema_sqlite.sql`, `schema_mysql.sql` | Database schema |
| `data/waste_guidance.json` | 72 Dortmund rules; labels match the classifier labels exactly |
| `demo_data_management.py`, `demo_ai_guidance.py`, `demo_dashboard_data.py` | Demos |
| `tests/` | Unit tests (AI is mocked) |

### API for the other subsystems

```python
from database.db import DatabaseManager
from database.guidance import GuidanceService

db = DatabaseManager()
db.initialize()                                   # tables + Dortmund rules
ai = GuidanceService(db)

# Backend (Sai) - after the classifier (Azi) returns a result
rule = db.get_rule("glass jar")                   # bin_type, instruction, category, is_deposit
text = ai.explain("glass jar", rule=rule)         # {"explanation", "source", "ai_generated"}
cid = db.save_classification("glass jar", 0.92, status="completed")
db.save_feedback(cid, is_correct=False, correct_label="glass bottle")
ai.ask("Do I need to wash it?", label="glass jar")  # {"answer", "source", "ai_generated"}

# Dashboard (Kanika)
db.get_classification_records(region="Dortmund", limit=50)   # newest first, region=None -> all
db.get_stats(region="Dortmund")
```

`get_stats()` returns `total_items`, `by_category`, `category_percentages`,
`recycling_rate` (0-1), `per_day`, `top_items`, `region_counts`,
`uncertain_count` and `wrong_feedback_count`.

Flask routes in `web_interface_dashboard/app.py`: `POST /analyse`, `POST /feedback`,
`POST /ask`, `GET /api/dashboard/stats?region=Dortmund|all`,
`GET /api/dashboard/records?region=...&limit=50`.

### Setup

```bash
python3 -m venv venv
source venv/bin/activate              # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                  # then add your AI key (see below)
```

### Run

```bash
python demo_dashboard_data.py         # optional: 200 example results for the dashboard
cd web_interface_dashboard
flask --app app run --port 5050       # open http://127.0.0.1:5050
```

On macOS port 5000 is often used by AirPlay Receiver, so we use port 5050.
Useful URLs: `/api/dashboard/stats`, `/api/dashboard/stats?region=all`,
`/api/dashboard/records?limit=10`.

### Database file

`database/waste.db` is created automatically on the first start (8 tables + 72 Dortmund rules
from `data/waste_guidance.json`). It is not committed to Git.
To load changed rules from the JSON file, delete `database/waste.db` and start again.
To use MySQL instead, set `DB_ENGINE=mysql` and the `DB_*` values in `.env`.

### AI key (free option)

Without an AI key the app still works: it shows the official rule as explanation.
For real AI answers, put a key in `.env`. Free option with Google Gemini:

1. Create a key at <https://aistudio.google.com> (Get API key, no credit card needed).
2. In `.env`:
   ```
   AI_API_KEY=your-gemini-key
   AI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
   AI_MODEL=gemini-3.5-flash-lite
   ```

For OpenAI: set `AI_API_KEY` to the OpenAI key, leave `AI_BASE_URL` empty and use `AI_MODEL=gpt-4o-mini`.
Never commit `.env`. Only the item label, region, rule text and the user's question are sent
to the AI, never images.

### Tests and demos

```bash
python -m pytest -q                   # 20 unit tests, AI is mocked (no key needed)
python -m pytest -q --cov=database    # with coverage
python demo_data_management.py        # classes + database
python demo_ai_guidance.py            # AI explanation, cache and fallback
```
