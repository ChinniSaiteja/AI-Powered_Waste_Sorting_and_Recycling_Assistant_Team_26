import pytest

from classifier import ModelEvaluator
from tests.conftest import make_image_bytes


@pytest.fixture
def dataset(tmp_path):
    for label in ("glass_jar", "banana_peel"):
        folder = tmp_path / label
        folder.mkdir()
        for i in range(2):
            (folder / f"{i}.jpg").write_bytes(make_image_bytes())
    (tmp_path / "glass_jar" / "notes.txt").write_text("ignored")
    (tmp_path / "glass_jar" / "broken.png").write_bytes(b"broken")
    return tmp_path


def test_load_dataset_uses_folder_names_as_labels(dataset):
    samples = ModelEvaluator.load_dataset(dataset)
    assert len(samples) == 5  # .txt is skipped, broken.png is kept
    assert {label for _, label in samples} == {"glass jar", "banana peel"}


def test_evaluate_reports_accuracy(make_classifier, dataset):
    evaluator = ModelEvaluator(make_classifier(label="glass jar", confidence=0.9))
    report = evaluator.evaluate(ModelEvaluator.load_dataset(dataset))

    assert report["total_images"] == 5
    assert report["evaluated"] == 4
    assert report["status_counts"] == {"completed": 4, "invalid_image": 1}
    assert report["label_accuracy"] == 0.5  # always says glass jar: right for 2 of 4
    assert report["category_accuracy"] == 0.5
    assert report["confusion_matrix"]["compostable"] == {"recyclable": 2}


def test_plot_confusion_matrix(make_classifier, dataset, tmp_path):
    pytest.importorskip("matplotlib")
    evaluator = ModelEvaluator(make_classifier())
    report = evaluator.evaluate(ModelEvaluator.load_dataset(dataset))
    output = tmp_path / "confusion.png"
    ModelEvaluator.plot_confusion_matrix(report, ["recyclable", "compostable", "landfill"], output)
    assert output.stat().st_size > 0
