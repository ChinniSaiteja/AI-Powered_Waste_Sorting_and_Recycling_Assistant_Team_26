"""
Tests for the Backend & Application Integration subsystem.

Tested components:
- ClassificationResultHandler
- ResponseComposer
- AnalysisService
- Backend exception handling
"""

import pytest

from backend.analysis_service import AnalysisService
from backend.classification_result_handler import (
    ClassificationResultHandler,
)
from backend.response_composer import ResponseComposer
from backend.exceptions import (
    ClassifierIntegrationError,
    InvalidImageError,
    InvalidClassificationResultError,
    GuidanceIntegrationError,
)


# ------------------------------------------------------------------
# Fake dependencies
# ------------------------------------------------------------------

class FakeClassifier:
    """Fake classifier used for backend testing."""

    def __init__(
        self,
        label="plastic bottle",
        category="recyclable",
        confidence=0.94,
        status="completed",
    ):
        self.label = label
        self.category = category
        self.confidence = confidence
        self.status = status

    def classify(self, image_bytes):
        """Return a simulated classifier result."""

        if not image_bytes:
            raise ValueError("Image data is empty.")

        return {
            "status": self.status,
            "label": self.label,
            "category": self.category,
            "confidence": self.confidence,
        }

class InvalidImageClassifier:
    """
    Fake classifier that reports an invalid uploaded image.
    """

    def classify(self, image_bytes):
        return {
            "status": "invalid_image",
            "message": (
                "The uploaded image is not suitable "
                "for waste classification."
            ),
        }

class BrokenClassifier:
    """Classifier that simulates an integration failure."""

    def classify(self, image_bytes):
        raise RuntimeError("Classifier is unavailable.")


class FakeGuidanceService:
    """Fake guidance service used for backend testing."""

    def get_guidance(self, label, region="Dortmund"):
        """Return simulated disposal guidance."""

        return {
            "rule": {
                "category": "recyclable",
                "bin_type": "Yellow recycling bin",
                "instruction": (
                    "Place the plastic bottle in the recycling bin."
                ),
                "is_deposit": True,
            },
            "explanation": (
                "Plastic bottles can generally be recycled."
            ),
            "ai_generated": False,
        }


class BrokenGuidanceService:
    """Guidance service that simulates an integration failure."""

    def get_guidance(self, label, region="Dortmund"):
        raise RuntimeError("Guidance service is unavailable.")


class FakeDatabaseManager:
    """Fake database manager used for backend testing."""

    def __init__(self):
        self.saved_classifications = []

    def save_classification(
        self,
        label,
        confidence,
        status,
        region,
    ):
        """Store a classification in memory and return an ID."""

        classification_id = len(
            self.saved_classifications
        ) + 1

        self.saved_classifications.append(
            {
                "id": classification_id,
                "label": label,
                "confidence": confidence,
                "status": status,
                "region": region,
            }
        )

        return classification_id


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------

@pytest.fixture
def database_manager():
    """Return a fake database manager."""

    return FakeDatabaseManager()


@pytest.fixture
def guidance_service():
    """Return a fake guidance service."""

    return FakeGuidanceService()


@pytest.fixture
def backend_service(
    database_manager,
    guidance_service,
):
    """Create a complete backend service for testing."""

    return AnalysisService(
        classifier=FakeClassifier(),
        database_manager=database_manager,
        guidance_service=guidance_service,
    )


# ------------------------------------------------------------------
# ClassificationResultHandler tests
# ------------------------------------------------------------------

def test_classification_result_handler_valid_result():
    """Valid classifier results should be normalized correctly."""

    handler = ClassificationResultHandler()

    result = handler.handle(
        {
            "status": "completed",
            "label": "Plastic Bottle",
            "category": "Recyclable",
            "confidence": 0.94,
        }
    )

    assert result["status"] == "completed"
    assert result["label"] == "plastic bottle"
    assert result["category"] == "recyclable"
    assert result["confidence"] == 0.94
    assert result["region"] == "Dortmund"


def test_classification_result_handler_custom_region():
    """A supplied region should be used instead of the default."""

    handler = ClassificationResultHandler()

    result = handler.handle(
        {
            "status": "completed",
            "label": "Plastic Bottle",
            "category": "Recyclable",
            "confidence": 0.94,
        },
        region="Dortmund",
    )

    assert result["region"] == "Dortmund"


def test_classification_result_handler_invalid_result():
    """A non-dictionary classifier result should be rejected."""

    handler = ClassificationResultHandler()

    with pytest.raises(
        InvalidClassificationResultError
    ):
        handler.handle("invalid result")

def test_classification_result_handler_invalid_image():
    """
    An invalid_image classifier result should raise
    InvalidImageError before label/confidence validation.
    """

    handler = ClassificationResultHandler()

    with pytest.raises(
        InvalidImageError,
        match="could not be used",
    ):
        handler.handle(
            {
                "status": "invalid_image",
                "message": (
                    "The uploaded image could not be used "
                    "for waste classification."
                ),
            }
        )

def test_backend_invalid_image_does_not_call_guidance_or_database():
    """
    An invalid image should stop the workflow immediately.

    Guidance and database saving must not happen.
    """

    database_manager = FakeDatabaseManager()
    guidance_service = FakeGuidanceService()

    service = AnalysisService(
        classifier=InvalidImageClassifier(),
        database_manager=database_manager,
        guidance_service=guidance_service,
    )

    with pytest.raises(InvalidImageError):
        service.analyze(
            image_bytes=b"fake-image-data",
            region="Dortmund",
        )

    # No classification should have been saved.
    assert len(
        database_manager.saved_classifications
    ) == 0

