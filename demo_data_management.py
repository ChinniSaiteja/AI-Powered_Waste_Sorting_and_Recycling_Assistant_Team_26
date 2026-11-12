"""
Demo for Home Assignment 1 - Subsystem 4: Data Management (Ha Le Thu)

Run:  python demo_data_management.py
Shows the 3 OOP classes (WasteCategory, WasteItem, DisposalRule)
and the DatabaseManager that stores them.
"""

from database.db import DatabaseManager
from database.models import DisposalRule, WasteCategory, WasteItem


def demo_classes() -> None:
    print("=== 1. Creating objects (constructor) ===")
    glass = WasteCategory(1, "recyclable", "Can be recycled")
    jar = WasteItem(1, "Glass Jar", glass)            # label is normalised by the setter
    rule = DisposalRule(1, jar, "Altglascontainer (glass container)",
                        "Remove the lid. Sort by colour.")
    print(glass)
    print(jar)
    print(rule)

    print("\n=== 2. Getters & setters (encapsulation) ===")
    print("label via getter:", jar.label)
    jar.is_deposit = False
    rule.region = "dortmund"                          # setter turns it into 'Dortmund'
    print("region via getter:", rule.region)

    print("\n=== 3. Setters protect the data ===")
    tests = [
        ("category name 'plastic'", lambda: setattr(glass, "name", "plastic")),
        ("empty label", lambda: setattr(jar, "label", "   ")),
        ("is_deposit = 'yes'", lambda: setattr(jar, "is_deposit", "yes")),
        ("empty instruction", lambda: setattr(rule, "instruction", "")),
    ]
    for name, action in tests:
        try:
            action()
        except (ValueError, TypeError) as error:
            print(f"Rejected {name}: {error}")

    print("\n=== 4. Private attributes cannot be read directly ===")
    try:
        print(jar.__label)
    except AttributeError:
        print("jar.__label -> AttributeError (only jar.label works)")


def demo_database() -> None:
    print("\n=== 5. DatabaseManager ===")
    db = DatabaseManager()
    loaded = db.initialize()
    print(f"Engine: {db.engine} | rules loaded now: {loaded} (0 = already in database)")
    print(f"Known items: {len(db.get_all_items())}")

    for label in ("glass jar", "plastic bottle", "banana peel", "unknown thing"):
        print(f"get_rule('{label}') ->", db.get_rule(label))

    cid = db.save_classification("glass jar", confidence=0.92)
    db.save_classification("banana peel", confidence=0.88)
    db.save_classification("plastic bottle", confidence=0.41, status="uncertain")
    db.save_feedback(cid, is_correct=True)
    print("\nget_stats() ->", db.get_stats())


if __name__ == "__main__":
    demo_classes()
    demo_database()
