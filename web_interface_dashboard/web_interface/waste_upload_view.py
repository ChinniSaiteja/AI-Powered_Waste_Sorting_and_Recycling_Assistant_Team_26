"""
Subsystem - Web Interface & Municipality Dashboard
Owner: Kanika Sehgal

WasteUploadView: receives the waste image the user selects on the upload page
(from the gallery or the phone camera) and stores its details
(file name, size, type) and the upload status.

Usage (in the Flask app):
    upload_view = WasteUploadView()
    upload_view.select_image(request.files["image"])
    if upload_view.submit_image():
        ...
"""

from web_interface.exceptions import InvalidUploadError


class WasteUploadView:
    """Handles selecting and submitting a waste image."""

    DEFAULT_MAX_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB, same limit as the Flask app
    VALID_STATUSES = (
        "Not Uploaded",
        "Uploaded",
        "Invalid Image",
        "Successfully Uploaded",
        "No Image Selected",
    )

    # ------------------------------------------------------------------
    # 1. Constructor
    # ------------------------------------------------------------------
    def __init__(self, max_size_bytes: int = DEFAULT_MAX_SIZE_BYTES):
        self._max_size_bytes = None
        self.max_size_bytes = max_size_bytes  # uses the setter -> validated
        self.initialize()

    # ------------------------------------------------------------------
    # 2. Initialisation methods
    # ------------------------------------------------------------------
    def initialize(self) -> None:
        """Reset the view to its empty starting state."""
        self._selected_image = None
        self._image_name = None
        self._image_size = 0
        self._image_type = None
        self._upload_status = "Not Uploaded"
        self._error_message = None

    def to_dict(self) -> dict:
        """Details of the selected image, e.g. for logging or display."""
        return {
            "image_name": self._image_name,
            "image_size": self._image_size,
            "image_type": self._image_type,
            "upload_status": self._upload_status,
        }

    # ------------------------------------------------------------------
    # 3. Getters & setters
    # ------------------------------------------------------------------
    @property
    def selected_image(self):
        return self._selected_image

    @selected_image.setter
    def selected_image(self, image) -> None:
        """Store the image and read its name, size and type (validated)."""
        if image is None or not getattr(image, "filename", None):
            raise InvalidUploadError("No image selected.")

        size = len(image.read())
        image.seek(0)  # rewind, so the image can be read again later
        if size == 0:
            raise InvalidUploadError("The selected image is empty.")
        if size > self._max_size_bytes:
            raise InvalidUploadError("The selected image is too large.")

        self._selected_image = image
        self._image_name = image.filename
        self._image_size = size
        self._image_type = getattr(image, "content_type", None)
        self.upload_status = "Uploaded"

    @property
    def upload_status(self) -> str:
        return self._upload_status

    @upload_status.setter
    def upload_status(self, status: str) -> None:
        if status not in self.VALID_STATUSES:
            raise InvalidUploadError(f"Invalid upload status: {status}")
        self._upload_status = status

    @property
    def max_size_bytes(self) -> int:
        return self._max_size_bytes

    @max_size_bytes.setter
    def max_size_bytes(self, size: int) -> None:
        if not isinstance(size, int) or size <= 0:
            raise InvalidUploadError("Maximum size must be a positive whole number.")
        self._max_size_bytes = size

    # Read-only: these are set automatically from the selected image
    @property
    def image_name(self) -> str | None:
        return self._image_name

    @property
    def image_size(self) -> int:
        return self._image_size

    @property
    def image_type(self) -> str | None:
        return self._image_type

    @property
    def error_message(self) -> str | None:
        return self._error_message

    # ------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------
    def select_image(self, image):
        """Select an image. An invalid image is not stored (status 'Invalid Image')."""
        try:
            self.selected_image = image
            self._error_message = None
        except InvalidUploadError as error:
            self._selected_image = None
            self._error_message = str(error)
            self.upload_status = "Invalid Image"
        return self.selected_image

    def submit_image(self) -> bool:
        """Confirm the upload. Returns False if no valid image was selected."""
        if self.selected_image:
            self.upload_status = "Successfully Uploaded"
            return True
        if self._upload_status != "Invalid Image":
            self.upload_status = "No Image Selected"
        return False


upload_view = WasteUploadView()