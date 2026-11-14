# AI-Powered_Waste_Sorting_and_Recycling_Assistant_Team_26
Python Compact Course Capstone Project


## Subsystem: Web Interface & Municipality Dashboard

**Location:** `web_interface_dashboard/`
## Overview

**Develops the web interface that lets citizens upload or photograph a waste item and see its classification, disposal instruction and AI explanation, and the municipality dashboard that summarises all stored classifications.**

---

### Responsibilities

- **Image upload:** users choose an existing image from their device (*Upload from Gallery*) or take a new photo with their phone camera (*Take a Photo*).
- **Upload validation:** checks that an image is present, not empty, at most 10 MB and of type PNG, JPG or JPEG before it is sent to the classifier.
- **Result display:** shows the waste name, category, confidence, disposal instruction and educational explanation, or a clear error message.
- **Municipality dashboard:** shows the number of analysed items, the share classified as recyclable and the distribution across the three waste categories, calculated from the stored classification records.

---

### Folder Structure

```
web_interface_dashboard/
├── app.py                              # Flask app: routes and connection of all subsystems
├── web_interface/
│   ├── waste_upload_view.py            # WasteUploadView
│   ├── analysis_controller.py          # AnalysisController
│   ├── classification_result_view.py   # ClassificationResultView, WasteCategory
│   └── exceptions.py                   # error classes of this subsystem
├── dashboard/
│   └── municipality_dashboard.py       # MunicipalityDashboard
├── templates/
│   ├── index.html                      # upload and result page
│   └── dashboard.html                  # municipality dashboard page
└── static/
    ├── css/                            # style.css, dashboard.css
    └── js/                             # script.js (upload, preview, result display)

tests/
└── test_web_interface.py               # automated tests for this subsystem
```

---

### How It Works

```
Upload page ──► AnalysisController (validate) ──► Classifier (Subsystem 3)
                                                      │
                                                      ▼
Result page ◄── ClassificationResultView ◄── Disposal rule + AI explanation (Subsystem 4)
                                                      │
                                                      ▼web
                                                
Dashboard   ◄── MunicipalityDashboard     ◄── Stored classification results (database)
```

1. The user selects or takes a photo on the upload page.
2. `WasteUploadView` stores the image and its details (name, size, type).
3. `AnalysisController` validates the upload (image present, allowed file type).
4. The classifier recognises the item; the database provides the disposal rule and `GuidanceService` the AI explanation.
5. `ClassificationResultView` validates the result and returns it to the page.
6. Every real classification is saved, so `MunicipalityDashboard` can show the statistics.

### Routes

| Route | Method | Description |
|---|---|---|
| `/` | GET | Upload page (`index.html`) |
| `/analyse` | POST | Receives the image (form field `image`) and returns the result as JSON |
| `/dashboard` | GET | Municipality dashboard (`dashboard.html`) |

---

### Screenshots

**Upload page:** choose an image from the gallery or take a photo.

![Upload page](docs/upload_page.png)

**Classification result:** waste category, disposal instruction and AI explanation.

![Classification result](docs/result.png)

**Municipality dashboard:** statistics from all stored classifications.

![Municipality dashboard](docs/dashboardd.png)

---

### Class Diagrams

#### Web Interface

![Web Interface class diagram](docs/class_diagram_web_interface.png)

#### Municipality Dashboard

![Municipality Dashboard class diagram](docs/class_diagram_municipality_dashboard.png)

---

### Classes

| Class | File | Responsibility | Main methods |
|---|---|---|---|
| `WasteUploadView` | `waste_upload_view.py` | Stores the selected image and its name, size, type and upload status. | `select_image(image)`, `submit_image()` |
| `AnalysisController` | `analysis_controller.py` | Validates the upload before classification and records the request status and errors. | `validate_upload(image, filename)`, `request_analysis(image, filename)`, `handle_error(message)` |
| `ClassificationResultView` | `classification_result_view.py` | Validates and stores one classification result and returns it for display, or returns an error message. | `display_result(result)`, `display_error(message)` |
| `WasteCategory` (Enum) | `classification_result_view.py` | The three waste categories used by the whole project. | `RECYCLABLE`, `COMPOSTABLE`, `LANDFILL` |
| `MunicipalityDashboard` | `municipality_dashboard.py` | Loads the statistics for a region once and prepares them for the dashboard page. | `load_data()`, `get_total_analysed_items()`, `get_recyclable_percentage()`, `get_category_distribution()` |

#### Object-Oriented Design

Every class follows the same structure:

1. **Constructor (`__init__`):** sets up the initial state, e.g. `WasteUploadView(max_size_bytes=10 MB)` or `MunicipalityDashboard(database_manager, region="Dortmund")`.
2. **Initialisation methods:** `initialize()` resets the object to its starting state and, where applicable, configures it (e.g. the accepted file types in `AnalysisController`). `to_dict()` returns the object's data for the web page. In `MunicipalityDashboard`, `load_data()` fetches the statistics from the database once.
3. **Encapsulation (getters & setters):** all attributes are private and accessed through `@property` getters. The setters validate their input, e.g. the confidence must be between 0 and 1, the category must be one of the `WasteCategory` values, and the upload status must be one of the known statuses.

