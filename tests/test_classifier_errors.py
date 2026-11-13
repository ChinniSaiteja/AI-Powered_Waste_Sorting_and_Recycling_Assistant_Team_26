"""Home Assignment 4 - error-handling class of Subsystem 3 (Azam Rahmani)."""

import logging

import pytest

from classifier import (
    ClassifierConfig,
    ClassifierError,
    ClassifierErrorHandler,
    ClassifierStatus,
    InvalidConfigError,
    InvalidImageError,
    ModelUnavailableError,
)


def test_error_hierarchy():
    assert issubclass(InvalidImageError, ClassifierError)
    assert issubclass(ModelUnavailableError, ClassifierError)
    assert issubclass(InvalidImageError, ValueError)  # old code catching ValueError still works


@pytest.mark.parametrize(
    "error_class, code, http_status, status",
    [
        (InvalidImageError, "INVALID_IMAGE", 400, "invalid_image"),
        (ModelUnavailableError, "MODEL_UNAVAILABLE", 503, "error"),
        (InvalidConfigError, "INVALID_CONFIG", 500, "error"),
    ],
)
def test_each_error_knows_code_http_status_and_status(error_class, code, http_status, status):
    error = error_class("message")
    assert (error.code, error.http_status, error.status.value) == (code, http_status, status)


def test_to_dict_is_the_json_error_body():
    error = InvalidImageError("The uploaded file is empty", {"size": 0})
    assert error.to_dict() == {
        "error": "INVALID_IMAGE",
        "status": "invalid_image",
        "message": "The uploaded file is empty",
        "details": {"size": 0},
    }


def test_details_getter_returns_a_copy():
    error = ClassifierError("x", {"a": 1})
    error.details["a"] = 2
    assert error.details == {"a": 1}


def test_handler_keeps_known_errors():
    error = InvalidImageError("The file is not a readable image")
    assert ClassifierErrorHandler().wrap(error) is error


def test_handler_hides_unexpected_errors(caplog):
    handler = ClassifierErrorHandler("The detector is currently unavailable")
    with caplog.at_level(logging.ERROR):
        status, message = handler.to_status(RuntimeError("CUDA out of memory"))
    assert status is ClassifierStatus.ERROR
    assert message == "The detector is currently unavailable"
    assert "CUDA" not in message                      # nothing internal for the user
    assert "Unexpected error" in caplog.text          # but the full error is logged


def test_handler_counts_errors_per_code():
    handler = ClassifierErrorHandler()
    handler.wrap(InvalidImageError("a"))
    handler.wrap(InvalidImageError("b"))
    handler.wrap(KeyError("c"))
    assert handler.error_counts == {"INVALID_IMAGE": 2, "MODEL_UNAVAILABLE": 1}


def test_handler_message_setter_validates():
    with pytest.raises(ValueError):
        ClassifierErrorHandler(" ")


def test_invalid_config_raises_invalid_config_error():
    with pytest.raises(InvalidConfigError) as info:
        ClassifierConfig(confidence_threshold=1.5)
    assert info.value.details == {"confidence_threshold": 1.5}


def test_classifier_reports_crash_through_handler(make_classifier, jpeg_bytes):
    classifier = make_classifier(error=RuntimeError("model file missing"))
    assert classifier.classify(jpeg_bytes)["status"] == "error"
    assert classifier.error_handler.error_counts == {"MODEL_UNAVAILABLE": 1}
