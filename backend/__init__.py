"""
Backend & Application Integration subsystem.

This package coordinates communication between:
- the Flask web interface
- the ML classifier
- the database management subsystem
- the AI guidance service
- the frontend response layer
"""

from .analysis_service import AnalysisService
from .classification_result_handler import ClassificationResultHandler
from .response_composer import ResponseComposer

__all__ = [
    "AnalysisService",
    "ClassificationResultHandler",
    "ResponseComposer",
]