---

### Error Handling

The subsystem has its own error classes in `web_interface/exceptions.py`:

```
WebInterfaceError            base class for all errors of this subsystem
├── InvalidUploadError       no image, empty file, file too large, invalid status
├── InvalidResultError       invalid result value, e.g. confidence outside 0-1
└── ImageRejectedError       the classifier could not use the image
```

The input errors also inherit from `ValueError`. Invalid uploads never crash the application: `WasteUploadView.select_image()` catches `InvalidUploadError`, sets the status to *Invalid Image* and stores the message.

The Flask app turns every problem into a clear JSON message:

| Situation | HTTP status | Message shown to the user |
|---|---|---|
| No image selected | 400 | Please select an image. |
| Empty or unusable image | 400 | Image upload failed. / message from the classifier |
| Wrong file type | 400 | Please upload a valid image file (PNG, JPG, JPEG). |
| File larger than 10 MB | 413 | File is too large. Maximum size is 10 MB. |
| Item has no disposal rule | 422 | This item could not be matched to a disposal rule. Please try another photo. |
| Classifier not available or failed | 503 | Classification service unavailable. |

---

### Testing

The subsystem is tested with **pytest** (`tests/test_web_interface.py`, 40 test cases):

| Test group | What is tested |
|---|---|
| `TestWasteUploadView` | Starting state, storing name/size/type, rewinding the file, submitting with and without an image, rejecting empty and too-large images, setter validation, `initialize()` |
| `TestAnalysisController` | Starting state, accepted file types (PNG, JPG, JPEG in any case), rejecting other types and missing images, `request_analysis()`, `handle_error()`, configuring allowed types, setter validation |
| `TestClassificationResultView` | Starting state, returned page data, conversion to `WasteCategory`, rejecting invalid categories / confidences / empty texts, replacing an old error, `display_error()` |
| `TestWebInterfaceExceptions` | Error class hierarchy, errors raised by the setters, stored error messages |

Run the tests from the project root:

```bash
python -m pytest tests/test_web_interface.py -v
```

---

### Setup and Running

**Requirements** (all listed in `requirements.txt`):

| Package | Needed for |
|---|---|
| `Flask` | Web application |
| `python-dotenv` | Reading the settings in `.env` |
| `torch`, `transformers`, `pillow` | Real image classification (Subsystem 3) |
| `openai` | AI explanations (Subsystem 4; works with Groq, Gemini or OpenAI) |
| `pytest` | Automated tests |

```bash
pip install -r requirements.txt
```

**Settings:** copy `.env.example` to `.env` in the project root and add an AI key (see the Data Management & AI Guidance section). Without a key the app still works and shows the official disposal rule instead of an AI explanation.

**Start the app** from the `web_interface_dashboard` folder:

```bash
python app.py
```

Then open:
- **http://127.0.0.1:5000** - upload page
- **http://127.0.0.1:5000/dashboard** - municipality dashboard

> On the first start, the classifier downloads its model (about 600 MB) once. Without `torch` and `transformers` the app still runs and uses placeholder results, which are not saved to the database.



## Subsystem 2: Backend & Application Integration
## Overview

The **Backend & Application Integration** subsystem is responsible for coordinating the communication between the web interface, ML image classifier, data management system, and AI guidance service.

It acts as the central orchestration layer of the application. It receives the uploaded image, sends it to the classifier, validates the classification result, requests disposal guidance, stores the classification result, and prepares the final structured response for the frontend.

## Responsibilities

The backend subsystem is responsible for:

- Receiving image data from the web interface.
- Communicating with the ML image classifier.
- Validating and normalizing classifier results.
- Handling invalid or unusable images.
- Requesting waste-disposal guidance for the classified item.
- Storing classification results through the database management subsystem.
- Combining classification and guidance information.
- Returning a structured response to the frontend.
- Handling integration errors between the different subsystems.

## Architecture

The main processing flow is:

```text
Web Interface
      |
      v
AnalysisService
      |
      +--------------------+
      |                    |
      v                    v
ML Classifier     ClassificationResultHandler
      |                    |
      |                    v
      |             Validated Result
      |                    |
      +----------->--------+
                   |
                   v
            GuidanceService
                   |
                   v
            DatabaseManager
                   |
                   v
          ResponseComposer
                   |
                   v
              Frontend
```

## Main Components

### `AnalysisService`

`AnalysisService` is the main orchestration component of the backend.

It coordinates the complete image-analysis workflow:

1. Receives the image data.
2. Sends the image to the ML classifier.
3. Passes the classifier result to `ClassificationResultHandler`.
4. Requests disposal guidance from `GuidanceService`.
5. Saves the classification through `DatabaseManager`.
6. Passes the collected information to `ResponseComposer`.
7. Returns the final response.

### `ClassificationResultHandler`

`ClassificationResultHandler` validates and normalizes the result received from the ML classifier.

It checks:

