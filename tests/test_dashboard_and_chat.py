"""
Capstone additions to Subsystem 4 (Ha Le Thu): dashboard records/statistics for Kanika.
The AI is MOCKED: no API key, no internet, no cost.
"""

import pytest

from database.db import DatabaseManager
from database.exceptions import InvalidDataError
from database.guidance import GuidanceService
from demo_dashboard_data import create_demo_data
from tests.test_guidance import FakeAIClient


@pytest.fixture
def db(tmp_path):
    manager = DatabaseManager(engine="sqlite", db_path=str(tmp_path / "test.db"))
    manager.initialize()
    return manager


# ---------------------------------------------------------------- dashboard
def test_records_have_all_dashboard_fields(db):
    """One record joins result + category + Dortmund rule + cached AI explanation."""
    GuidanceService(db, client=FakeAIClient("Return it for 25 cent.")).explain("plastic bottle")
    cid = db.save_classification("plastic bottle", 0.94)
    record = db.get_classification_records()[0]
    assert record["id"] == cid
    assert record["waste_name"] == "Plastic bottle"
    assert record["category"] == "recyclable"
    assert record["confidence"] == 0.94
    assert record["is_deposit"] is True
    assert "Pfand" in record["bin_type"]
    assert record["disposal_instruction"]
    assert record["explanation"] == "Return it for 25 cent."
    assert record["status"] == "completed"
    assert record["created_at"]


def test_records_newest_first_limit_and_region(db):
    db.save_classification("newspaper", 0.9, created_at="2026-11-01 10:00:00")
    db.save_classification("glass jar", 0.9, created_at="2026-11-10 10:00:00")
    db.save_classification("diaper", 0.9, region="Bochum", created_at="2026-11-11 10:00:00")
    records = db.get_classification_records("Dortmund", limit=1)
    assert [r["label"] for r in records] == ["glass jar"]
    assert len(db.get_classification_records(region=None)) == 3
    with pytest.raises(InvalidDataError):
        db.get_classification_records(limit=0)


def test_unknown_label_record_has_no_rule(db):
    db.save_classification("rubber duck", 0.7)
    record = db.get_classification_records()[0]
    assert record["category"] is None and record["bin_type"] is None


def test_stats_percentages_top_items_and_regions(db):
    for label in ("newspaper", "glass jar", "glass jar", "banana peel"):
        db.save_classification(label, 0.9)
    db.save_classification("diaper", 0.4, status="uncertain")
    db.save_classification("newspaper", 0.9, region="Bochum")

    stats = db.get_stats()
    assert stats["total_items"] == 5
    assert stats["by_category"] == {"recyclable": 3, "compostable": 1, "landfill": 1}
    assert stats["category_percentages"] == {"recyclable": 60.0, "compostable": 20.0, "landfill": 20.0}
    assert stats["recycling_rate"] == 0.6
    assert stats["top_items"][0] == {"label": "glass jar", "waste_name": "Glass jar", "count": 2}
    assert stats["region_counts"] == {"Dortmund": 5}

    everything = db.get_stats(region=None)
    assert everything["region"] == "All regions"
    assert everything["total_items"] == 6
    assert everything["region_counts"] == {"Dortmund": 5, "Bochum": 1}


def test_demo_data_fills_the_dashboard(db):
    create_demo_data(db, count=100)
    stats = db.get_stats(region=None)
    assert stats["total_items"] == 100
    assert sum(stats["category_percentages"].values()) == pytest.approx(100, abs=0.2)
