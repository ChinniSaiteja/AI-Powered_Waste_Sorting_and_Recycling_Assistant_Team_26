"""
Handles and validates the result returned by the ML classifier.
"""

from .exceptions import (
    InvalidClassificationResultError,
    InvalidImageError,
)


class ClassificationResultHandler:
    """
    Validates and normalizes the raw classifier result.
    """

    DEFAULT_REGION = "Dortmund"

    def __init__(self, default_region: str = DEFAULT_REGION):
        self._default_region = default_region

    @property
    def default_region(self) -> str:
        """Return the default region."""
        return self._default_region

    @default_region.setter
    def default_region(self, value: str) -> None:
        """Set the default region."""
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Region must be a non-empty string.")

        self._default_region = value.strip().title()

    def initialize(self) -> None:
        """
        Initialize the handler.

        Currently no additional initialization is required.
        """
        pass

    def handle(
        self,
        prediction: dict,
        region: str | None = None,
    ) -> dict:
        """
        Validate and normalize the classifier response.

        Expected classifier result:

        {
            "status": "completed",
            "label": "plastic bottle",
            "category": "recyclable",
            "confidence": 0.94
        }
        """

        if not isinstance(prediction, dict):
            raise InvalidClassificationResultError(
                "Classifier result must be a dictionary."
            )

        status = prediction.get("status", "completed")

        # Handles invalid image case
        if status == "invalid_image":

            message = prediction.get("message")

            if not isinstance(message, str) or not message.strip():
                message = (
                    "The uploaded image could not be used "
                    "for waste classification."
                )

            raise InvalidImageError(message)

        if status not in ("completed", "uncertain"):
            raise InvalidClassificationResultError(
                f"Unsupported classification status: {status}"
            )

        label = prediction.get("label")

        if not isinstance(label, str) or not label.strip():
            raise InvalidClassificationResultError(
                "Classifier result must contain a valid label."
            )

        confidence = prediction.get("confidence")

        if confidence is None:
            raise InvalidClassificationResultError(
                "Classifier result is missing confidence."
            )

        try:
            confidence = float(confidence)
        except (TypeError, ValueError) as error:
            raise InvalidClassificationResultError(
                "Classifier confidence must be numeric."
            ) from error

        if not 0.0 <= confidence <= 1.0:
            raise InvalidClassificationResultError(
                "Classifier confidence must be between 0 and 1."
            )

        category = prediction.get("category", "landfill")

        if not isinstance(category, str):
            category = "landfill"

        selected_region = (
            region.strip().title()
            if isinstance(region, str) and region.strip()
            else self.default_region
        )

        return {
            "status": status,
            "label": label.strip().lower(),
            "category": category.strip().lower(),
            "confidence": confidence,
            "message": prediction.get("message", ""),
            "region": selected_region,
        }