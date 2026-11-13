"""
Subsystem 3 - Image Classifier & Object Detector
Owner: Azam Rahmani

Home Assignment 4: Exception Handling
Error classes and the error-handling class of the classifier subsystem.

    ClassifierError                base class for every error of this subsystem
     |- InvalidImageError          upload is empty, broken, too large or not an image
     |- ModelUnavailableError      the vision model could not be loaded or crashed
     |- InvalidConfigError         a setting is out of range (e.g. threshold 1.5)

    ClassifierErrorHandler         turns any exception into one of these errors,
                                   logs it, and gives the status / HTTP response

Every error knows:
    - a readable message (safe to show to the user)
    - an error code (for logs and the frontend)
    - the HTTP status the Flask backend should return
    - the ClassifierStatus that WasteClassifier / WasteDetector report
    - to_dict() -> JSON body for the API response
"""

import logging
from collections import Counter

from classifier.status import ClassifierStatus

logger = logging.getLogger(__name__)


class ClassifierError(Exception):
    """Base class: catch this to handle every error of the classifier subsystem."""

    code = "CLASSIFIER_ERROR"
    http_status = 500
    status = ClassifierStatus.ERROR

    def __init__(self, message: str, details: dict | None = None):
        super().__init__(message)
        self.__message = message
        self.__details = details or {}

    @property
    def message(self) -> str:
        return self.__message

    @property
    def details(self) -> dict:
        return dict(self.__details)

    def to_dict(self) -> dict:
        return {
            "error": self.code,
            "status": self.status.value,
            "message": self.__message,
            "details": self.details,
        }


class InvalidImageError(ClassifierError, ValueError):
    """The uploaded file cannot be used (empty, broken, too large, wrong format)."""

    code = "INVALID_IMAGE"
    http_status = 400
    status = ClassifierStatus.INVALID_IMAGE


class ModelUnavailableError(ClassifierError):
    """The vision model could not be loaded or failed during inference."""

    code = "MODEL_UNAVAILABLE"
    http_status = 503
    status = ClassifierStatus.ERROR


class InvalidConfigError(ClassifierError, ValueError):
    """A classifier setting is invalid, e.g. a threshold outside 0..1."""

    code = "INVALID_CONFIG"
    http_status = 500
    status = ClassifierStatus.ERROR


class ClassifierErrorHandler:
    """The error-handling class of Subsystem 3.

    WasteClassifier and WasteDetector send every exception here instead of
    letting it crash the app. Known errors keep their message; unexpected
    ones (e.g. a CUDA or download error inside the model) are logged with the
    full traceback and replaced by a ModelUnavailableError, so no internal
    details reach the user. The handler also counts errors per code.
    """

    STATUS_TO_HTTP = {
        ClassifierStatus.COMPLETED: 200,
        ClassifierStatus.UNCERTAIN: 200,
        ClassifierStatus.INVALID_IMAGE: 400,
        ClassifierStatus.ERROR: 503,
    }

    def __init__(self, unavailable_message: str = "The classifier is currently unavailable"):
        self.unavailable_message = unavailable_message
        self.__counts = Counter()

    @property
    def unavailable_message(self) -> str:
        return self.__unavailable_message

    @unavailable_message.setter
    def unavailable_message(self, value: str) -> None:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("unavailable_message must be a non-empty string")
        self.__unavailable_message = value.strip()

    @property
    def error_counts(self) -> dict:
        """How many errors of each code were handled, e.g. {"INVALID_IMAGE": 2}."""
        return dict(self.__counts)

    def wrap(self, exc: Exception) -> ClassifierError:
        """Return a ClassifierError for any exception (and log unexpected ones)."""
        if isinstance(exc, ClassifierError):
            error = exc
            logger.info("%s: %s", error.code, error.message)
        else:
            logger.error("Unexpected error in the classifier subsystem", exc_info=exc)
            error = ModelUnavailableError(self.__unavailable_message,
                                          {"cause": type(exc).__name__})
        self.__counts[error.code] += 1
        return error

    def to_status(self, exc: Exception) -> tuple[ClassifierStatus, str]:
        """Status and user message for WasteClassifier / WasteDetector results."""
        error = self.wrap(exc)
        return error.status, error.message

    def to_response(self, exc: Exception) -> tuple[dict, int]:
        """JSON body and HTTP status code for a Flask error response."""
        error = self.wrap(exc)
        return error.to_dict(), error.http_status

    @classmethod
    def http_status_for(cls, status: str | ClassifierStatus) -> int:
        """HTTP status for a classifier result status ("invalid_image" -> 400)."""
        return cls.STATUS_TO_HTTP[ClassifierStatus(status)]

    def register(self, app) -> None:
        """Make a Flask app answer every ClassifierError with its JSON body and HTTP status."""
        app.register_error_handler(ClassifierError, lambda exc: self.to_response(exc))
