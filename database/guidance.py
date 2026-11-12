"""
Subsystem 4 - Data Management & AI Guidance
Owner: Ha Le Thu

GuidanceService: disposal guidance + a short AI explanation for each result.

Flow of explain(label):
    1. look up the Dortmund rule in the database           (DatabaseManager.get_rule)
    2. cached AI answer for this item?  -> return it        (no API call, no cost)
    3. no API key / daily limit reached -> fallback text    (the official rule)
    4. otherwise call the AI, cache the answer, count the call
    5. if the AI call fails             -> fallback text    (the app never breaks)

Works with OpenAI or any OpenAI-compatible provider (Groq, Gemini).
Settings in .env (no code change to switch provider):
    AI_API_KEY=...            (or OPENAI_API_KEY)
    AI_BASE_URL=...           empty = OpenAI, e.g. https://api.groq.com/openai/v1
    AI_MODEL=...              e.g. gpt-4o-mini, llama-3.3-70b-versatile
    AI_DAILY_LIMIT=200
"""

import os
from datetime import date

from database.db import DatabaseManager
from database.exceptions import InvalidDataError
from database.models import DisposalRule


class GuidanceService:
    """Combines the database rules with short AI explanations."""

    DEFAULT_MODEL = "gpt-4o-mini"
    MAX_QUESTION_LENGTH = 300
    DEFAULT_SYSTEM_PROMPT = "You are a helpful recycling assistant for German cities."
    CHAT_SYSTEM_PROMPT = (
        "You are a friendly recycling assistant for {region}, Germany. Only answer questions "
        "about waste sorting, recycling and reducing waste. If the question is about another "
        "topic, politely say you can only help with waste and recycling. Never contradict the "
        "official local rule you are given. Answer in plain English in at most 3 short sentences."
    )
    FALLBACK_ANSWER = ("The AI assistant is not available right now. Please follow the disposal "
                       "instruction above or check the EDG Dortmund website (www.edg.de).")

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
        # NFR "AI answer < 5 s": no automatic retries (a retry after a timeout or a
        # rate limit can make the user wait 30 s). If the AI is slow -> fallback text.
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

    def ask(self, question: str, label: str | None = None,
            region: str = DisposalRule.DEFAULT_REGION) -> dict:
        """Answer a citizen's follow-up question (chat box on the result page).

        Returns {"answer": str, "source": "cache" | "ai" | "fallback", "ai_generated": bool}
        Only the question, the item label and the official rule are sent to the AI.
        """
        question = str(question or "").strip()
        if not question:
            raise InvalidDataError("question", question, "must not be empty")
        if len(question) > self.MAX_QUESTION_LENGTH:
            raise InvalidDataError("question", question[:30] + "...",
                                   f"must be at most {self.MAX_QUESTION_LENGTH} characters")
        label = label.strip().lower() if label else None
        rule = self.__db.get_rule(label, region) if label else None

        if label:
            cached = self.__db.get_cached_guidance(label, question)
            if cached:
                return self.__answer(cached, "cache")

        today = date.today().isoformat()
        if not self.ai_enabled or self.__db.get_ai_usage(today) >= self.__daily_limit:
            return self.__answer(self.FALLBACK_ANSWER, "fallback")

        context = ""
        if rule:
            context = (f"The citizen is asking about '{label}'. Official rule: "
                       f"'{rule['bin_type']}' - {rule['instruction']} ")
        elif label:
            context = f"The citizen is asking about '{label}' (no official rule stored). "
        try:
            answer = self.__ask_model(f"{context}Question: {question}",
                                      self.CHAT_SYSTEM_PROMPT.format(region=region))
        except Exception:
            return self.__answer(self.FALLBACK_ANSWER, "fallback")

        self.__db.increment_ai_usage(today)
        if rule is not None:
            self.__db.save_guidance(label, answer, question)
        return self.__answer(answer, "ai")

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

    def __ask_model(self, prompt: str, system_prompt: str | None = None) -> str:
        response = self.__client.chat.completions.create(
            model=self.__model,
            messages=[
                {"role": "system", "content": system_prompt or self.DEFAULT_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            # newer "reasoning" models (e.g. Gemini) use tokens for thinking first;
            # too small a limit cuts answers off. Change with AI_MAX_TOKENS in .env.
            max_tokens=int(os.getenv("AI_MAX_TOKENS", "1500")),
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

    @staticmethod
    def __answer(text: str, source: str) -> dict:
        return {"answer": text, "source": source, "ai_generated": source in ("ai", "cache")}
