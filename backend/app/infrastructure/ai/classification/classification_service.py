"""Classification orchestration service for email categorisation."""

from __future__ import annotations

import logging

from core.config import get_settings
from core.constants import EMAIL_CATEGORY_OTHER
from infrastructure.ai.classification.exceptions import ClassificationInputError
from infrastructure.ai.classification.schemas import (
    ClassificationResult,
    EmailClassificationInput,
)
from infrastructure.ai.classification.zero_shot_classifier import ZeroShotClassifier
from infrastructure.ai.embeddings.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)


class ClassificationService:
    """Coordinate embedding generation, zero-shot classification, and threshold evaluation.

    The service executes the phase-5 classification pipeline in order:

    1. Generate an embedding for the email text.
    2. Run zero-shot classification.
    3. Apply the configured confidence threshold and fallback to ``Other``
       when the score is below the threshold.

    The resulting category and confidence score are returned in a
    :class:`~infrastructure.ai.classification.schemas.ClassificationResult`.
    """

    def __init__(
        self,
        *,
        embedding_service: EmbeddingService | None = None,
        zero_shot_classifier: ZeroShotClassifier | None = None,
        confidence_threshold: float | None = None,
    ) -> None:
        """Initialise the classification service.

        Args:
            embedding_service: Optional embedding service dependency override.
            zero_shot_classifier: Optional zero-shot classifier dependency override.
            confidence_threshold: Minimum confidence required to keep the
                classifier's predicted category. When omitted, the configured
                application threshold is used.
        """
        settings = get_settings()
        self._embedding_service = embedding_service or EmbeddingService()
        self._zero_shot_classifier = zero_shot_classifier or ZeroShotClassifier(
            confidence_threshold=0.0  # threshold enforced below; classifier returns all scores
        )
        self._confidence_threshold = (
            confidence_threshold
            if confidence_threshold is not None
            else settings.classification_confidence_threshold
        )

    def classify(self, input_data: EmailClassificationInput) -> ClassificationResult:
        """Classify an email using embeddings followed by zero-shot inference.

        Args:
            input_data: Validated input payload for the email to classify.

        Returns:
            A classification result containing the final category and score.

        Raises:
            ClassificationInputError: If no usable text can be produced from
                the input payload.
        """
        text = input_data.build_classification_text()
        if not text:
            raise ClassificationInputError(
                f"No usable text could be extracted from email "
                f"'{input_data.gmail_message_id}' for classification."
            )

        self._embedding_service.embed_text(text)
        classification_result = self._zero_shot_classifier.classify(input_data)

        print("RESULT TYPE:", type(classification_result))
        print("RESULT:", classification_result)

        if classification_result.confidence_score < self._confidence_threshold:
            logger.warning(
                "classification_below_threshold",
                extra={
                    "gmail_message_id": classification_result.gmail_message_id,
                    "predicted_category": classification_result.category,
                    "confidence_score": classification_result.confidence_score,
                    "threshold": self._confidence_threshold,
                    "override_to": EMAIL_CATEGORY_OTHER,
                },
            )
            return ClassificationResult(
                gmail_message_id=classification_result.gmail_message_id,
                category=EMAIL_CATEGORY_OTHER,
                confidence_score=classification_result.confidence_score,
                # Do NOT forward all_scores here: the model_validator requires the
                # winning category to appear in all_scores, but the real winner is
                # a different label (below-threshold). Pass an empty list so the
                # validator is satisfied; callers that need the full distribution
                # can re-run the classifier without the threshold override.
                all_scores=[],
                method=classification_result.method,
            )

        return classification_result