import time
from typing import List, Optional

from classifier.category_mapper import CategoryMapper
from classifier.config import ClassifierConfig
from classifier.exceptions import ClassifierErrorHandler
from classifier.detection_model import DetectionModel, RawDetection, ZeroShotOwlVitModel
from classifier.detection_result import DetectedObject, DetectionResult
from classifier.preprocessor import ImagePreprocessor, ImageSource
from classifier.status import ClassifierStatus


class WasteDetector:
    """Finds every waste item in an image: label, category, confidence and bounding box.

    Pipeline: ImagePreprocessor -> DetectionModel -> overlap removal -> CategoryMapper.
    Like WasteClassifier, detect() never raises: every failure becomes a status.
    Images are only kept in memory and never written to disk.
    """

    def __init__(
        self,
        config: Optional[ClassifierConfig] = None,
        model: Optional[DetectionModel] = None,
        mapper: Optional[CategoryMapper] = None,
    ):
        self.config = config or ClassifierConfig()
        self.mapper = mapper or CategoryMapper()
        self.preprocessor = ImagePreprocessor(self.config)
        self.model = model or ZeroShotOwlVitModel(self.config, self.mapper.labels)
        self.error_handler = ClassifierErrorHandler("The detector is currently unavailable")

    @property
    def detection_threshold(self) -> float:
        return self.config.detection_threshold

    @detection_threshold.setter
    def detection_threshold(self, value: float) -> None:
        if not 0.0 <= value <= 1.0:
            raise ValueError("detection_threshold must be between 0 and 1")
        self.config.detection_threshold = value

    def warm_up(self) -> None:
        """Load the model at app start so the first user does not wait for the download."""
        self.model.load()

    def detect(self, image: ImageSource) -> DetectionResult:
        try:
            prepared = self.preprocessor.prepare_for_detection(self.preprocessor.validate(image))
        except Exception as exc:
            status, message = self.error_handler.to_status(exc)
            return DetectionResult(status, message=message)

        start = time.perf_counter()
        try:
            raw = self.model.detect(prepared)
        except Exception as exc:  # e.g. model download or memory error
            status, message = self.error_handler.to_status(exc)
            return DetectionResult(status, message=message)
        inference_ms = (time.perf_counter() - start) * 1000

        objects = [self._to_object(d) for d in self._remove_overlaps(raw)]
        if not objects:
            return DetectionResult(
                ClassifierStatus.UNCERTAIN, [], "No waste item was found, please try another photo",
                inference_ms,
            )
        if any(obj.status == ClassifierStatus.COMPLETED for obj in objects):
            return DetectionResult(ClassifierStatus.COMPLETED, objects, "", inference_ms)
        return DetectionResult(
            ClassifierStatus.UNCERTAIN, objects,
            "The detection is uncertain, please check the items or try another photo",
            inference_ms,
        )

    def detect_dict(self, image: ImageSource) -> dict:
        """Same as detect() but returns a JSON-ready dict for the backend."""
        return self.detect(image).to_dict()

    def _to_object(self, detection: RawDetection) -> DetectedObject:
        label, score, box = detection
        confident = self.mapper.check_confidence(score, self.detection_threshold)
        status = ClassifierStatus.COMPLETED if confident else ClassifierStatus.UNCERTAIN
        return DetectedObject(label, self.mapper.map_category(label), score, box, status)

    def _remove_overlaps(self, detections: List[RawDetection]) -> List[RawDetection]:
        """Keep the best label per object: the model often boxes one item several
        times with different labels, so overlapping boxes count as one object."""
        kept = []
        for detection in sorted(detections, key=lambda d: d[1], reverse=True):
            if detection[1] < self.config.min_detection_score:
                continue
            if all(self.iou(detection[2], other[2]) <= self.config.overlap_iou for other in kept):
                kept.append(detection)
            if len(kept) == self.config.max_objects:
                break
        return kept

    @staticmethod
    def iou(box_a, box_b) -> float:
        """Intersection over union of two (x, y, width, height) boxes, from 0 to 1."""
        ax, ay, aw, ah = box_a
        bx, by, bw, bh = box_b
        overlap_w = max(0, min(ax + aw, bx + bw) - max(ax, bx))
        overlap_h = max(0, min(ay + ah, by + bh) - max(ay, by))
        overlap = overlap_w * overlap_h
        union = aw * ah + bw * bh - overlap
        return overlap / union if union else 0.0
