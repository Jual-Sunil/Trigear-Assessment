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

logger = logging.getLogger(__name__)


class ClassificationService:
    """Coordinate zero-shot classification and confidence-threshold evaluation.

    The service executes the classification pipeline in order:

    1. Run zero-shot classification (single email or batched).
    2. Apply the configured confidence threshold and fall back to ``Other``
       when the score is below the threshold.

    The resulting category and confidence score are returned in a
    :class:`~infrastructure.ai.classification.schemas.ClassificationResult`.
    """

    def __init__(
        self,
        *,
        zero_shot_classifier: ZeroShotClassifier | None = None,
        confidence_threshold: float | None = None,
    ) -> None:
        """Initialise the classification service.

        Args:
            zero_shot_classifier: Optional zero-shot classifier dependency override.
            confidence_threshold: Minimum confidence required to keep the
                classifier's predicted category. When omitted, the configured
                application threshold is used.
        """
        settings = get_settings()
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

        classification_result = self._zero_shot_classifier.classify(input_data)
        return self._apply_threshold(classification_result)

    def classify_batch(
        self,
        inputs: list[EmailClassificationInput],
    ) -> list[ClassificationResult | None]:
        """Classify many emails in a single batched zero-shot inference call.

        Produces results equivalent to calling :meth:`classify` per email — the
        same model, hypothesis template, and confidence-threshold override are
        applied — but issues one batched model call instead of one call per
        email. Inputs without usable text yield ``None`` at the matching index,
        mirroring the :class:`ClassificationInputError` path of :meth:`classify`.

        Args:
            inputs: Validated classification inputs, one per email.

        Returns:
            A list aligned with ``inputs`` where each element is a
            :class:`ClassificationResult` or ``None`` when the email had no
            usable text.
        """
        results: list[ClassificationResult | None] = [None] * len(inputs)

        classifiable: list[EmailClassificationInput] = []
        positions: list[int] = []
        for index, input_data in enumerate(inputs):
            if input_data.build_classification_text():
                classifiable.append(input_data)
                positions.append(index)
            else:
                logger.warning(
                    "classification_skipped_no_usable_text",
                    extra={"gmail_message_id": input_data.gmail_message_id},
                )

        if not classifiable:
            return results

        raw_results = self._zero_shot_classifier.classify_many(classifiable)
        for position, raw_result in zip(positions, raw_results):
            results[position] = self._apply_threshold(raw_result)

        return results

    def _apply_threshold(
        self,
        classification_result: ClassificationResult,
    ) -> ClassificationResult:
        """Apply the configured confidence threshold to a raw classifier result.

        Args:
            classification_result: The raw result from the zero-shot classifier.

        Returns:
            The original result, or an ``Other`` fallback result when the
            confidence score is below the configured threshold.
        """
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