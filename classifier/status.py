from enum import Enum


class ClassifierStatus(str, Enum):
    """Fixed status values returned to the backend (NFR 5: consistency)."""

    COMPLETED = "completed"        # confident prediction (backend ALLOWED_STATUS)
    UNCERTAIN = "uncertain"        # prediction below the confidence threshold
    INVALID_IMAGE = "invalid_image"  # unreadable / unsupported / too large
    ERROR = "error"                # model failed unexpectedly
