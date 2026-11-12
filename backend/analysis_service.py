"""
Main orchestration service for image analysis.

The AnalysisService coordinates:

    Flask / Web Interface
            ↓
        ML Classifier
            ↓
    ClassificationResultHandler
            ↓
      GuidanceService
            ↓
      DatabaseManager
            ↓
      ResponseComposer
            ↓
       Frontend response
"""

from .classification_result_handler import (
    ClassificationResultHandler,
)
from .response_composer import ResponseComposer

from .exceptions import (
    ClassifierIntegrationError,
    GuidanceIntegrationError,
)


class AnalysisService:
    """
    Coordinates the complete image-analysis workflow.
    """

    def __init__(
        self,
        classifier,
        database_manager,
        guidance_service,
        result_handler=None,
        response_composer=None,
    ):
        self._classifier = classifier
        self._database_manager = database_manager
        self._guidance_service = guidance_service

        self._result_handler = (
            result_handler
            or ClassificationResultHandler()
        )

        self._response_composer = (
            response_composer
            or ResponseComposer()
        )

    # ---------------------------------------------------------
    # Properties
    # ---------------------------------------------------------

    @property
    def classifier(self):
        """Return the classifier."""
        return self._classifier

    @classifier.setter
    def classifier(self, value):
        """Set the classifier."""
        if value is None:
            raise ValueError("Classifier cannot be None.")

        self._classifier = value

    @property
    def database_manager(self):
        """Return the database manager."""
        return self._database_manager

    @database_manager.setter
    def database_manager(self, value):
        """Set the database manager."""
        if value is None:
            raise ValueError(
                "Database manager cannot be None."
            )

        self._database_manager = value

    @property
    def guidance_service(self):
        """Return the guidance service."""
        return self._guidance_service

    @guidance_service.setter
    def guidance_service(self, value):
        """Set the guidance service."""
        if value is None:
            raise ValueError(
                "Guidance service cannot be None."
            )

        self._guidance_service = value

    # ---------------------------------------------------------
    # Initialization
    # ---------------------------------------------------------

    def initialize(self) -> None:
        """
        Initialize backend components.
        """

        self._result_handler.initialize()
        self._response_composer.initialize()

    # ---------------------------------------------------------
    # Main analysis workflow
    # ---------------------------------------------------------

    def analyze(
        self,
        image_bytes: bytes,
        region: str = "Dortmund",
    ) -> dict:
        """
        Analyze an uploaded image.

        Parameters
        ----------
        image_bytes:
            Raw image bytes received from Flask.

        region:
            Region used for waste-disposal rules.

        Returns
        -------
        dict
            Final response expected by the frontend.
        """

        if not image_bytes:
            raise ValueError(
                "Image data cannot be empty."
            )

        # -----------------------------------------------------
        # Step 1: Call the ML classifier
        # -----------------------------------------------------

        try:
            prediction = self._classifier.classify(
                image_bytes
            )

        except Exception as error:
            raise ClassifierIntegrationError(
                "The classifier could not process the image."
            ) from error

        # -----------------------------------------------------
        # Step 2: Validate and normalize classifier result
        # -----------------------------------------------------

        classification = self._result_handler.handle(
            prediction,
            region=region,
        )

        # -----------------------------------------------------
        # Step 3: Retrieve guidance
        # -----------------------------------------------------

        try:
            guidance = self._guidance_service.get_guidance(
                classification["label"],
                classification["region"],
            )

        except Exception as error:
            raise GuidanceIntegrationError(
                "Could not retrieve waste guidance."
            ) from error

        # -----------------------------------------------------
        # Step 4: Save classification
        # -----------------------------------------------------

        classification_id = (
            self._database_manager.save_classification(
                label=classification["label"],
                confidence=classification["confidence"],
                status=classification["status"],
                region=classification["region"],
            )
        )

        # -----------------------------------------------------
        # Step 5: Compose final frontend response
        # -----------------------------------------------------

        return self._response_composer.compose(
            classification=classification,
            guidance=guidance,
            classification_id=classification_id,
        )