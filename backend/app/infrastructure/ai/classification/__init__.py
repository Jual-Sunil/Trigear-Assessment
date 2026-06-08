"""Classification subsystem public API.

Exports the abstractions, DTOs, and exceptions that form the contract between
the orchestration layer and concrete classifier implementations.
"""

from infrastructure.ai.classification.base import BaseClassifier
from infrastructure.ai.classification.exceptions import (
    ClassificationError,
    ClassificationInferenceError,
    ClassificationInputError,
    ClassificationTimeoutError,
    ClassifierNotReadyError,
    LowConfidenceError,
)
from infrastructure.ai.classification.schemas import (
    CategoryScore,
    ClassificationResult,
    EmailClassificationInput,
)

__all__ = [
    # Base
    "BaseClassifier",
    # Schemas
    "EmailClassificationInput",
    "ClassificationResult",
    "CategoryScore",
    # Exceptions
    "ClassificationError",
    "ClassifierNotReadyError",
    "ClassificationInputError",
    "ClassificationInferenceError",
    "ClassificationTimeoutError",
    "LowConfidenceError",
]
