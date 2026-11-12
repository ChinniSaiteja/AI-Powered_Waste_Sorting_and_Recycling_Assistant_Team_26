"""
Subsystem 4 - Data Management & AI Guidance
Owner: Ha Le Thu

Home Assignment 1: Object-Oriented Concepts
Domain classes that mirror the database tables:

    WasteCategory   <->  waste_categories
    WasteItem       <->  waste_items
    DisposalRule    <->  disposal_rules

Every class has:
    1. a constructor (__init__)          -> state initialisation
    2. initialisation methods            -> from_dict() / validate() / to_dict()
    3. encapsulation (getters & setters) -> private attributes + @property

Invalid values raise InvalidDataError (see exceptions.py, Home Assignment 4).
"""

from database.exceptions import InvalidDataError


class WasteCategory:
    """One of the three classifier categories."""

    ALLOWED_NAMES = ("recyclable", "compostable", "landfill")

    # 1. Constructor
    def __init__(self, category_id: int | None, name: str, description: str = ""):
        self.__id = category_id
        self.name = name                # uses the setter -> validated
        self.description = description

    # 2. Initialisation methods
    @classmethod
    def from_dict(cls, data: dict, category_id: int | None = None) -> "WasteCategory":
        """Create a category from a JSON / database row."""
        return cls(data.get("id", category_id), data["name"], data.get("description", ""))

    def to_dict(self) -> dict:
        return {"id": self.__id, "name": self.__name, "description": self.__description}

    # 3. Getters & setters
    @property
    def id(self) -> int | None:
        return self.__id

    @id.setter
    def id(self, value: int) -> None:
        if not isinstance(value, int) or value <= 0:
            raise InvalidDataError("id", value, "must be a positive integer")
        self.__id = value

    @property
    def name(self) -> str:
        return self.__name

    @name.setter
    def name(self, value: str) -> None:
        value = str(value).strip().lower()
        if value not in self.ALLOWED_NAMES:
            raise InvalidDataError("category", value, f"allowed: {', '.join(self.ALLOWED_NAMES)}")
        self.__name = value

    @property
    def description(self) -> str:
        return self.__description

    @description.setter
    def description(self, value: str) -> None:
        self.__description = str(value or "").strip()

    def __str__(self) -> str:
        return f"WasteCategory(id={self.__id}, name={self.__name})"


class WasteItem:
    """A concrete waste item that the classifier can recognise, e.g. 'glass jar'."""

    # 1. Constructor
    def __init__(self, item_id: int | None, label: str, category: WasteCategory,
                 is_deposit: bool = False):
        self.__id = item_id
        self.label = label
        self.category = category
        self.is_deposit = is_deposit

    # 2. Initialisation methods
    @classmethod
    def from_dict(cls, data: dict, category: WasteCategory,
                  item_id: int | None = None) -> "WasteItem":
        """Create an item from one entry of waste_guidance.json."""
        return cls(data.get("id", item_id), data["label"], category,
                   bool(data.get("is_deposit", False)))

    def to_dict(self) -> dict:
        return {
            "id": self.__id,
            "label": self.__label,
            "category": self.__category.name,
            "is_deposit": self.__is_deposit,
        }

    # 3. Getters & setters
    @property
    def id(self) -> int | None:
        return self.__id

    @id.setter
    def id(self, value: int) -> None:
        if not isinstance(value, int) or value <= 0:
            raise InvalidDataError("id", value, "must be a positive integer")
        self.__id = value

    @property
    def label(self) -> str:
        return self.__label

    @label.setter
    def label(self, value: str) -> None:
        # labels must match the classifier output exactly -> lowercase, no extra spaces
        value = str(value).strip().lower()
        if not value:
            raise InvalidDataError("label", value, "must not be empty")
        if len(value) > 100:
            raise InvalidDataError("label", value, "must be at most 100 characters")
        self.__label = value

    @property
    def category(self) -> WasteCategory:
        return self.__category

    @category.setter
    def category(self, value: WasteCategory) -> None:
        if not isinstance(value, WasteCategory):
            raise InvalidDataError("category", value, "must be a WasteCategory object")
        self.__category = value

    @property
    def is_deposit(self) -> bool:
        return self.__is_deposit

    @is_deposit.setter
    def is_deposit(self, value: bool) -> None:
        if not isinstance(value, bool):
            raise InvalidDataError("is_deposit", value, "must be True or False")
        self.__is_deposit = value

    def __str__(self) -> str:
        deposit = " [Pfand]" if self.__is_deposit else ""
        return f"WasteItem({self.__label} -> {self.__category.name}{deposit})"


class DisposalRule:
    """Where and how to dispose of one WasteItem in one region."""

    DEFAULT_REGION = "Dortmund"

    # 1. Constructor
    def __init__(self, rule_id: int | None, item: WasteItem, bin_type: str,
                 instruction: str, region: str = DEFAULT_REGION):
        self.__id = rule_id
        self.item = item
        self.bin_type = bin_type
        self.instruction = instruction
        self.region = region

    # 2. Initialisation methods
    @classmethod
    def from_dict(cls, data: dict, item: WasteItem, region: str = DEFAULT_REGION,
                  rule_id: int | None = None) -> "DisposalRule":
        """Create a rule from one entry of waste_guidance.json."""
        return cls(data.get("rule_id", rule_id), item, data["bin_type"],
                   data["instruction"], data.get("region", region))

    def to_dict(self) -> dict:
        """Format the backend sends to the web interface."""
        return {
            "label": self.__item.label,
            "category": self.__item.category.name,
            "is_deposit": self.__item.is_deposit,
            "region": self.__region,
            "bin_type": self.__bin_type,
            "instruction": self.__instruction,
        }

    # 3. Getters & setters
    @property
    def id(self) -> int | None:
        return self.__id

    @id.setter
    def id(self, value: int) -> None:
        if not isinstance(value, int) or value <= 0:
            raise InvalidDataError("id", value, "must be a positive integer")
        self.__id = value

    @property
    def item(self) -> WasteItem:
        return self.__item

    @item.setter
    def item(self, value: WasteItem) -> None:
        if not isinstance(value, WasteItem):
            raise InvalidDataError("item", value, "must be a WasteItem object")
        self.__item = value

    @property
    def bin_type(self) -> str:
        return self.__bin_type

    @bin_type.setter
    def bin_type(self, value: str) -> None:
        value = str(value).strip()
        if not value:
            raise InvalidDataError("bin_type", value, "must not be empty")
        self.__bin_type = value

    @property
    def instruction(self) -> str:
        return self.__instruction

    @instruction.setter
    def instruction(self, value: str) -> None:
        value = str(value).strip()
        if not value:
            raise InvalidDataError("instruction", value, "must not be empty")
        self.__instruction = value

    @property
    def region(self) -> str:
        return self.__region

    @region.setter
    def region(self, value: str) -> None:
        value = str(value).strip().title()
        if not value:
            raise InvalidDataError("region", value, "must not be empty")
        self.__region = value

    def __str__(self) -> str:
        return f"DisposalRule({self.__item.label} @ {self.__region}: {self.__bin_type})"
