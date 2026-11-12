"""
Subsystem 4 - Data Management & AI Guidance
Owner: Ha Le Thu

Home Assignment 4: Exception Handling
Error-handling classes for the Data Management subsystem.

    DataManagementError            base class for every error of this subsystem
     |- InvalidDataError           wrong input (empty label, confidence 1.5, ...)
     |- ItemNotFoundError          label / record does not exist in the database
     |- DatabaseConnectionError    database server not reachable / wrong password

Every error knows:
    - a readable message
    - an error code (for logs and the frontend)
    - the HTTP status the Flask backend should return
    - to_dict() -> JSON body for the API response
"""


class DataManagementError(Exception):
    """Base class: catch this to handle every error of the data subsystem."""

    code = "DATA_ERROR"
    http_status = 500

    def __init__(self, message: str, details: dict | None = None):
        super().__init__(message)
        self.__message = message
        self.__details = details or {}

    @property
    def message(self) -> str:
        return self.__message

    @property
    def details(self) -> dict:
        return dict(self.__details)

    def to_dict(self) -> dict:
        """JSON body the backend can return directly, e.g. return err.to_dict(), err.http_status"""
        return {"error": self.code, "message": self.__message, "details": self.details}

    def __str__(self) -> str:
        return f"[{self.code}] {self.__message}"


class InvalidDataError(DataManagementError, ValueError):
    """Input data is wrong. Also a ValueError, so normal `except ValueError` still works."""

    code = "INVALID_DATA"
    http_status = 400

    def __init__(self, field: str, value, reason: str):
        super().__init__(f"Invalid {field} {value!r}: {reason}",
                         {"field": field, "value": repr(value), "reason": reason})
        self.field = field


class ItemNotFoundError(DataManagementError, LookupError):
    """The requested item / record does not exist."""

    code = "NOT_FOUND"
    http_status = 404

    def __init__(self, what: str, key, region: str | None = None):
        where = f" in {region}" if region else ""
        super().__init__(f"No {what} found for {key!r}{where}",
                         {"what": what, "key": str(key), "region": region})


class DatabaseConnectionError(DataManagementError):
    """The database cannot be reached (MySQL not running, wrong password, ...)."""

    code = "DB_UNAVAILABLE"
    http_status = 503

    def __init__(self, engine: str, original: Exception):
        super().__init__(f"Cannot connect to the {engine} database: {original}",
                         {"engine": engine, "original_error": type(original).__name__})
