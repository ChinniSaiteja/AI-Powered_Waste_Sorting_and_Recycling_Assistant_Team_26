from enum import Enum


class WasteCategory(Enum):
    RECYCLABLE = "Recyclable"
    COMPOSTABLE = "Compostable"
    LANDFILL = "Landfill"


class ClassificationResultView:


    def __init__(self):
        self._waste_name = None
        self._category = None
        self._confidence = 0.0
        self._disposal_instruction = None
        self._explanation = None
        self._error_message = None

    @property
    def waste_name(self):
        return self._waste_name

    @property
    def category(self):
        return self._category

    @property
    def confidence(self):
        return self._confidence

    @property
    def disposal_instruction(self):
        return self._disposal_instruction

    @property
    def explanation(self):
        return self._explanation

    @property
    def error_message(self):
        return self._error_message

    def display_result(self, result):
        self._waste_name = result["waste_name"]
        self._category = WasteCategory[result["category"].upper()]
        self._confidence = float(result["confidence"])
        self._disposal_instruction = result["disposal_instruction"]
        self._explanation = result["explanation"]
        self._error_message = None

        return {
            "waste_name": self._waste_name,
            "category": self._category.value,
            "confidence": self._confidence,
            "disposal_instruction": self._disposal_instruction,
            "explanation": self._explanation
        }

    def display_error(self, message):
        self._error_message = message

        return {
            "status": "error",
            "message": self._error_message
        }