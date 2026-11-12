"""
Home Assignment 4 - Unit tests for Subsystem 4: Data Management (Ha Le Thu)

Run:  pytest -v
Each test uses its own temporary SQLite database (fixture `db`),
so the tests never touch your real MySQL / waste.db data.
"""

import pytest

from database.db import DatabaseManager
from database.exceptions import (DataManagementError, InvalidDataError,
                                 ItemNotFoundError)
from database.models import DisposalRule, WasteCategory, WasteItem


# ---------------------------------------------------------------- fixtures
@pytest.fixture
def db(tmp_path):
    """A fresh database with the 72 Dortmund rules, created before each test."""
    manager = DatabaseManager(engine="sqlite", db_path=str(tmp_path / "test.db"))
    manager.initialize()
    return manager


@pytest.fixture
def recyclable():
    return WasteCategory(1, "recyclable")


# ---------------------------------------------------------------- tests
def test_get_rule_returns_correct_bin(db):
    """A known label returns the right Dortmund bin and instruction."""
    rule = db.get_rule("glass jar")
    assert rule["bin_type"] == "Altglascontainer (glass container)"
    assert rule["category"] == "recyclable"
    assert rule["region"] == "Dortmund"


def test_unknown_label_raises_item_not_found(db):
    """require_rule() raises our own ItemNotFoundError with HTTP status 404."""
    assert db.get_rule("unknown thing") is None
    with pytest.raises(ItemNotFoundError) as error:
        db.require_rule("unknown thing")
    assert error.value.http_status == 404
    assert error.value.to_dict()["error"] == "NOT_FOUND"


def test_setter_rejects_invalid_values(recyclable):
    """Encapsulation: setters reject wrong data with InvalidDataError."""
    item = WasteItem(1, "Glass Jar", recyclable)
    assert item.label == "glass jar"                 # setter normalises the label
    with pytest.raises(InvalidDataError):
        recyclable.name = "plastic"                  # not one of the 3 categories
    with pytest.raises(InvalidDataError):
        item.label = "   "                           # empty label
    with pytest.raises(InvalidDataError):
        DisposalRule(1, item, "Glass container", "")  # empty instruction


@pytest.mark.parametrize("confidence", [1.5, -0.1, "high"])
def test_save_classification_rejects_bad_confidence(db, confidence):
    """Confidence must be a number between 0 and 1, otherwise HTTP 400."""
    with pytest.raises(InvalidDataError) as error:
        db.save_classification("glass jar", confidence=confidence)
    assert error.value.http_status == 400
    assert error.value.field == "confidence"


def test_stats_count_new_classifications(db):
    """Integration: saving results updates the dashboard statistics."""
    assert db.get_stats()["total_items"] == 0
    db.save_classification("glass jar", 0.92)
    db.save_classification("banana peel", 0.88)
    db.save_classification("plastic bottle", 0.41, status="uncertain")
    stats = db.get_stats()
    assert stats["total_items"] == 3
    assert stats["by_category"] == {"recyclable": 2, "compostable": 1, "landfill": 0}
    assert stats["uncertain_count"] == 1


def test_feedback_errors(db):
    """Feedback for an unknown classification or a second feedback is rejected."""
    with pytest.raises(ItemNotFoundError):
        db.save_feedback(999, is_correct=False)
    cid = db.save_classification("glass jar", 0.92)
    db.save_feedback(cid, is_correct=True)
    with pytest.raises(InvalidDataError):           # UNIQUE: only 1 feedback per result
        db.save_feedback(cid, is_correct=False)


def test_all_errors_share_one_base_class():
    """One `except DataManagementError` catches every error of this subsystem."""
    for error_class in (InvalidDataError, ItemNotFoundError):
        assert issubclass(error_class, DataManagementError)
    assert issubclass(InvalidDataError, ValueError)   # still works with old code
