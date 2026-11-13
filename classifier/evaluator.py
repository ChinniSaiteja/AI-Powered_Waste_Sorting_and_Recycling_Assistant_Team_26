from collections import Counter, defaultdict
from pathlib import Path

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


class ModelEvaluator:
    """Measures accuracy and inference time on labelled images (NFR 1, NFR 8).

    Expected folder layout: one sub-folder per true label, with "_" in place
    of spaces in the folder name, e.g.
        test_images/glass_jar/1.jpg
        test_images/banana_peel/2.jpg
    """

    def __init__(self, classifier):
        self.classifier = classifier

    @staticmethod
    def load_dataset(folder) -> list:
        """Return a list of (image_path, true_label) pairs."""
        samples = []
        for label_dir in sorted(Path(folder).iterdir()):
            if label_dir.is_dir():
                for image_path in sorted(label_dir.iterdir()):
                    if image_path.suffix.lower() in IMAGE_EXTENSIONS:
                        samples.append((image_path, label_dir.name.replace("_", " ")))
        return samples

    def evaluate(self, samples: list) -> dict:
        mapper = self.classifier.mapper
        confusion = defaultdict(Counter)  # true category -> predicted category counts
        label_hits = category_hits = evaluated = 0
        statuses = Counter()
        times = []

        for image_path, true_label in samples:
            result = self.classifier.predict(image_path)
            statuses[result.status.value] += 1
            if result.label is None:  # invalid image or model error
                continue
            evaluated += 1
            true_category = mapper.map_category(true_label)
            label_hits += result.label == true_label
            category_hits += result.category == true_category
            confusion[true_category][result.category] += 1
            times.append(result.inference_ms)

        return {
            "total_images": len(samples),
            "evaluated": evaluated,
            "label_accuracy": label_hits / evaluated if evaluated else 0.0,
            "category_accuracy": category_hits / evaluated if evaluated else 0.0,
            "avg_inference_ms": sum(times) / len(times) if times else 0.0,
            "status_counts": dict(statuses),
            "confusion_matrix": {true: dict(pred) for true, pred in confusion.items()},
        }

    @staticmethod
    def plot_confusion_matrix(report: dict, categories: list, output_path) -> None:
        from matplotlib.figure import Figure  # no GUI backend needed (works in Docker/servers)

        matrix = report["confusion_matrix"]
        values = [[matrix.get(t, {}).get(p, 0) for p in categories] for t in categories]

        fig = Figure(figsize=(5, 4))
        ax = fig.subplots()
        ax.imshow(values, cmap="Blues")
        ax.set_xticks(range(len(categories)), categories)
        ax.set_yticks(range(len(categories)), categories)
        ax.set_xlabel("Predicted category")
        ax.set_ylabel("True category")
        ax.set_title(f"Category accuracy: {report['category_accuracy']:.0%}")
        for i, row in enumerate(values):
            for j, value in enumerate(row):
                ax.text(j, i, value, ha="center", va="center")
        fig.tight_layout()
        fig.savefig(output_path, dpi=150)
