"""Home Assignment 4 - Flask tests of the classifier routes (Azam Rahmani).

Uses Flask's test client and fake models, so no model download is needed.
"""

import io

import pytest

from classifier.api import create_app
from tests.conftest import FakeDetectionModel, FakeModel


@pytest.fixture
def make_client():
    from classifier import WasteClassifier, WasteDetector

    def _make(model=None, detection_model=None):
        app = create_app(WasteClassifier(model=model or FakeModel()),
                         WasteDetector(model=detection_model or FakeDetectionModel()))
        app.config["TESTING"] = True
        return app.test_client()

    return _make


def upload(data, name="item.jpg"):
    return {"image": (io.BytesIO(data), name)}


def test_health(make_client):
    response = make_client().get("/api/classifier/health")
    assert response.status_code == 200
    assert response.get_json()["labels"] == 23


def test_classify_returns_label_and_category(make_client, jpeg_bytes):
    response = make_client().post("/api/classifier/classify", data=upload(jpeg_bytes),
                                  content_type="multipart/form-data")
    assert response.status_code == 200
    body = response.get_json()
    assert (body["status"], body["label"], body["category"]) == ("completed", "glass jar", "recyclable")


def test_low_confidence_is_still_a_valid_response(make_client, jpeg_bytes):
    client = make_client(model=FakeModel(confidence=0.2))
    response = client.post("/api/classifier/classify", data=upload(jpeg_bytes),
                           content_type="multipart/form-data")
    assert response.status_code == 200
    assert response.get_json()["status"] == "uncertain"


def test_missing_file_gives_400_with_error_code(make_client):
    response = make_client().post("/api/classifier/classify", data={},
                                  content_type="multipart/form-data")
    assert response.status_code == 400
    assert response.get_json()["error"] == "INVALID_IMAGE"


def test_broken_file_gives_400(make_client):
    response = make_client().post("/api/classifier/classify", data=upload(b"not an image"),
                                  content_type="multipart/form-data")
    assert response.status_code == 400
    assert response.get_json()["status"] == "invalid_image"


def test_model_crash_gives_503_without_internal_details(make_client, jpeg_bytes):
    client = make_client(model=FakeModel(error=RuntimeError("CUDA out of memory")))
    response = client.post("/api/classifier/classify", data=upload(jpeg_bytes),
                           content_type="multipart/form-data")
    assert response.status_code == 503
    assert "CUDA" not in response.get_data(as_text=True)


def test_detect_returns_objects_with_bounding_boxes(make_client, jpeg_bytes):
    response = make_client().post("/api/classifier/detect", data=upload(jpeg_bytes),
                                  content_type="multipart/form-data")
    assert response.status_code == 200
    objects = response.get_json()["objects"]
    assert [o["label"] for o in objects] == ["plastic bottle", "aluminium can"]
    assert objects[0]["bounding_box"] == [10, 5, 20, 40]


def test_detect_broken_file_gives_400(make_client):
    response = make_client().post("/api/classifier/detect", data=upload(b""),
                                  content_type="multipart/form-data")
    assert response.status_code == 400


def test_detector_crash_gives_503(make_client, jpeg_bytes):
    client = make_client(detection_model=FakeDetectionModel(error=OSError("weights not found")))
    response = client.post("/api/classifier/detect", data=upload(jpeg_bytes),
                           content_type="multipart/form-data")
    assert response.status_code == 503
    assert response.get_json()["message"] == "The detector is currently unavailable"


def test_get_on_classify_is_not_allowed(make_client):
    assert make_client().get("/api/classifier/classify").status_code == 405
