"""
Unit tests for GuidanceService (AI part) - Ha Le Thu
The AI is MOCKED with a fake client: no API key, no internet, no cost.
"""

import pytest

from database.db import DatabaseManager
from database.exceptions import InvalidDataError
from database.guidance import GuidanceService


class FakeAIClient:
    """Pretends to be the OpenAI client and counts how often it is called."""

    def __init__(self, answer="Glass can be recycled forever. Remove the lid first.", fail=False):
        self.calls = 0
        self.answer = answer
        self.fail = fail
        self.chat = self                 # client.chat.completions.create(...)
        self.completions = self

    def create(self, **kwargs):
        self.calls += 1
        if self.fail:
            raise ConnectionError("AI provider is down")
        message = type("Message", (), {"content": self.answer})
        choice = type("Choice", (), {"message": message})
        return type("Response", (), {"choices": [choice]})


@pytest.fixture
def db(tmp_path):
    manager = DatabaseManager(engine="sqlite", db_path=str(tmp_path / "test.db"))
    manager.initialize()
    return manager


def test_ai_answer_is_cached(db):
    """First call asks the AI, second call comes from the database cache."""
    fake = FakeAIClient()
    service = GuidanceService(db, client=fake)
    first = service.explain("glass jar")
    second = service.explain("glass jar")
    assert first["source"] == "ai" and first["ai_generated"]
    assert second["source"] == "cache"
    assert fake.calls == 1                       # AI was called only once


def test_fallback_without_api_key(db, monkeypatch):
    """No key in .env -> official rule is returned, the app still works."""
    monkeypatch.delenv("AI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    service = GuidanceService(db)
    result = service.explain("battery")
    assert not service.ai_enabled
    assert result["source"] == "fallback"
    assert "Battery collection box" in result["explanation"]


def test_fallback_when_ai_fails_and_limit(db):
    """AI error or daily limit reached -> fallback, never an exception."""
    broken = GuidanceService(db, client=FakeAIClient(fail=True))
    assert broken.explain("glass jar")["source"] == "fallback"

    fake = FakeAIClient()
    limited = GuidanceService(db, client=fake, daily_limit=0)
    assert limited.explain("banana peel")["source"] == "fallback"
    assert fake.calls == 0                       # limit reached -> AI not called
    with pytest.raises(InvalidDataError):
        limited.daily_limit = -5
