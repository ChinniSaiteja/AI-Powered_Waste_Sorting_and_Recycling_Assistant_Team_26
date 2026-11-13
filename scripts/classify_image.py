"""Classify one photo from the command line.

    python scripts/classify_image.py path/to/photo.jpg
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from classifier import WasteClassifier  # noqa: E402


def main():
    if len(sys.argv) != 2:
        sys.exit("Usage: python scripts/classify_image.py <image>")
    result = WasteClassifier().classify(sys.argv[1])
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