def test_classification_result_handler_missing_label():
    """A classifier result without a label should be rejected."""

    handler = ClassificationResultHandler()

    with pytest.raises(
        InvalidClassificationResultError
    ):
        handler.handle(
            {
                "status": "completed",
                "confidence": 0.94,
            }
        )


def test_classification_result_handler_invalid_confidence():
    """Confidence values outside 0-1 should be rejected."""

    handler = ClassificationResultHandler()

    with pytest.raises(
        InvalidClassificationResultError
    ):
        handler.handle(
            {
                "status": "completed",
                "label": "plastic bottle",
                "confidence": 1.5,
            }
        )


def test_classification_result_handler_missing_confidence():
    """A missing confidence value should be rejected."""

    handler = ClassificationResultHandler()

    with pytest.raises(
        InvalidClassificationResultError
    ):
        handler.handle(
            {
                "status": "completed",
                "label": "plastic bottle",
            }
        )

def test_invalid_image_does_not_require_label_or_confidence():
    """
    An invalid image result should be rejected as an invalid image,
    not as a missing-label or missing-confidence result.
    """

    handler = ClassificationResultHandler()

    with pytest.raises(InvalidImageError):
        handler.handle(
            {
                "status": "invalid_image",
                "message": "No recognizable waste was detected.",
            }
        )


# ------------------------------------------------------------------
# ResponseComposer tests
# ------------------------------------------------------------------

def test_response_composer():
    """ResponseComposer should create the expected frontend response."""

    composer = ResponseComposer()
    composer.initialize()

    result = composer.compose(
        classification={
            "status": "completed",
            "label": "plastic bottle",
            "category": "recyclable",
            "confidence": 0.94,
            "region": "Dortmund",
        },
        guidance={
            "rule": {
                "category": "recyclable",
                "bin_type": "Yellow recycling bin",
                "instruction": (
                    "Place the plastic bottle in the recycling bin."
                ),
                "is_deposit": True,
            },
            "explanation": (
                "Plastic bottles can generally be recycled."
            ),
            "ai_generated": False,
        },
        classification_id=1,
    )

    assert result["waste_name"] == "Plastic bottle"
    assert result["category"] == "recyclable"
    assert result["confidence"] == 0.94
    assert result["classification_id"] == 1
    assert result["status"] == "completed"
    assert result["region"] == "Dortmund"


def test_response_composer_uses_fallback_category():
    """Unknown categories should fall back to landfill."""

    composer = ResponseComposer()
    composer.initialize()

    result = composer.compose(
        classification={
            "status": "completed",
            "label": "unknown item",
            "category": "something_else",
            "confidence": 0.80,
            "region": "Dortmund",
        },
        guidance={},
        classification_id=2,
    )

    assert result["category"] == "landfill"


# ------------------------------------------------------------------
# AnalysisService tests
# ------------------------------------------------------------------

def test_backend_end_to_end(
    backend_service,
    database_manager,
):
    """
    Test the complete backend workflow:

    Image
        ↓
    Classifier
        ↓
    Result Handler
        ↓
    Guidance Service
        ↓
    Database
        ↓
    Response Composer
    """

    result = backend_service.analyze(
        image_bytes=b"fake-image-data",
        region="Dortmund",
    )

    assert result["status"] == "completed"
    assert result["waste_name"] == "Plastic bottle"
    assert result["category"] == "recyclable"
    assert result["confidence"] == 0.94
    assert result["region"] == "Dortmund"

    assert (
        result["disposal_instruction"]
        == (
            "Yellow recycling bin: "
            "Place the plastic bottle in the recycling bin."
        )
    )

    assert result["classification_id"] == 1

    # Verify that the backend saved the classification.
    assert len(
        database_manager.saved_classifications
    ) == 1

    saved = database_manager.saved_classifications[0]

    assert saved["label"] == "plastic bottle"
    assert saved["confidence"] == 0.94
    assert saved["region"] == "Dortmund"


def test_backend_rejects_empty_image(
    backend_service,
):
    """An empty image should be rejected."""

    with pytest.raises(ValueError):
        backend_service.analyze(b"")


def test_backend_classifier_failure(
    database_manager,
    guidance_service,
):
    """Classifier failures should become Backend errors."""

    service = AnalysisService(
        classifier=BrokenClassifier(),
        database_manager=database_manager,
        guidance_service=guidance_service,
    )

    with pytest.raises(
        ClassifierIntegrationError
    ):
        service.analyze(
            image_bytes=b"fake-image-data"
        )


def test_backend_guidance_failure(
    database_manager,
):
    """Guidance failures should become Backend errors."""

    service = AnalysisService(
        classifier=FakeClassifier(),
        database_manager=database_manager,
        guidance_service=BrokenGuidanceService(),
    )

    with pytest.raises(
        GuidanceIntegrationError
    ):
        service.analyze(
            image_bytes=b"fake-image-data"
        )


def test_backend_saves_classification(
    backend_service,
    database_manager,
):
    """The backend should save the classification."""

    backend_service.analyze(
        image_bytes=b"fake-image-data",
        region="Dortmund",
    )

    assert len(
        database_manager.saved_classifications
    ) == 1

    saved = database_manager.saved_classifications[0]

    assert saved["id"] == 1
    assert saved["label"] == "plastic bottle"
    assert saved["confidence"] == 0.94
    assert saved["status"] == "completed"