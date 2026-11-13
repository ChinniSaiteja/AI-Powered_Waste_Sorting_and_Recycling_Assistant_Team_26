"""Evaluate the classifier on labelled test images.

    python scripts/evaluate.py test_images/ --threshold 0.5

test_images/ must contain one sub-folder per label from CategoryMapper,
with _ instead of spaces, e.g. test_images/glass_jar/*.jpg. Writes results/evaluation.json and
results/confusion_matrix.png for the final presentation.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from classifier import ClassifierConfig, ModelEvaluator, WasteClassifier  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", help="folder with one sub-folder per label")
    parser.add_argument("--threshold", type=float, default=0.5)
    parser.add_argument("--output", default="results")
    args = parser.parse_args()

    classifier = WasteClassifier(ClassifierConfig(confidence_threshold=args.threshold))
    classifier.warm_up()  # keep model loading out of the inference-time numbers
    evaluator = ModelEvaluator(classifier)
    samples = evaluator.load_dataset(args.dataset)
    if not samples:
        sys.exit(f"No images found in {args.dataset}")

    report = evaluator.evaluate(samples)
    output = Path(args.output)
    output.mkdir(exist_ok=True)
    (output / "evaluation.json").write_text(json.dumps(report, indent=2))
    evaluator.plot_confusion_matrix(
        report, classifier.mapper.categories, output / "confusion_matrix.png"
    )

    print(f"Images evaluated:   {report['evaluated']} / {report['total_images']}")
    print(f"Label accuracy:     {report['label_accuracy']:.1%}")
    print(f"Category accuracy:  {report['category_accuracy']:.1%}")
    print(f"Avg inference time: {report['avg_inference_ms']:.0f} ms")
    print(f"Statuses:           {report['status_counts']}")
    print(f"Saved to {output}/")


if __name__ == "__main__":
    main()
