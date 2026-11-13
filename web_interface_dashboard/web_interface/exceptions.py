"""
Subsystem - Web Interface & Municipality Dashboard


Error handling for the web interface subsystem.

All errors inherit from WebInterfaceError, so the Flask app can catch every
web interface problem with one `except WebInterfaceError`.
The input errors also inherit from ValueError, because they are caused by
invalid values (existing `except ValueError` code keeps working).

    WebInterfaceError
    ├── InvalidUploadError      the uploaded image or request is not valid
    ├── InvalidResultError      the classification result has invalid values
    └── ImageRejectedError      the classifier could not use the image
"""


class WebInterfaceError(Exception):
    """Base class for all errors in the web interface subsystem."""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class InvalidUploadError(WebInterfaceError, ValueError):
    """The upload is not valid, e.g. no image, empty file, too large, wrong status."""


class InvalidResultError(WebInterfaceError, ValueError):
    """The classification result has an invalid value, e.g. confidence outside 0-1."""


class ImageRejectedError(WebInterfaceError, ValueError):
    """The classifier could not use the image (classifier status 'invalid_image')."""