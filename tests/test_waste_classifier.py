import json

import pytest

from classifier import ClassifierStatus

EXPECTED_FIELDS = {"status", "label", "category", "confidence", "message", "inference_ms"}


def test_confident_prediction(make_classifier, jpeg_bytes):
    result = make_classifier(label="glass jar", confidence=0.92).classify(jpeg_bytes)
    assert result["status"] == "completed"
    assert result["label"] == "glass jar"
    assert result["category"] == "recyclable"
    assert result["confidence"] == 0.92
    assert result["inference_ms"] >= 0


def test_low_confidence_is_flagged_uncertain(make_classifier, jpeg_bytes):
    result = make_classifier(label="banana peel", confidence=0.2).classify(jpeg_bytes)
    assert result["status"] == "uncertain"
    assert result["category"] == "compostable"
    assert "uncertain" in result["message"]


def test_missing_confidence_is_uncertain(make_classifier, jpeg_bytes):
    assert make_classifier(confidence=None).classify(jpeg_bytes)["status"] == "uncertain"


def test_invalid_image_does_not_call_model(make_classifier):
    classifier = make_classifier()
    result = classifier.classify(b"not an image")
    assert result["status"] == "invalid_image"
    assert result["label"] is None
    assert classifier.model.calls == 0


def test_model_crash_returns_error_status(make_classifier, jpeg_bytes):
    result = make_classifier(error=RuntimeError("CUDA out of memory")).classify(jpeg_bytes)
    assert result["status"] == "error"
    assert "CUDA" not in result["message"]  # no internal details leak to the user


def test_output_always_has_fixed_fields(make_classifier, jpeg_bytes):
    classifier = make_classifier()
    for source in (jpeg_bytes, b"", b"junk"):
        assert set(classifier.classify(source)) == EXPECTED_FIELDS


def test_output_is_json_serialisable(make_classifier, jpeg_file):
    json.dumps(make_classifier().classify(jpeg_file))


def test_predict_returns_result_object(make_classifier, jpeg_bytes):
    result = make_classifier().predict(jpeg_bytes)
    assert result.status is ClassifierStatus.COMPLETED
    assert result.is_success


def test_warm_up_does_not_predict(make_classifier):
    classifier = make_classifier()
    classifier.warm_up()
    assert classifier.model.calls == 0


def test_image_is_not_saved_to_disk(make_classifier, jpeg_bytes, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    make_classifier().classify(jpeg_bytes)
    assert list(tmp_path.iterdir()) == []


def test_threshold_setter_changes_status(make_classifier, jpeg_bytes):
    classifier = make_classifier(confidence=0.7)
    classifier.confidence_threshold = 0.8
    assert classifier.classify(jpeg_bytes)["status"] == "uncertain"


def test_threshold_setter_rejects_out_of_range(make_classifier):
    with pytest.raises(ValueError):
        make_classifier().confidence_threshold = 1.5
