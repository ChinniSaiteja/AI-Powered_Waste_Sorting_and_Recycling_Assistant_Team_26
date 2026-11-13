import time
from typing import Optional

from classifier.category_mapper import CategoryMapper
from classifier.config import ClassifierConfig
from classifier.exceptions import ClassifierErrorHandler
from classifier.model import ClassifierModel, ZeroShotClipModel
from classifier.preprocessor import ImagePreprocessor, ImageSource
from classifier.result import PredictionResult
from classifier.status import ClassifierStatus


class WasteClassifier:
    """The single entry point the Flask backend calls (FR 1, FR 9, FR 10).

    Pipeline: ImagePreprocessor -> ClassifierModel -> CategoryMapper -> PredictionResult.
    classify() never raises: every failure becomes a status the backend can show.
    Images are only kept in memory and never written to disk (NFR 3: privacy).
    """

    def __init__(
        self,
        config: Optional[ClassifierConfig] = None,
        model: Optional[ClassifierModel] = None,
        mapper: Optional[CategoryMapper] = None,
    ):
        self.config = config or ClassifierConfig()
        self.mapper = mapper or CategoryMapper()
        self.preprocessor = ImagePreprocessor(self.config)
        self.model = model or ZeroShotClipModel(self.config, self.mapper.labels)
        self.error_handler = ClassifierErrorHandler("The classifier is currently unavailable")

    @property
    def confidence_threshold(self) -> float:
        return self.config.confidence_threshold

    @confidence_threshold.setter
    def confidence_threshold(self, value: float) -> None:
        if not 0.0 <= value <= 1.0:
            raise ValueError("confidence_threshold must be between 0 and 1")
        self.config.confidence_threshold = value

    def warm_up(self) -> None:
        """Load the model at app start so the first user does not wait for the download."""
        self.model.load()

    def predict(self, image: ImageSource) -> PredictionResult:
        try:
            raw = self.preprocessor.validate(image)
            prepared = self.preprocessor.preprocess(raw)
        except Exception as exc:
            status, message = self.error_handler.to_status(exc)
            return PredictionResult(status, message=message)

        start = time.perf_counter()
        try:
            label, confidence = self.model.predict(prepared)
        except Exception as exc:  # e.g. model download or memory error
            status, message = self.error_handler.to_status(exc)
            return PredictionResult(status, message=message)
        inference_ms = (time.perf_counter() - start) * 1000  # NFR 1: performance

        category = self.mapper.map_category(label)
        if self.mapper.check_confidence(confidence, self.confidence_threshold):
            status, message = ClassifierStatus.COMPLETED, ""
        else:
            status = ClassifierStatus.UNCERTAIN
            message = "The prediction is uncertain, please check the item or try another photo"

        return PredictionResult(status, label, category, confidence, message, inference_ms)

    def classify(self, image: ImageSource) -> dict:
        """Same as predict() but returns a JSON-ready dict for the backend."""
        return self.predict(image).to_dict()
