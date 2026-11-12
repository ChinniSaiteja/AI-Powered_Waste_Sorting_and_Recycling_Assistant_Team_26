"""
Custom exceptions for the Backend & Application Integration subsystem.
"""


class BackendError(Exception):
    """Base exception for backend integration errors."""

    pass


class ClassifierIntegrationError(BackendError):
    """Raised when the classifier cannot process an image."""

    pass


class InvalidImageError(BackendError):
    """
    Raised when the classifier determines that the uploaded
    image cannot be used for classification.
    """

    pass

class InvalidClassificationResultError(BackendError):
    """Raised when the classifier returns an invalid result."""

    pass


class GuidanceIntegrationError(BackendError):
    """Raised when the guidance service cannot provide guidance."""

    pass


class ResponseCompositionError(BackendError):
    """Raised when the final response cannot be composed."""

    pass