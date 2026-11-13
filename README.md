# AI-Powered_Waste_Sorting_and_Recycling_Assistant_Team_26
Python Compact Course Capstone Project

## Subsystem 3: Image Classifier & Object Detector (Azam Rahmani)

Answers three questions for every uploaded photo: **what is it, where is it, and how sure are we.**
Two pretrained, zero-shot models from Hugging Face, so no training is needed:

| Class | Model | Returns |
|---|---|---|
| `WasteClassifier` | CLIP `openai/clip-vit-base-patch32` | one label per photo (used by the web app) |
| `WasteDetector` | OWL-ViT `google/owlvit-base-patch32` | every item with a bounding box `[x, y, width, height]` |

The 23 labels are exactly item labels of `data/waste_guidance.json`, so a predicted label goes
straight into `DatabaseManager.get_rule(label)`.

```python
from classifier import WasteClassifier

classifier = WasteClassifier()
classifier.warm_up()                     # once at app start (downloads ~600 MB the first time)
result = classifier.classify(image_bytes)
# {"status": "completed", "label": "glass jar", "category": "recyclable",
#  "confidence": 0.92, "message": "", "inference_ms": 140.3}
```

| status | meaning | web app (`app.py`) |
|---|---|---|
| `completed` | confident prediction (confidence >= 0.5) | result shown and saved |
| `uncertain` | low confidence | result shown and saved as uncertain |
| `invalid_image` | empty, broken, too large or unsupported file | 400 with the message |
| `error` | the model failed | 503 "Classification service unavailable" |

The classifier never raises: `ClassifierErrorHandler` (`classifier/exceptions.py`) turns every
exception into one of these statuses, logs unexpected errors and hides internal details.
Images stay in memory and are never saved to disk.

```mermaid
classDiagram
    class WasteClassifier {
        +confidence_threshold
        +warm_up()
        +classify(image) dict
    }
    class WasteDetector {
        +detection_threshold
        +detect_dict(image) dict
    }
    class ImagePreprocessor {
        +validate(image)
        +preprocess(image)
    }
    class CategoryMapper {
        +label_to_category
        +map_category(label) str
    }
    class ClassifierModel {
        <<abstract>>
        +predict(image)
    }
    class DetectionModel {
        <<abstract>>
        +detect(image)
    }
    class ClassifierErrorHandler {
        +to_status(exc)
        +to_response(exc)
    }
    ClassifierModel <|-- ZeroShotClipModel
    DetectionModel <|-- ZeroShotOwlVitModel
    WasteClassifier --> ImagePreprocessor
    WasteClassifier --> ClassifierModel
    WasteClassifier --> CategoryMapper
    WasteClassifier --> ClassifierErrorHandler
    WasteDetector --> ImagePreprocessor
    WasteDetector --> DetectionModel
    WasteDetector --> CategoryMapper
    WasteDetector --> ClassifierErrorHandler
```

**Setup:** `pip install -r requirements.txt` (torch and transformers are only needed for real
predictions; without them `app.py` falls back to a placeholder result).
**Try one photo:** `python scripts/classify_image.py photo.jpg` ·
**Accuracy on a photo folder:** `python scripts/evaluate.py test_images/`
**Tests:** `tests/test_preprocessor.py`, `test_category_mapper.py`, `test_waste_classifier.py`,
`test_waste_detector.py`, `test_evaluator.py`, `test_classifier_errors.py`, `test_classifier_api.py`
(84 tests, fake models, no download). Details: [docs/CLASSIFIER.md](docs/CLASSIFIER.md).

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
| `docs/class_diagram_data.png`, `.puml` | UML class diagram of this subsystem (matches the code) |

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
`POST /ask`, `GET /dashboard` (Kanika's HTML dashboard page, built on `get_stats()`).

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
Useful URLs: `/` (upload a photo), `/dashboard` (municipality dashboard).

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
python -m pytest -q                   # 67 tests for the whole project (33 are Ha's: database + AI, mocked)
python -m pytest -q --cov=database    # coverage for Ha's part
python demo_data_management.py        # classes + database
python demo_ai_guidance.py            # AI explanation, cache and fallback
```
