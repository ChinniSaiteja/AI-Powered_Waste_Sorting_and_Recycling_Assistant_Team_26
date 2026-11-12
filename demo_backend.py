"""
Demo for the Backend & Application Integration subsystem.

The real ML classifier is still under development.
Therefore, this demo uses a temporary classifier
that follows the same interface expected by AnalysisService.

The database and guidance services are the actual
components from the project.
"""

from backend.analysis_service import AnalysisService

from database.db import DatabaseManager
from database.guidance import GuidanceService


class DemoClassifier:
    """
    Temporary classifier used only for demonstration.

    This class imitates the interface of the future
    real ML classifier.
    """

    def classify(self, image_bytes: bytes) -> dict:
        """
        Return a simulated classifier prediction.
        """

        if not image_bytes:
            raise ValueError("Image data cannot be empty.")

        return {
            "status": "completed",
            "label": "plastic bottle",
            "category": "recyclable",
            "confidence": 0.94,
        }


def main():
    print("=" * 60)
    print("AI-Powered Waste Sorting Assistant")
    print("Backend Integration Demo")
    print("=" * 60)

    # ---------------------------------------------------------
    # 1. Initialize database
    # ---------------------------------------------------------

    print("\n[1] Initializing database...")

    database_manager = DatabaseManager()
    database_manager.initialize()

    print("Database initialized successfully.")

    # ---------------------------------------------------------
    # 2. Initialize guidance service
    # ---------------------------------------------------------

    print("\n[2] Initializing guidance service...")

    guidance_service = GuidanceService(
        database_manager
    )

    print("Guidance service initialized successfully.")

    # ---------------------------------------------------------
    # 3. Initialize temporary classifier
    # ---------------------------------------------------------

    print("\n[3] Initializing classifier...")

    classifier = DemoClassifier()

    print("Temporary classifier initialized.")

    # ---------------------------------------------------------
    # 4. Create backend integration service
    # ---------------------------------------------------------

    print("\n[4] Initializing backend integration...")

    analysis_service = AnalysisService(
        classifier=classifier,
        database_manager=database_manager,
        guidance_service=guidance_service,
    )

    analysis_service.initialize()

    print("Backend integration initialized successfully.")

    # ---------------------------------------------------------
    # 5. Simulate an uploaded image
    # ---------------------------------------------------------

    print("\n[5] Processing uploaded image...")

    fake_image = b"demo-image-data"

    # ---------------------------------------------------------
    # 6. Run complete analysis workflow
    # ---------------------------------------------------------

    result = analysis_service.analyze(
        image_bytes=fake_image,
        region="Dortmund",
    )

    # ---------------------------------------------------------
    # 7. Display final response
    # ---------------------------------------------------------

    print("\n[6] Final backend response:")
    print("-" * 60)

    print(f"Waste name          : {result['waste_name']}")
    print(f"Category            : {result['category']}")
    print(f"Confidence          : {result['confidence']}")
    print(
        f"Disposal instruction: "
        f"{result['disposal_instruction']}"
    )
    print(f"Explanation         : {result['explanation']}")
    print(f"Region              : {result['region']}")
    print(
        f"Classification ID   : "
        f"{result['classification_id']}"
    )

    print("-" * 60)
    print("\nBackend integration completed successfully.")


if __name__ == "__main__":
    main()