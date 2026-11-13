"""
Subsystem: Web Interface - Analysis Controller

AnalysisController: checks whether an uploaded image is valid (an image and a
file name are present, and the file type is PNG, JPG or JPEG) before it is sent
to the classifier, and records the request status and any error message.

Usage (in the Flask app):
    controller = AnalysisController()
    response = controller.request_analysis(image, image.filename)
    if response["status"] == "error":
        ...
"""


class AnalysisController:
    """Validates uploads and keeps track of the analysis request."""

    DEFAULT_EXTENSIONS = (".png", ".jpg", ".jpeg")
    VALID_STATUSES = (
        "Not Requested",
        "Valid Upload",
        "Invalid Upload",
        "Analysis Requested",
        "Error",
    )

    # ------------------------------------------------------------------
    # 1. Constructor
    # ------------------------------------------------------------------
    def __init__(self, allowed_extensions: tuple | None = None):
        self._allowed_extensions = self.DEFAULT_EXTENSIONS
        self.initialize(allowed_extensions)

    # ------------------------------------------------------------------
    # 2. Initialisation methods
    # ------------------------------------------------------------------
    def initialize(self, allowed_extensions: tuple | None = None) -> None:
        """Reset the controller and optionally configure the accepted file types."""
        if allowed_extensions is not None:
            self.allowed_extensions = allowed_extensions
        self._request_status = "Not Requested"
        self._error_message = None

    def to_dict(self) -> dict:
        """Current state of the request."""
        return {
            "request_status": self._request_status,
            "error_message": self._error_message,
        }

    # ------------------------------------------------------------------
    # 3. Getters & setters
    # ------------------------------------------------------------------
    @property
    def request_status(self) -> str:
        return self._request_status

    @request_status.setter
    def request_status(self, status: str) -> None:
        if status not in self.VALID_STATUSES:
            raise ValueError(f"Invalid request status: {status}")
        self._request_status = status

    @property
    def error_message(self) -> str | None:
        return self._error_message

    @error_message.setter
    def error_message(self, message: str | None) -> None:
        if message is not None and (not isinstance(message, str) or not message.strip()):
            raise ValueError("Error message must be a non-empty string or None.")
        self._error_message = message

    @property
    def allowed_extensions(self) -> tuple:
        return self._allowed_extensions

    @allowed_extensions.setter
    def allowed_extensions(self, extensions) -> None:
        if not extensions or not all(
            isinstance(ext, str) and ext.startswith(".") for ext in extensions
        ):
            raise ValueError("Extensions must be a non-empty list like ('.png', '.jpg').")
        self._allowed_extensions = tuple(ext.lower() for ext in extensions)

    # ------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------
    def validate_upload(self, image, filename) -> bool:
        """True if an image and a file name are given and the file type is allowed."""
        if image and filename:
            if filename.lower().endswith(self.allowed_extensions):
                self.request_status = "Valid Upload"
                self.error_message = None
                return True
            self.request_status = "Invalid Upload"
            self.error_message = "Please upload a valid image file (PNG, JPG, JPEG)."
            return False
        self.request_status = "Invalid Upload"
        self.error_message = "Please provide both an image and a filename."
        return False

    def handle_error(self, error_message: str) -> None:
        """Record an error from a later step, e.g. the classifier."""
        self.error_message = error_message
        self.request_status = "Error"

    def request_analysis(self, image, filename) -> dict:
        """Validate the upload and mark it as ready for the classifier."""
        if not self.validate_upload(image, filename):
            return {
                "status": "error",
                "message": self.error_message,
            }

        self.error_message = None
        self.request_status = "Analysis Requested"

        return {
            "status": "success",
            "message": "Image is ready for analysis",
        }