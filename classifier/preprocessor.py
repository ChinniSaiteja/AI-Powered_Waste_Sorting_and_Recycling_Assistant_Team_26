import io
from pathlib import Path
from typing import Union

from PIL import Image, ImageOps, UnidentifiedImageError

from classifier.config import ClassifierConfig
from classifier.exceptions import InvalidImageError

ImageSource = Union[str, Path, bytes, Image.Image]


class ImagePreprocessor:
    """Validates and prepares an image for the model (FR 2, FR 3)."""

    def __init__(self, config: ClassifierConfig):
        self.config = config

    @property
    def config(self) -> ClassifierConfig:
        return self.__config

    @config.setter
    def config(self, value: ClassifierConfig) -> None:
        if not isinstance(value, ClassifierConfig):
            raise TypeError("config must be a ClassifierConfig")
        self.__config = value

    def validate(self, source: ImageSource) -> Image.Image:
        """Open the image and check it is readable, supported and not too large."""
        if isinstance(source, Image.Image):
            return source

        if isinstance(source, (str, Path)):
            path = Path(source)
            if not path.is_file():
                raise InvalidImageError(f"File not found: {path.name}")
            data = path.read_bytes()
        elif isinstance(source, (bytes, bytearray)):
            data = bytes(source)
        else:
            raise InvalidImageError(f"Unsupported input type: {type(source).__name__}")

        if not data:
            raise InvalidImageError("The uploaded file is empty")
        size_mb = len(data) / (1024 * 1024)
        if size_mb > self.config.max_file_size_mb:
            raise InvalidImageError(
                f"Image is {size_mb:.1f} MB, the limit is {self.config.max_file_size_mb} MB"
            )

        try:
            image = Image.open(io.BytesIO(data))
            image.verify()  # detects truncated / corrupt files
            image = Image.open(io.BytesIO(data))  # verify() leaves the image unusable
        except (UnidentifiedImageError, OSError, SyntaxError) as exc:
            raise InvalidImageError("The file is not a readable image") from exc

        if image.format not in self.config.allowed_formats:
            raise InvalidImageError(
                f"Format {image.format} is not supported, use {', '.join(self.config.allowed_formats)}"
            )
        return image

    def prepare_for_detection(self, image: Image.Image) -> Image.Image:
        """Fix rotation and colour mode but keep the full size, so bounding boxes
        are in the coordinates of the uploaded photo."""
        return ImageOps.exif_transpose(image).convert("RGB")

    def preprocess(self, image: Image.Image) -> Image.Image:
        """Fix phone rotation, convert to RGB and resize (NFR 4: robustness)."""
        image = ImageOps.exif_transpose(image)
        image = image.convert("RGB")
        size = self.config.image_size
        return ImageOps.fit(image, (size, size))
