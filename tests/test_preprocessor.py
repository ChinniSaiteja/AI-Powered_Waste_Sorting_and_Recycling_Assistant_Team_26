import pytest
from PIL import Image

from classifier import ClassifierConfig, ImagePreprocessor, InvalidImageError
from tests.conftest import make_image_bytes


@pytest.fixture
def preprocessor():
    return ImagePreprocessor(ClassifierConfig())


@pytest.mark.parametrize("fmt", ["JPEG", "PNG", "WEBP"])
def test_supported_formats_are_accepted(preprocessor, fmt):
    image = preprocessor.validate(make_image_bytes(fmt))
    assert image.format == fmt


def test_file_path_is_accepted(preprocessor, jpeg_file):
    assert preprocessor.validate(jpeg_file).size == (64, 48)


def test_missing_file_is_rejected(preprocessor, tmp_path):
    with pytest.raises(InvalidImageError, match="not found"):
        preprocessor.validate(tmp_path / "missing.jpg")


def test_empty_file_is_rejected(preprocessor):
    with pytest.raises(InvalidImageError, match="empty"):
        preprocessor.validate(b"")


def test_non_image_is_rejected(preprocessor):
    with pytest.raises(InvalidImageError, match="not a readable image"):
        preprocessor.validate(b"this is a text file, not a photo")


def test_truncated_image_is_rejected(preprocessor):
    data = make_image_bytes("PNG")
    with pytest.raises(InvalidImageError):
        preprocessor.validate(data[: len(data) // 2])


def test_unsupported_format_is_rejected(preprocessor):
    with pytest.raises(InvalidImageError, match="not supported"):
        preprocessor.validate(make_image_bytes("BMP"))


def test_too_large_file_is_rejected():
    preprocessor = ImagePreprocessor(ClassifierConfig(max_file_size_mb=0.0001))
    with pytest.raises(InvalidImageError, match="limit"):
        preprocessor.validate(make_image_bytes("PNG", size=(200, 200)))


def test_unsupported_input_type_is_rejected(preprocessor):
    with pytest.raises(InvalidImageError, match="Unsupported input type"):
        preprocessor.validate(12345)


@pytest.mark.parametrize("mode", ["RGB", "L", "RGBA"])
def test_preprocess_returns_square_rgb(preprocessor, mode):
    image = Image.new(mode, (300, 120))
    result = preprocessor.preprocess(image)
    assert result.mode == "RGB"
    assert result.size == (224, 224)


def test_invalid_config_is_rejected():
    with pytest.raises(ValueError):
        ClassifierConfig(confidence_threshold=1.5)
