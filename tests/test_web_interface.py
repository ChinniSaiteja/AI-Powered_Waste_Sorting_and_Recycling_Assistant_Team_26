"""
Automated tests for the Web Interface classes.
Location: tests/test_web_interface.py

Run from the project root:
    python -m pytest tests/test_web_interface.py -v
"""

import io
import sys
from pathlib import Path

import pytest
from werkzeug.datastructures import FileStorage

# Make "web_interface" importable, the same way app.py sees it:
# <project root>/web_interface_dashboard/web_interface/...
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "web_interface_dashboard"))

from web_interface.analysis_controller import AnalysisController  # noqa: E402
from web_interface.classification_result_view import ClassificationResultView, WasteCategory  # noqa: E402
from web_interface.waste_upload_view import WasteUploadView  # noqa: E402


def make_image(data: bytes = b"fake image bytes", filename: str = "bottle.png",
               content_type: str = "image/png") -> FileStorage:
    """An uploaded file, like the one Flask gives us in request.files."""
    return FileStorage(stream=io.BytesIO(data), filename=filename, content_type=content_type)


@pytest.fixture()
def image():
    return make_image()


@pytest.fixture()
def valid_result():
    """A classification result in the format app.py passes to display_result()."""
    return {
        "waste_name": "Glass jar",
        "category": "recyclable",
        "confidence": 0.94,
        "disposal_instruction": "Glass container: Remove the lid first.",
        "explanation": "Glass can be recycled again and again.",
    }


# ---------------------------------------------------------------------------
# WasteUploadView
# ---------------------------------------------------------------------------

class TestWasteUploadView:

    def test_constructor_sets_empty_starting_state(self):
        view = WasteUploadView()
        assert view.selected_image is None
        assert view.image_size == 0
        assert view.upload_status == "Not Uploaded"

    def test_select_image_stores_name_size_and_type(self, image):
        view = WasteUploadView()
        view.select_image(image)
        assert view.image_name == "bottle.png"
        assert view.image_size == len(b"fake image bytes")
        assert view.image_type == "image/png"
        assert view.upload_status == "Uploaded"

    def test_select_image_rewinds_file_so_it_can_be_read_again(self, image):
        WasteUploadView().select_image(image)
        assert image.read() == b"fake image bytes"

    def test_submit_after_valid_image_succeeds(self, image):
        view = WasteUploadView()
        view.select_image(image)
        assert view.submit_image() is True
        assert view.upload_status == "Successfully Uploaded"

    def test_submit_without_image_fails(self):
        view = WasteUploadView()
        assert view.submit_image() is False
        assert view.upload_status == "No Image Selected"

    @pytest.mark.parametrize("bad_image, message", [
        (None, "No image selected."),
        (make_image(data=b""), "The selected image is empty."),
    ])
    def test_invalid_image_is_not_stored(self, bad_image, message):
        view = WasteUploadView()
        view.select_image(bad_image)
        assert view.selected_image is None
        assert view.upload_status == "Invalid Image"
        assert view.error_message == message
        assert view.submit_image() is False

    def test_image_larger_than_limit_is_rejected(self):
        view = WasteUploadView(max_size_bytes=10)
        view.select_image(make_image(data=b"x" * 11))
        assert view.selected_image is None
        assert view.error_message == "The selected image is too large."

    def test_setters_reject_invalid_values(self):
        view = WasteUploadView()
        with pytest.raises(ValueError):
            view.upload_status = "nonsense"
        with pytest.raises(ValueError):
            view.max_size_bytes = 0

    def test_initialize_resets_the_view(self, image):
        view = WasteUploadView()
        view.select_image(image)
        view.initialize()
        assert view.selected_image is None
        assert view.upload_status == "Not Uploaded"


# ---------------------------------------------------------------------------
# AnalysisController
# ---------------------------------------------------------------------------

