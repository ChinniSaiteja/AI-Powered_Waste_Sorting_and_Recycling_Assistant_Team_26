"""
Flask routes of Subsystem 3 (Home Assignment 4).

    POST /api/classifier/classify   form field "image" -> one label
    POST /api/classifier/detect     form field "image" -> every item + bounding box
    GET  /api/classifier/health     model and label information

Errors never crash the app: ClassifierErrorHandler turns them into a JSON
body with an error code and the matching HTTP status
(400 invalid image, 503 model unavailable).

    from classifier.api import create_app
    app = create_app()          # real models
    app.run()
"""

from flask import Blueprint, Flask, jsonify, request

from classifier.exceptions import ClassifierErrorHandler, InvalidImageError
from classifier.waste_classifier import WasteClassifier
from classifier.waste_detector import WasteDetector


def create_blueprint(classifier: WasteClassifier, detector: WasteDetector) -> Blueprint:
    api = Blueprint("classifier", __name__, url_prefix="/api/classifier")

    def uploaded_image() -> bytes:
        file = request.files.get("image")
        if file is None or not file.filename:
            raise InvalidImageError("No image file was sent (form field 'image')")
        return file.read()

    @api.post("/classify")
    def classify():
        result = classifier.classify(uploaded_image())
        return jsonify(result), ClassifierErrorHandler.http_status_for(result["status"])

    @api.post("/detect")
    def detect():
        result = detector.detect_dict(uploaded_image())
        return jsonify(result), ClassifierErrorHandler.http_status_for(result["status"])

    @api.get("/health")
    def health():
        return jsonify({
            "status": "ok",
            "classifier_model": classifier.config.model_name,
            "detector_model": detector.config.detector_model_name,
            "labels": len(classifier.mapper.labels),
        })

    return api


def create_app(classifier: WasteClassifier | None = None,
               detector: WasteDetector | None = None) -> Flask:
    """Flask app with the classifier routes; tests pass classifiers with fake models."""
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # same limit as ImagePreprocessor
    app.register_blueprint(create_blueprint(classifier or WasteClassifier(),
                                            detector or WasteDetector()))
    ClassifierErrorHandler().register(app)
    return app
