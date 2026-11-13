"""
Subsystem 4 - Data Management & AI Guidance
Owner: Ha Le Thu

GuidanceService: disposal guidance + a short AI explanation for each result.

explain(label): cache -> AI (if a key is set and under the daily limit) -> fallback
to the official rule. The app never breaks, even without an AI key.

Works with OpenAI or any OpenAI-compatible provider (Groq, Gemini); set
AI_API_KEY, AI_BASE_URL, AI_MODEL, AI_DAILY_LIMIT in .env, no code change needed.
"""

import os
from datetime import date

from database.db import DatabaseManager
from database.exceptions import InvalidDataError
from database.models import DisposalRule


class GuidanceService:
    """Combines the database rules with short AI explanations."""

    DEFAULT_MODEL = "gpt-4o-mini"
    DEFAULT_SYSTEM_PROMPT = "You are a helpful recycling assistant for German cities."

    # 1. Constructor
    def __init__(self, db: DatabaseManager, client=None, daily_limit: int | None = None,
                 model: str | None = None):
        self.__db = db
        self.__model = model or os.getenv("AI_MODEL", self.DEFAULT_MODEL)
        self.daily_limit = daily_limit if daily_limit is not None else int(os.getenv("AI_DAILY_LIMIT", "200"))
        # client can be passed in (tests use a fake one); otherwise built from .env
        self.__client = client if client is not None else self.__create_client()

    # 2. Initialisation method
    @staticmethod
    def __create_client():
        """Create the OpenAI client from .env, or return None if no key is set."""
        api_key = os.getenv("AI_API_KEY") or os.getenv("OPENAI_API_KEY")
        if not api_key:
            return None
        try:
            from openai import OpenAI
        except ImportError:
            return None
        base_url = os.getenv("AI_BASE_URL") or None
        # no retries, so a slow AI falls back quickly instead of making the user wait
        timeout = float(os.getenv("AI_TIMEOUT", "8"))
        return OpenAI(api_key=api_key, base_url=base_url, timeout=timeout, max_retries=0)

    # 3. Getters & setters
    @property
    def daily_limit(self) -> int:
        return self.__daily_limit

    @daily_limit.setter
    def daily_limit(self, value: int) -> None:
        if not isinstance(value, int) or value < 0:
            raise InvalidDataError("daily_limit", value, "must be an integer >= 0")
        self.__daily_limit = value

    @property
    def model(self) -> str:
        return self.__model

    @property
    def ai_enabled(self) -> bool:
        return self.__client is not None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def get_guidance(self, label: str, region: str = DisposalRule.DEFAULT_REGION) -> dict:
        """Rule + explanation in one dict - what the backend sends to the web page."""
        rule = self.__db.get_rule(label, region)
        explanation = self.explain(label, region, rule=rule)
        return {"label": label.strip().lower(), "rule": rule, **explanation}

    def explain(self, label: str, region: str = DisposalRule.DEFAULT_REGION,
                rule: dict | None = None) -> dict:
        """Short explanation for one item.

        Returns {"explanation": str, "source": "cache" | "ai" | "fallback", "ai_generated": bool}
        """
        label = label.strip().lower()
        if rule is None:
            rule = self.__db.get_rule(label, region)

        cached = self.__db.get_cached_guidance(label)
        if cached:
            return self.__result(cached, "cache")

        today = date.today().isoformat()
        if not self.ai_enabled or self.__db.get_ai_usage(today) >= self.__daily_limit:
            return self.__fallback(label, rule)

        try:
            answer = self.__ask_model(self.__build_prompt(label, region, rule))
        except Exception:
            # network error, wrong key, provider down ... -> never break the app
            return self.__fallback(label, rule)

        self.__db.increment_ai_usage(today)
        if rule is not None:                      # only cache items we know
            self.__db.save_guidance(label, answer)
        return self.__result(answer, "ai")

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------
    @staticmethod
    def __build_prompt(label: str, region: str, rule: dict | None) -> str:
        if rule:
            return (
                f"A citizen in {region}, Germany, wants to throw away: '{label}'. "
                f"Official rule: put it in '{rule['bin_type']}'. Instruction: {rule['instruction']} "
                "In 2 short, friendly sentences, explain why this is the right bin "
                "and give one practical tip. Plain English, no lists."
            )
        return (
            f"A citizen in {region}, Germany, wants to throw away: '{label}'. "
            "We have no official rule for this item. In 2 short sentences, suggest the most "
            "likely bin in Germany (yellow, blue, brown, grey bin, glass container or "
            "Recyclinghof) and say they should check the local waste company website."
        )

    def __ask_model(self, prompt: str) -> str:
        response = self.__client.chat.completions.create(
            model=self.__model,
            messages=[
                {"role": "system", "content": self.DEFAULT_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            max_tokens=int(os.getenv("AI_MAX_TOKENS", "1500")),  # Gemini needs more room than GPT
            temperature=0.3,
        )
        answer = (response.choices[0].message.content or "").strip()
        if not answer:
            raise ValueError("empty AI answer")
        return answer

    def __fallback(self, label: str, rule: dict | None) -> dict:
        if rule:
            text = f"{rule['bin_type']}: {rule['instruction']}"
        else:
            text = (f"We don't have a rule for '{label}' yet. "
                    "Please check the EDG Dortmund website (www.edg.de).")
        return self.__result(text, "fallback")

    @staticmethod
    def __result(text: str, source: str) -> dict:
        return {"explanation": text, "source": source, "ai_generated": source in ("ai", "cache")}
