# Subsystem 3 – Computer Vision Classifier Model

**Owner:** Azam Rahmani (ESE, 7224524) · Team 26 · AI-Powered Waste Sorting & Recycling Assistant

The classifier receives one waste-item image from the Flask backend and returns
the item label, waste category (recyclable · compostable · landfill), confidence
and a status. It uses a pretrained CLIP vision model (`openai/clip-vit-base-patch32`)
in zero-shot mode, so no training is needed.

## How the backend uses it

```python
from classifier import WasteClassifier

classifier = WasteClassifier()            # create once at app start
classifier.warm_up()                      # load the model before the first request
result = classifier.classify(request.files["image"].read())
```

The result always contains the same fields:

```json
{"status": "completed", "label": "glass jar", "category": "recyclable",
 "confidence": 0.92, "message": "", "inference_ms": 140.3}
```

| status | meaning | what the web page should show |
|---|---|---|
| `completed` | confident prediction | label, category, bin guidance |
| `uncertain` | confidence below threshold (default 0.5) | the prediction marked as "uncertain" |
| `invalid_image` | empty, corrupt, unsupported or too large file | `message` as an error |
| `error` | model failed | "classifier unavailable" |

`label` is exactly an item label from the Data Management subsystem's
`data/waste_guidance.json` (lowercase with spaces, e.g. `banana peel`), so the
backend can pass it straight to `get_rule(label)`. The category matches that file too.

## Object detection: every item with a bounding box

`WasteDetector` finds **all** waste items in one photo. It uses the pretrained
zero-shot detector OWL-ViT (`google/owlvit-base-patch32`), which is built on CLIP and
reads the same item labels, so no training is needed either.

```python
from classifier import WasteDetector

detector = WasteDetector()
detector.warm_up()
result = detector.detect_dict(request.files["image"].read())
```

```json
{"status": "completed", "count": 2, "message": "", "inference_ms": 850.2,
 "objects": [
   {"label": "plastic bottle", "category": "recyclable", "confidence": 0.41,
    "bounding_box": [10, 5, 20, 40], "status": "completed"},
   {"label": "aluminium can", "category": "recyclable", "confidence": 0.30,
    "bounding_box": [40, 10, 15, 25], "status": "completed"}]}
```

- `bounding_box` is `[x, y, width, height]` in pixels of the uploaded photo (no cropping).
- Each object has its own `status`: `completed` or `uncertain` (score below
  `detection_threshold`, default 0.2). OWL-ViT scores are lower than CLIP probabilities,
  so this threshold is lower than the classifier's 0.5.
- The whole result is `completed` if at least one object is confident, `uncertain` if
  nothing confident was found, and `invalid_image` / `error` as for the classifier.
- When the model boxes the same item twice with different labels, only the best label is kept.

## Class diagram

```mermaid
classDiagram
    class WasteClassifier {
        +config: ClassifierConfig
        +predict(image) PredictionResult
        +classify(image) dict
    }
    class ClassifierConfig {
        +model_name: str
        +confidence_threshold: float
        +image_size: int
        +max_file_size_mb: float
        +allowed_formats: tuple
    }
    class ImagePreprocessor {
        +validate(image) Image
        +preprocess(image) Image
    }
    class ClassifierModel {
        <<abstract>>
        +predict(image) (label, confidence)
    }
    class ZeroShotClipModel {
        -_pipeline
        +predict(image) (label, confidence)
    }
    class CategoryMapper {
        +LABEL_TO_CATEGORY: dict
        +map_category(label) str
        +check_confidence(confidence, threshold) bool
    }
    class PredictionResult {
        +status: ClassifierStatus
        +label: str
        +category: str
        +confidence: float
        +message: str
        +inference_ms: float
        +to_dict() dict
    }
    class ClassifierStatus {
        <<enumeration>>
        COMPLETED
        UNCERTAIN
        INVALID_IMAGE
        ERROR
    }
    class ModelEvaluator {
        +load_dataset(folder) list
        +evaluate(samples) dict
        +plot_confusion_matrix(report, categories, path)
    }
    class InvalidImageError
    class WasteDetector {
        +detection_threshold: float
        +detect(image) DetectionResult
        +detect_dict(image) dict
    }
    class DetectionModel {
        <<abstract>>
        +detect(image) list
    }
    class ZeroShotOwlVitModel
    class DetectionResult {
        +status: ClassifierStatus
        +objects: list~DetectedObject~
        +to_dict() dict
    }
    class DetectedObject {
        +label: str
        +category: str
        +confidence: float
        +bounding_box: tuple
        +status: ClassifierStatus
    }

    WasteClassifier --> ClassifierConfig
    WasteClassifier --> ImagePreprocessor
    WasteClassifier --> ClassifierModel
    WasteClassifier --> CategoryMapper
    WasteClassifier ..> PredictionResult : creates
    ClassifierModel <|-- ZeroShotClipModel
    PredictionResult --> ClassifierStatus
    ImagePreprocessor ..> InvalidImageError : raises
    ModelEvaluator --> WasteClassifier
    WasteDetector --> ImagePreprocessor
    WasteDetector --> CategoryMapper
    WasteDetector --> DetectionModel
    DetectionModel <|-- ZeroShotOwlVitModel
    WasteDetector ..> DetectionResult : creates
    DetectionResult *-- DetectedObject
```

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```bash
python scripts/classify_image.py photo.jpg        # one image
python scripts/evaluate.py test_images/           # accuracy + confusion matrix
python -m pytest -v                               # unit tests (no model download needed)
```

For `evaluate.py`, put photos in `test_images/<label>/`, using the labels from
`CategoryMapper.LABEL_TO_CATEGORY`, with `_` instead of spaces in folder names
(e.g. `test_images/glass_jar/1.jpg` for the label `glass jar`).
The first real run downloads the CLIP model (about 600 MB).

## Requirements coverage

| Requirement | Where |
|---|---|
| FR1 Accept image from backend | `WasteClassifier.classify` (bytes, path or PIL image) |
| FR2 Check image readable/supported | `ImagePreprocessor.validate` |
| FR3 Preprocess | `ImagePreprocessor.preprocess` |
| FR4 Pretrained model inference | `ZeroShotClipModel` |
| FR5 Most likely label | `ZeroShotClipModel.predict` |
| FR6 Map to category | `CategoryMapper.map_category` |
| FR7 Return confidence | `PredictionResult.confidence` |
| FR8 Flag low confidence | `CategoryMapper.check_confidence` → `uncertain` |
| FR9 Clear status | `ClassifierStatus` |
| FR10 Structured output | `PredictionResult.to_dict` |
| NFR1 Performance | `inference_ms`, `ModelEvaluator` average time |
| NFR2 Reliability | `classify` never raises |
| NFR3 Privacy | images stay in memory, never saved |
| NFR4 Robustness | EXIF rotation, RGB conversion, resize |
| NFR5 Consistency | fixed field names (tested) |
| NFR6 Interoperability | JSON-ready dict for Flask |
| NFR7 Observability | status + message, errors logged |
| NFR8 Accuracy | `scripts/evaluate.py` |
| NFR9 Maintainability | preprocessing, model and mapping in separate classes |
| NFR10 Testability | `tests/` with a fake model |