- Classification status.
- Waste label.
- Confidence score.
- Waste category.
- Region.

It also handles the `invalid_image` status when the uploaded image cannot be used for classification.

The default region is **Dortmund**.

### `ResponseComposer`

`ResponseComposer` combines the classification result, disposal guidance, and database classification ID into a structured response that can be returned to the frontend.

## Error Handling

The backend uses custom exceptions to handle integration failures:

```text
BackendError
├── ClassifierIntegrationError
├── InvalidImageError
├── InvalidClassificationResultError
├── GuidanceIntegrationError
└── ResponseCompositionError
```

This allows different types of failures to be identified and handled separately.

## Classifier Integration

The backend expects the ML classifier to return a structured result such as:

```json
{
    "status": "completed",
    "label": "plastic bottle",
    "category": "recyclable",
    "confidence": 0.94
}
```

For an invalid image, the classifier can return:

```json
{
    "status": "invalid_image",
    "message": "The uploaded image is not suitable for classification."
}
```

The backend validates this result before continuing with the remaining processing steps.

## Database Integration

The backend does not directly perform SQL operations.

Instead, it communicates with the `DatabaseManager` provided by the **Data Management & AI Guidance** subsystem.

After successful classification, the backend stores relevant classification information such as:

- Label
- Confidence
- Status
- Region

The database operation returns a `classification_id`, which is then included in the final response.

## Guidance Integration

After classification, the backend sends the normalized waste label and region to the `GuidanceService`.

The guidance service retrieves the appropriate disposal guidance from the data-management subsystem and can use AI assistance when required.

The backend then combines:

```text
Classification Result
        +
Disposal Guidance
        +
Classification ID
        |
        v
Final Structured Response
```

## Example Backend Response

A successful response can contain information such as:

```json
{
    "classification": {
        "label": "plastic bottle",
        "category": "recyclable",
        "confidence": 0.94,
        "region": "Dortmund"
    },
    "guidance": {
        "bin_type": "Yellow Bin",
        "instruction": "Dispose of the empty plastic bottle in the appropriate recycling container."
    },
    "classification_id": 15
}
```

## Testing

The backend subsystem is tested using `pytest`.

Tests cover:

- Valid classifier results.
- Invalid classifier results.
- Invalid images.
- Missing labels.
- Invalid confidence values.
- Guidance integration.
- Classification storage.
- Response composition.
- Complete backend integration flow.

Run the backend tests with:

```bash
python -m pytest -v tests/test_backend.py
```

## Files

The main backend files are:

```text
backend/
├── __init__.py
├── analysis_service.py
├── classification_result_handler.py
├── response_composer.py
└── exceptions.py
```

## Subsystem Dependencies

The backend integrates with:

- **Web Interface** — provides uploaded images and receives the final response.
- **ML Image Classification** — provides the predicted waste label and confidence.
- **Data Management & AI Guidance** — provides disposal guidance and database operations.

The backend therefore serves as the integration layer connecting the major components of the application.


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

**UML class diagram:** `docs/class_diagram_classifier.png` (source: `docs/class_diagram_classifier.puml`,
matches the code in `classifier/`).

![Classifier class diagram](docs/class_diagram_classifier.png)

Simplified overview:

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

Kept deliberately simple: SQLite only, no admin/feedback/chat features that
nobody in the team uses yet. Easier for everyone to read and explain.

| File | Purpose |
|------|---------|
| `database/db.py` | `DatabaseManager`, the only file with SQL (SQLite, 5 tables) |
| `database/models.py` | `WasteCategory`, `WasteItem`, `DisposalRule` (encapsulation, validation) |
| `database/exceptions.py` | `DataManagementError`, `InvalidDataError`, `ItemNotFoundError`, `DatabaseConnectionError` |
| `database/guidance.py` | `GuidanceService`: AI explanation for a result, with cache, daily limit and fallback |
| `database/schema_sqlite.sql` | Database schema |
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
db.save_classification("glass jar", 0.92, status="completed")

# Dashboard (Kanika)
db.get_classification_records(region="Dortmund", limit=50)   # newest first, region=None -> all
db.get_stats(region="Dortmund")
```

`get_stats()` returns `total_items`, `by_category`, `category_percentages`,
`recycling_rate` (0-1), `per_day`, `top_items`, `region_counts` and `uncertain_count`.

Flask routes in `web_interface_dashboard/app.py`: `POST /analyse`,
`GET /dashboard` (Kanika's HTML dashboard page, built on `get_stats()`).

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

`database/waste.db` is created automatically on the first start (5 tables + 72 Dortmund rules
from `data/waste_guidance.json`). It is not committed to Git.
To load changed rules from the JSON file, delete `database/waste.db` and start again.

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
python -m pytest -q                   # tests for the whole project (16 are Ha's: database + AI, mocked)
python -m pytest -q --cov=database    # coverage for Ha's part
python demo_data_management.py        # classes + database
python demo_ai_guidance.py            # AI explanation, cache and fallback
```
### Capstone Project Vedio demonstration
https://www.youtube.com/watch?v=JKf68Jn4LGo