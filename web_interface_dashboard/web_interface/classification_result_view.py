"""
Subsystem - Web Interface & Municipality Dashboard
Owner: Kanika Sehgal

ClassificationResultView: stores the classification result for one image
(waste name, category, confidence, disposal instruction, AI explanation)
and returns it in the format the web page displays - or an error message.

Usage (in the Flask app):
    result_view = ClassificationResultView()
    page_data = result_view.display_result(classification)   # -> dict
    error_data = result_view.display_error("Please select an image.")
"""

from enum import Enum

from web_interface.exceptions import InvalidResultError


class WasteCategory(Enum):
    """The three waste categories used by the whole project."""

    RECYCLABLE = "Recyclable"
    COMPOSTABLE = "Compostable"
    LANDFILL = "Landfill"


class ClassificationResultView:
    """Holds one classification result or an error for display."""

    # ------------------------------------------------------------------
    # 1. Constructor
    # ------------------------------------------------------------------
    def __init__(self):
        self.initialize()

    # ------------------------------------------------------------------
    # 2. Initialisation methods
    # ------------------------------------------------------------------
    def initialize(self) -> None:
        """Clear any previous result, so the view can show a new one."""
        self._waste_name = None
        self._category = None
        self._confidence = 0.0
        self._disposal_instruction = None
        self._explanation = None
        self._error_message = None

    def to_dict(self) -> dict:
        """The result in the format the web page displays."""
        return {
            "waste_name": self._waste_name,
            "category": self._category.value if self._category else None,
            "confidence": self._confidence,
            "disposal_instruction": self._disposal_instruction,
            "explanation": self._explanation,
        }

    # ------------------------------------------------------------------
    # 3. Getters & setters
    # ------------------------------------------------------------------
    @property
    def waste_name(self) -> str | None:
        return self._waste_name

    @waste_name.setter
    def waste_name(self, name: str) -> None:
        if not isinstance(name, str) or not name.strip():
            raise InvalidResultError("Waste name must be a non-empty string.")
        self._waste_name = name.strip()

    @property
    def category(self) -> WasteCategory | None:
        return self._category

    @category.setter
    def category(self, category) -> None:
        """Accepts a WasteCategory or its name as text, e.g. 'recyclable'."""
        if isinstance(category, WasteCategory):
            self._category = category
            return
        try:
            self._category = WasteCategory[str(category).strip().upper()]
        except KeyError:
            raise InvalidResultError(f"Unknown waste category: {category}") from None

    @property
    def confidence(self) -> float:
        return self._confidence

    @confidence.setter
    def confidence(self, value) -> None:
        try:
            value = float(value)
        except (TypeError, ValueError):
            raise InvalidResultError("Confidence must be a number.") from None
        if not 0.0 <= value <= 1.0:
            raise InvalidResultError("Confidence must be between 0 and 1.")
        self._confidence = value

    @property
    def disposal_instruction(self) -> str | None:
        return self._disposal_instruction

    @disposal_instruction.setter
    def disposal_instruction(self, text: str) -> None:
        if not isinstance(text, str) or not text.strip():
            raise InvalidResultError("Disposal instruction must be a non-empty string.")
        self._disposal_instruction = text.strip()

    @property
    def explanation(self) -> str | None:
        return self._explanation

    @explanation.setter
    def explanation(self, text) -> None:
        if text is not None and not isinstance(text, str):
            raise InvalidResultError("Explanation must be text or None.")
        self._explanation = text

    @property
    def error_message(self) -> str | None:
        return self._error_message

    @error_message.setter
    def error_message(self, message: str | None) -> None:
        if message is not None and (not isinstance(message, str) or not message.strip()):
            raise InvalidResultError("Error message must be a non-empty string or None.")
        self._error_message = message

    # ------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------
    def display_result(self, result: dict) -> dict:
        """Validate and store a classification result, return it for the page."""
        self.initialize()
        self.waste_name = result["waste_name"]
        self.category = result["category"]
        self.confidence = result["confidence"]
        self.disposal_instruction = result["disposal_instruction"]
        self.explanation = result["explanation"]
        return self.to_dict()

    def display_error(self, message: str) -> dict:
        """Store an error message and return it for the page."""
        self.error_message = message
        return {
            "status": "error",
            "message": self.error_message,
        }