class TestAnalysisController:

    def test_constructor_sets_starting_state(self):
        controller = AnalysisController()
        assert controller.request_status == "Not Requested"
        assert controller.error_message is None
        assert controller.allowed_extensions == (".png", ".jpg", ".jpeg")

    @pytest.mark.parametrize("filename", ["bottle.jpg", "bottle.JPEG", "can.png"])
    def test_valid_image_types_are_accepted(self, filename):
        controller = AnalysisController()
        assert controller.validate_upload(b"image data", filename) is True
        assert controller.request_status == "Valid Upload"

    def test_invalid_file_type_is_rejected(self):
        controller = AnalysisController()
        assert controller.validate_upload(b"image data", "document.pdf") is False
        assert controller.request_status == "Invalid Upload"
        assert controller.error_message == "Please upload a valid image file (PNG, JPG, JPEG)."

    def test_missing_image_is_rejected(self):
        controller = AnalysisController()
        assert controller.validate_upload(None, None) is False
        assert controller.error_message == "Please provide both an image and a filename."

    def test_request_analysis_success(self):
        controller = AnalysisController()
        response = controller.request_analysis(b"image data", "bottle.jpg")
        assert response == {"status": "success", "message": "Image is ready for analysis"}
        assert controller.request_status == "Analysis Requested"

    def test_request_analysis_error(self):
        response = AnalysisController().request_analysis(b"image data", "document.pdf")
        assert response["status"] == "error"

    def test_handle_error_records_message_and_status(self):
        controller = AnalysisController()
        controller.handle_error("Classification service unavailable")
        assert controller.request_status == "Error"
        assert controller.error_message == "Classification service unavailable"

    def test_initialize_can_configure_allowed_extensions(self):
        controller = AnalysisController(allowed_extensions=(".PNG",))
        assert controller.allowed_extensions == (".png",)
        assert controller.validate_upload(b"image data", "photo.jpg") is False

    def test_setters_reject_invalid_values(self):
        controller = AnalysisController()
        with pytest.raises(ValueError):
            controller.request_status = "nonsense"
        with pytest.raises(ValueError):
            controller.error_message = "   "
        with pytest.raises(ValueError):
            controller.allowed_extensions = ("png",)  # missing the dot


# ---------------------------------------------------------------------------
# ClassificationResultView
# ---------------------------------------------------------------------------

class TestClassificationResultView:

    def test_constructor_sets_empty_starting_state(self):
        view = ClassificationResultView()
        assert view.waste_name is None
        assert view.category is None
        assert view.confidence == 0.0

    def test_display_result_returns_page_data(self, valid_result):
        page_data = ClassificationResultView().display_result(valid_result)
        assert page_data == {
            "waste_name": "Glass jar",
            "category": "Recyclable",
            "confidence": 0.94,
            "disposal_instruction": "Glass container: Remove the lid first.",
            "explanation": "Glass can be recycled again and again.",
        }

    def test_category_is_converted_to_enum(self, valid_result):
        view = ClassificationResultView()
        view.display_result(valid_result)
        assert view.category is WasteCategory.RECYCLABLE

    @pytest.mark.parametrize("field, bad_value", [
        ("category", "plastic"),
        ("confidence", 1.5),
        ("confidence", "high"),
        ("waste_name", ""),
        ("disposal_instruction", "   "),
    ])
    def test_invalid_result_values_are_rejected(self, valid_result, field, bad_value):
        valid_result[field] = bad_value
        with pytest.raises(ValueError):
            ClassificationResultView().display_result(valid_result)

    def test_new_result_replaces_old_one(self, valid_result):
        view = ClassificationResultView()
        view.display_error("Old error")
        view.display_result(valid_result)
        assert view.error_message is None

    def test_display_error_returns_error_data(self):
        view = ClassificationResultView()
        assert view.display_error("Please select an image.") == {
            "status": "error",
            "message": "Please select an image.",
        }
        assert view.error_message == "Please select an image."