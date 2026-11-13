"""Subsystem 3 - Computer Vision Classifier Model (Azam Rahmani, Team 26).

The backend only needs:

    from classifier import WasteClassifier
    result = WasteClassifier().classify(image_bytes_or_path)    # one label
    result = WasteDetector().detect_dict(image_bytes_or_path)   # every item + bounding box
"""

from classifier.category_mapper import CategoryMapper
from classifier.config import ClassifierConfig
from classifier.detection_model import DetectionModel, ZeroShotOwlVitModel
from classifier.detection_result import DetectedObject, DetectionResult
from classifier.evaluator import ModelEvaluator
from classifier.exceptions import (
    ClassifierError,
    ClassifierErrorHandler,
    InvalidConfigError,
    InvalidImageError,
    ModelUnavailableError,
)
from classifier.model import ClassifierModel, ZeroShotClipModel
from classifier.preprocessor import ImagePreprocessor
from classifier.result import PredictionResult
from classifier.status import ClassifierStatus
from classifier.waste_classifier import WasteClassifier
from classifier.waste_detector import WasteDetector

__all__ = [
    "CategoryMapper",
    "ClassifierError",
    "ClassifierErrorHandler",
    "ClassifierConfig",
    "ClassifierModel",
    "ClassifierStatus",
    "DetectedObject",
    "DetectionModel",
    "DetectionResult",
    "ImagePreprocessor",
    "InvalidConfigError",
    "InvalidImageError",
    "ModelEvaluator",
    "ModelUnavailableError",
    "PredictionResult",
    "WasteClassifier",
    "WasteDetector",
    "ZeroShotClipModel",
    "ZeroShotOwlVitModel",
]
