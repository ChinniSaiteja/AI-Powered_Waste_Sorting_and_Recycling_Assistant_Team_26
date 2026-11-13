from dataclasses import dataclass
from typing import Optional

from classifier.status import ClassifierStatus


@dataclass
class PredictionResult:
    """Structured output that the backend receives (FR 10)."""

    status: ClassifierStatus
    label: Optional[str] = None
    category: Optional[str] = None
    confidence: Optional[float] = None
    message: str = ""
    inference_ms: Optional[float] = None

    @property
    def is_success(self) -> bool:
        return self.status == ClassifierStatus.COMPLETED

    def to_dict(self) -> dict:
        """JSON-ready dictionary with fixed field names."""
        return {
            "status": self.status.value,
            "label": self.label,
            "category": self.category,
            "confidence": None if self.confidence is None else round(self.confidence, 4),
            "message": self.message,
            "inference_ms": None if self.inference_ms is None else round(self.inference_ms, 1),
        }
