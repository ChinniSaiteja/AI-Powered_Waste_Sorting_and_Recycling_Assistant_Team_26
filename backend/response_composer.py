"""
Composes the final response returned to the web interface.
"""

from .exceptions import ResponseCompositionError


class ResponseComposer:
    """
    Combines classification and guidance information
    into the structure expected by the frontend.
    """

    def __init__(self):
        self._initialized = False

    @property
    def initialized(self) -> bool:
        """Return whether the composer has been initialized."""
        return self._initialized

    def initialize(self) -> None:
        """Initialize the response composer."""
        self._initialized = True

    def compose(
        self,
        classification: dict,
        guidance: dict,
        classification_id: int,
    ) -> dict:
        """
        Build the final response for the frontend.

        Parameters
        ----------
        classification:
            Normalized classifier result.

        guidance:
            Result returned by the guidance service.

        classification_id:
            ID returned after saving the classification.
        """

        if not isinstance(classification, dict):
            raise ResponseCompositionError(
                "Classification data must be a dictionary."
            )

        if not isinstance(guidance, dict):
            raise ResponseCompositionError(
                "Guidance data must be a dictionary."
            )

        if classification_id is None:
            raise ResponseCompositionError(
                "Classification ID is required."
            )

        rule = guidance.get("rule") or {}

        category = (
            rule.get("category")
            or classification.get("category")
            or "landfill"
        )

        category = str(category).strip().lower()

        if category not in (
            "recyclable",
            "compostable",
            "landfill",
        ):
            category = "landfill"

        if rule:
            bin_type = rule.get("bin_type", "")
            instruction = rule.get("instruction", "")

            disposal_instruction = (
                f"{bin_type}: {instruction}"
                if bin_type
                else instruction
            )
        else:
            label = classification["label"]

            disposal_instruction = (
                f"No local rule for '{label}' yet. "
                "Please check the EDG Dortmund website (www.edg.de)."
            )

        return {
            "waste_name": classification["label"].capitalize(),
            "category": category,
            "confidence": classification["confidence"],
            "disposal_instruction": disposal_instruction,
            "explanation": guidance.get(
                "explanation",
                "No additional explanation available.",
            ),

            # Additional information used by the frontend.
            "classification_id": classification_id,
            "label": classification["label"],
            "status": classification["status"],
            "message": classification.get("message", ""),
            "bin_type": rule.get("bin_type"),
            "is_deposit": rule.get("is_deposit", False),
            "explanation_ai_generated": guidance.get(
                "ai_generated",
                False,
            ),
            "region": classification["region"],
        }