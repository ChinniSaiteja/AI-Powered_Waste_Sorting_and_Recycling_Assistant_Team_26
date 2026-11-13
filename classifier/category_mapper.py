from typing import Optional

RECYCLABLE = "recyclable"
COMPOSTABLE = "compostable"
LANDFILL = "landfill"


class CategoryMapper:
    """Maps a predicted item label to one of the three waste categories (FR 6, FR 8).

    The labels are exactly the item labels in Ha's data/waste_guidance.json
    (lowercase, words separated by spaces), so the backend can pass a predicted
    label straight to get_rule(label). The categories match that file too.
    """

    LABEL_TO_CATEGORY = {
        # recyclable
        "plastic bottle": RECYCLABLE,
        "glass bottle": RECYCLABLE,
        "glass jar": RECYCLABLE,
        "aluminium can": RECYCLABLE,
        "tin can": RECYCLABLE,
        "cardboard box": RECYCLABLE,
        "newspaper": RECYCLABLE,
        "paper bag": RECYCLABLE,
        "beverage carton": RECYCLABLE,
        "yogurt cup": RECYCLABLE,
        "chip bag": RECYCLABLE,  # yellow bin in Dortmund
        "styrofoam packaging": RECYCLABLE,  # yellow bin in Dortmund
        # compostable
        "banana peel": COMPOSTABLE,
        "apple core": COMPOSTABLE,
        "food leftovers": COMPOSTABLE,
        "vegetable scraps": COMPOSTABLE,
        "coffee grounds": COMPOSTABLE,
        "eggshell": COMPOSTABLE,
        "tea bag": COMPOSTABLE,
        # landfill
        "diaper": LANDFILL,
        "cigarette butt": LANDFILL,
        "ceramic plate": LANDFILL,
        "used tissue": LANDFILL,
    }

    CATEGORIES = (RECYCLABLE, COMPOSTABLE, LANDFILL)

    def __init__(self, label_to_category: Optional[dict] = None):
        self.label_to_category = label_to_category or self.LABEL_TO_CATEGORY

    @property
    def label_to_category(self) -> dict:
        return dict(self.__label_to_category)

    @label_to_category.setter
    def label_to_category(self, value: dict) -> None:
        if not value:
            raise ValueError("The label mapping must not be empty")
        for label, category in value.items():
            if category not in self.CATEGORIES:
                raise ValueError(f"Unknown category {category!r} for label {label!r}")
        self.__label_to_category = {label.strip().lower(): c for label, c in value.items()}

    @property
    def labels(self) -> list:
        return list(self.__label_to_category)

    @property
    def categories(self) -> list:
        return sorted(set(self.__label_to_category.values()))

    def map_category(self, label: str) -> str:
        """Return the category for a label; unknown labels go to landfill (safe default)."""
        return self.__label_to_category.get(label, LANDFILL)

    @staticmethod
    def check_confidence(confidence: Optional[float], threshold: float) -> bool:
        """True when the prediction is confident enough to show as certain."""
        return confidence is not None and confidence >= threshold
