import pytest

from classifier import CategoryMapper


@pytest.fixture
def mapper():
    return CategoryMapper()


@pytest.mark.parametrize(
    "label, category",
    [
        ("glass jar", "recyclable"),
        ("plastic bottle", "recyclable"),
        ("banana peel", "compostable"),
        ("coffee grounds", "compostable"),
        ("diaper", "landfill"),
    ],
)
def test_known_labels(mapper, label, category):
    assert mapper.map_category(label) == category


def test_unknown_label_defaults_to_landfill(mapper):
    assert mapper.map_category("spaceship") == "landfill"


def test_every_label_maps_to_one_of_three_categories(mapper):
    assert set(mapper.categories) == {"recyclable", "compostable", "landfill"}
    for label in mapper.labels:
        assert mapper.map_category(label) in mapper.categories


def test_labels_use_database_format(mapper):
    # Ha's get_rule(label) expects lowercase labels with spaces, e.g. "glass jar"
    for label in mapper.labels:
        assert label == label.lower().strip() and "_" not in label


@pytest.mark.parametrize(
    "confidence, expected",
    [(0.9, True), (0.5, True), (0.49, False), (None, False)],
)
def test_check_confidence(confidence, expected):
    assert CategoryMapper.check_confidence(confidence, threshold=0.5) is expected


def test_custom_mapping():
    mapper = CategoryMapper({"pizza_box": "recyclable"})
    assert mapper.labels == ["pizza_box"]


def test_mapping_getter_returns_a_copy(mapper):
    mapper.label_to_category["glass jar"] = "landfill"
    assert mapper.map_category("glass jar") == "recyclable"


def test_mapping_setter_rejects_unknown_category(mapper):
    with pytest.raises(ValueError):
        mapper.label_to_category = {"glass jar": "space"}
