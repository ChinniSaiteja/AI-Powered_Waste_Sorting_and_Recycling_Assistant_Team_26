from abc import ABC, abstractmethod
from typing import List, Tuple

from PIL import Image

from classifier.config import ClassifierConfig

# (label, score, (x, y, width, height)) in pixels of the input image
RawDetection = Tuple[str, float, Tuple[int, int, int, int]]


class DetectionModel(ABC):
    """Interface for any object detection model; lets tests use a fake model."""

    def __init__(self, config: ClassifierConfig, labels: list):
        self.config = config
        self.labels = labels

    def load(self) -> None:
        """Load weights ahead of time; models without weights do nothing."""

    @abstractmethod
    def detect(self, image: Image.Image) -> List[RawDetection]:
        """Return every object found, with its label, score and bounding box."""


class ZeroShotOwlVitModel(DetectionModel):
    """Pretrained OWL-ViT model that finds and boxes objects by their names.

    Like CLIP it needs no training: it looks for regions matching sentences like
    "a photo of a glass jar". It is built on CLIP, so it uses the same labels.
    The model is loaded lazily on the first detection.

    All label sentences are checked in one forward pass. (The Hugging Face
    "zero-shot-object-detection" pipeline runs the model once per label, which
    was about 30x slower with our 23 labels.)
    """

    def __init__(self, config: ClassifierConfig, labels: list):
        super().__init__(config, labels)
        self._processor = None
        self._model = None
        self._prompts = [config.prompt_template.format(label) for label in labels]

    def load(self) -> None:
        self._load()

    def _load(self):
        if self._model is None:
            # heavy imports, only when really needed
            from transformers import OwlViTForObjectDetection, OwlViTProcessor

            self._processor = OwlViTProcessor.from_pretrained(self.config.detector_model_name)
            self._model = OwlViTForObjectDetection.from_pretrained(self.config.detector_model_name)
            self._model.to(self.config.device).eval()
        return self._processor, self._model

    def detect(self, image: Image.Image) -> List[RawDetection]:
        import torch

        processor, model = self._load()
        inputs = processor(text=[self._prompts], images=image, return_tensors="pt").to(self.config.device)
        with torch.no_grad():
            outputs = model(**inputs)
        found = processor.post_process_grounded_object_detection(
            outputs,
            threshold=self.config.min_detection_score,
            target_sizes=[(image.height, image.width)],
        )[0]

        detections = []
        for score, label_index, box in zip(found["scores"], found["labels"], found["boxes"]):
            xmin, ymin, xmax, ymax = (max(0, int(v)) for v in box.tolist())
            detections.append(
                (self.labels[int(label_index)], float(score), (xmin, ymin, xmax - xmin, ymax - ymin))
            )
        return detections
