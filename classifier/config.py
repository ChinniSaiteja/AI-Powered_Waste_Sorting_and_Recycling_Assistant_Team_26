from dataclasses import dataclass, field

from classifier.exceptions import InvalidConfigError


@dataclass
class ClassifierConfig:
    """All tunable settings of the classifier in one place."""

    model_name: str = "openai/clip-vit-base-patch32"
    confidence_threshold: float = 0.5
    image_size: int = 224
    max_file_size_mb: float = 10.0
    allowed_formats: tuple = ("JPEG", "PNG", "WEBP")
    prompt_template: str = "a photo of {}"
    device: str = field(default="cpu")

    # Object detection (WasteDetector). OWL-ViT scores are much lower than CLIP's
    # probabilities: a correct object often scores 0.1-0.4, so the thresholds differ.
    detector_model_name: str = "google/owlvit-base-patch32"
    detection_threshold: float = 0.2   # objects below this are "uncertain"
    min_detection_score: float = 0.05  # objects below this are dropped
    max_objects: int = 10
    overlap_iou: float = 0.5           # boxes overlapping more than this are one object

    def __post_init__(self):
        for name in ("confidence_threshold", "detection_threshold",
                     "min_detection_score", "overlap_iou"):
            if not 0.0 <= getattr(self, name) <= 1.0:
                raise InvalidConfigError(f"{name} must be between 0 and 1", {name: getattr(self, name)})
        if self.max_objects <= 0:
            raise InvalidConfigError("max_objects must be positive", {"max_objects": self.max_objects})
        if self.image_size <= 0:
            raise InvalidConfigError("image_size must be positive", {"image_size": self.image_size})
