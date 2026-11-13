"""
Demo data for the municipality dashboard - Subsystem 4 (Ha Le Thu)

Run:  python demo_dashboard_data.py            # 200 example results over 30 days
      python demo_dashboard_data.py 500 60     # 500 results over 60 days
Fills database/waste.db so the dashboard has something to show in the screencast.
"""

import random
import sys
from datetime import datetime, timedelta

from database.db import DatabaseManager

# (label, weight) - labels from data/waste_guidance.json, common items appear more often
DEMO_ITEMS = [
    ("plastic bottle", 14), ("cardboard box", 10), ("newspaper", 8), ("food leftovers", 9),
    ("glass bottle", 7), ("banana peel", 7), ("yogurt cup", 6), ("tin can", 5),
    ("coffee grounds", 5), ("beverage carton", 5), ("glass jar", 5), ("pizza box", 4),
    ("diaper", 3), ("cigarette butt", 3), ("battery", 2), ("aluminium can", 4),
]
DEMO_REGIONS = [("Dortmund", 8), ("Bochum", 1), ("Essen", 1)]


def create_demo_data(db: DatabaseManager, count: int = 200, days: int = 30, seed: int = 26) -> int:
    rng = random.Random(seed)
    labels, label_weights = zip(*DEMO_ITEMS)
    regions, region_weights = zip(*DEMO_REGIONS)
    now = datetime.now()
    for _ in range(count):
        confidence = round(rng.uniform(0.4, 0.99), 2)
        created = now - timedelta(days=rng.uniform(0, days))
        db.save_classification(
            rng.choices(labels, label_weights)[0],
            confidence=confidence,
            status="completed" if confidence >= 0.5 else "uncertain",
            region=rng.choices(regions, region_weights)[0],
            created_at=created.strftime("%Y-%m-%d %H:%M:%S"),
        )
    return count


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 200
    d = int(sys.argv[2]) if len(sys.argv) > 2 else 30
    manager = DatabaseManager()
    manager.initialize()
    create_demo_data(manager, n, d)
    stats = manager.get_stats()
    print(f"Added {n} demo results. Dortmund: {stats['total_items']} items, "
          f"recycling rate {stats['recycling_rate']:.0%}.")
