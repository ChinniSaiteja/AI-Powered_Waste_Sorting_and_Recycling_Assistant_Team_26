import json

import pytest

from classifier import ClassifierConfig, WasteDetector

EXPECTED_FIELDS = {"status", "count", "objects", "message", "inference_ms"}
OBJECT_FIELDS = {"label", "category", "confidence", "bounding_box", "status"}


def test_finds_every_object_with_box_and_category(make_detector, jpeg_bytes):
    result = make_detector().detect_dict(jpeg_bytes)
    assert result["status"] == "completed"
    assert result["count"] == 2
    bottle, can = result["objects"]
    assert bottle == {
        "label": "plastic bottle",
        "category": "recyclable",
        "confidence": 0.41,
        "bounding_box": [10, 5, 20, 40],
        "status": "completed",
    }
    assert can["label"] == "aluminium can"


def test_objects_are_sorted_by_confidence(make_detector, jpeg_bytes):
    detections = [("tin can", 0.25, (0, 0, 5, 5)), ("banana peel", 0.6, (30, 30, 5, 5))]
    labels = [o["label"] for o in make_detector(detections=detections).detect_dict(jpeg_bytes)["objects"]]
    assert labels == ["banana peel", "tin can"]


def test_low_score_object_is_uncertain(make_detector, jpeg_bytes):
    detections = [("glass jar", 0.4, (0, 0, 10, 10)), ("diaper", 0.1, (30, 30, 10, 10))]
    objects = make_detector(detections=detections).detect_dict(jpeg_bytes)["objects"]
    assert [o["status"] for o in objects] == ["completed", "uncertain"]


def test_only_low_scores_make_whole_result_uncertain(make_detector, jpeg_bytes):
    result = make_detector(detections=[("glass jar", 0.1, (0, 0, 10, 10))]).detect_dict(jpeg_bytes)
    assert result["status"] == "uncertain"
    assert result["count"] == 1


def test_scores_below_minimum_are_dropped(make_detector, jpeg_bytes):
    result = make_detector(detections=[("glass jar", 0.01, (0, 0, 10, 10))]).detect_dict(jpeg_bytes)
    assert result["count"] == 0


def test_nothing_found_is_uncertain(make_detector, jpeg_bytes):
    result = make_detector(detections=[]).detect_dict(jpeg_bytes)
    assert result["status"] == "uncertain"
    assert result["objects"] == []
    assert "No waste item" in result["message"]


def test_overlapping_boxes_count_as_one_object(make_detector, jpeg_bytes):
    detections = [
        ("glass bottle", 0.30, (10, 10, 20, 40)),
        ("plastic bottle", 0.45, (11, 10, 20, 40)),  # same item, better label
        ("tin can", 0.35, (50, 10, 10, 10)),
    ]
    labels = [o["label"] for o in make_detector(detections=detections).detect_dict(jpeg_bytes)["objects"]]
    assert labels == ["plastic bottle", "tin can"]


def test_max_objects_limit(make_detector, jpeg_bytes):
    detections = [("tin can", 0.3, (i * 20, 0, 10, 10)) for i in range(5)]
    detector = make_detector(ClassifierConfig(max_objects=2), detections=detections)
    assert detector.detect_dict(jpeg_bytes)["count"] == 2


def test_invalid_image_does_not_call_model(make_detector):
    detector = make_detector()
    result = detector.detect_dict(b"not an image")
    assert result["status"] == "invalid_image"
    assert result["objects"] == []
    assert detector.model.calls == 0


def test_model_crash_returns_error_status(make_detector, jpeg_bytes):
    result = make_detector(error=RuntimeError("CUDA out of memory")).detect_dict(jpeg_bytes)
    assert result["status"] == "error"
    assert "CUDA" not in result["message"]


def test_output_always_has_fixed_fields(make_detector, jpeg_bytes):
    detector = make_detector()
    for source in (jpeg_bytes, b"", b"junk"):
        result = detector.detect_dict(source)
        assert set(result) == EXPECTED_FIELDS
        for obj in result["objects"]:
            assert set(obj) == OBJECT_FIELDS


def test_output_is_json_serialisable(make_detector, jpeg_file):
    json.dumps(make_detector().detect_dict(jpeg_file))


def test_model_sees_full_size_image(make_detector, tmp_path):
    # no 224x224 crop, otherwise the boxes would not match the uploaded photo
    from PIL import Image

    path = tmp_path / "wide.png"
    Image.new("RGB", (640, 480)).save(path)
    detector = make_detector()
    detector.detect(path)
    assert detector.model.last_image_size == (640, 480)


def test_threshold_setter(make_detector, jpeg_bytes):
    detector = make_detector()
    detector.detection_threshold = 0.9
    assert detector.detect_dict(jpeg_bytes)["status"] == "uncertain"
    with pytest.raises(ValueError):
        detector.detection_threshold = 2


@pytest.mark.parametrize(
    "box_a, box_b, expected",
    [
        ((0, 0, 10, 10), (0, 0, 10, 10), 1.0),
        ((0, 0, 10, 10), (20, 20, 10, 10), 0.0),
        ((0, 0, 10, 10), (5, 0, 10, 10), 50 / 150),
    ],
)
def test_iou(box_a, box_b, expected):
    assert WasteDetector.iou(box_a, box_b) == pytest.approx(expected)
