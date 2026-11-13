from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from classifier.status import ClassifierStatus


@dataclass
class DetectedObject:
    """One waste item found in the image."""

    label: str
    category: str
    confidence: float
    bounding_box: Tuple[int, int, int, int]  # x, y, width, height in pixels
    status: ClassifierStatus

    def to_dict(self) -> dict:
        return {
            "label": self.label,
            "category": self.category,
            "confidence": round(self.confidence, 4),
            "bounding_box": list(self.bounding_box),
            "status": self.status.value,
        }


@dataclass
class DetectionResult:
    """Structured output of WasteDetector that the backend receives."""

    status: ClassifierStatus
    objects: List[DetectedObject] = field(default_factory=list)
    message: str = ""
    inference_ms: Optional[float] = None

    @property
    def is_success(self) -> bool:
        return self.status == ClassifierStatus.COMPLETED

    def to_dict(self) -> dict:
        """JSON-ready dictionary with fixed field names."""
        return {
            "status": self.status.value,
            "count": len(self.objects),
            "objects": [obj.to_dict() for obj in self.objects],
            "message": self.message,
            "inference_ms": None if self.inference_ms is None else round(self.inference_ms, 1),
        }
