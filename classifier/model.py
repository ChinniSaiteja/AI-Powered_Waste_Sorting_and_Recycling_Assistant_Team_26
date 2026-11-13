from abc import ABC, abstractmethod
from typing import Optional, Tuple

from PIL import Image

from classifier.config import ClassifierConfig


class ClassifierModel(ABC):
    """Interface for any vision model; lets tests use a fake model (NFR 9, NFR 10)."""

    def __init__(self, config: ClassifierConfig, labels: list):
        self.config = config
        self.labels = labels

    def load(self) -> None:
        """Load weights ahead of time; models without weights do nothing."""

    @abstractmethod
    def predict(self, image: Image.Image) -> Tuple[str, Optional[float]]:
        """Return (most likely label, confidence between 0 and 1 or None)."""


class ZeroShotClipModel(ClassifierModel):
    """Pretrained CLIP model that picks the best matching label text (FR 4, FR 5).

    No training is needed: CLIP compares the image with sentences like
    "a photo of a glass jar" and returns a probability for each label.
    The model is loaded lazily on the first prediction.
    """

    def __init__(self, config: ClassifierConfig, labels: list):
        super().__init__(config, labels)
        self._pipeline = None
        self._prompts = {
            config.prompt_template.format(label.replace("_", " ")): label for label in labels
        }

    def load(self) -> None:
        self._load()

    def _load(self):
        if self._pipeline is None:
            from transformers import pipeline  # heavy import, only when really needed

            self._pipeline = pipeline(
                "zero-shot-image-classification",
                model=self.config.model_name,
                device=self.config.device,
            )
        return self._pipeline

    def predict(self, image: Image.Image) -> Tuple[str, Optional[float]]:
        outputs = self._load()(image, candidate_labels=list(self._prompts))
        best = max(outputs, key=lambda item: item["score"])
        return self._prompts[best["label"]], float(best["score"])
