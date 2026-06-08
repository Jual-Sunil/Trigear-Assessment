"""Zero-shot email classifier backed by facebook/bart-large-mnli."""

from __future__ import annotations

import re as _re
import threading
from collections.abc import Callable
from typing import TypedDict, cast

from core.config import get_settings
from core.constants import CLASSIFICATION_METHOD_ZERO_SHOT, EMAIL_CATEGORIES
from infrastructure.ai.classification.base import BaseClassifier
from infrastructure.ai.classification.exceptions import (
    ClassificationInferenceError,
    ClassificationInputError,
    ClassifierNotReadyError,
    LowConfidenceError,
)
from infrastructure.ai.classification.schemas import (
    CategoryScore,
    ClassificationResult,
    EmailClassificationInput,
)


_INVISIBLE_UNICODE_RE = _re.compile(
    r"[\u200b\u200c\u200d\u200e\u200f\ufeff\u00ad]+"
)


def _strip_invisible_unicode(text: str) -> str:
    """Remove zero-width and invisible Unicode characters from classifier input.

    Job board digest emails (Glassdoor, LinkedIn, hirist.tech) embed
    zero-width joiners, non-breaking spaces, and BOM characters as tracking
    spacers.  These consume the 512-character classification window without
    contributing any semantic signal and degrade NLI model accuracy.

    Args:
        text: Raw classification text from
            :meth:`~infrastructure.ai.classification.schemas.EmailClassificationInput.build_classification_text`.

    Returns:
        Cleaned text with invisible characters removed and collapsed whitespace.
    """
    cleaned = _INVISIBLE_UNICODE_RE.sub(" ", text)
    return " ".join(cleaned.split())


class _LabelScore(TypedDict):
    """Typed representation of a single zero-shot label score output."""

    label: str
    score: float


class ZeroShotClassifier(BaseClassifier):
    """Classify emails using HuggingFace's zero-shot classification pipeline.

    The classifier loads ``facebook/bart-large-mnli`` lazily and shares the
    model across all instances. Classification returns a
    :class:`~infrastructure.ai.classification.schemas.ClassificationResult`
    containing the winning category, its confidence score, and the top-k
    category scores.
    """

    _model_name: str = "facebook/bart-large-mnli"
    _pipeline: Callable[..., object] | None = None
    _pipeline_lock = threading.Lock()

    def __init__(
        self,
        *,
        top_k_labels: int | None = None,
        confidence_threshold: float | None = None,
    ) -> None:
        """Initialise classifier settings without loading the model.

        Args:
            top_k_labels: Maximum number of label scores to keep in the result.
                When ``None``, all available categories are returned.
            confidence_threshold: Minimum score required for a successful
                classification. When omitted, the global configured threshold
                is used.
        """
        self._top_k_labels = top_k_labels
        self._confidence_threshold = (
            confidence_threshold
            if confidence_threshold is not None
            else get_settings().classification_confidence_threshold
        )

        if self._top_k_labels is not None and self._top_k_labels < 1:
            raise ValueError("top_k_labels must be greater than or equal to 1.")

    @property
    def method_name(self) -> str:
        """Return the canonical method identifier for this classifier."""
        return CLASSIFICATION_METHOD_ZERO_SHOT

    def is_ready(self) -> bool:
        """Return True when the HuggingFace pipeline has been loaded."""
        return self.__class__._pipeline is not None

    def load(self) -> None:
        """Load the HuggingFace zero-shot pipeline in a thread-safe manner."""
        if self.__class__._pipeline is not None:
            return

        with self.__class__._pipeline_lock:
            if self.__class__._pipeline is not None:
                return

            settings = get_settings()
            from transformers import pipeline as hf_pipeline

            self.__class__._pipeline = hf_pipeline(
                task="zero-shot-classification",
                model=self._model_name,
                cache_dir=settings.huggingface_cache_dir,
            )

    def unload(self) -> None:
        """Release the shared HuggingFace pipeline from memory."""
        with self.__class__._pipeline_lock:
            self.__class__._pipeline = None

    def classify(self, input_data: EmailClassificationInput) -> ClassificationResult:
        """Classify a single email using zero-shot inference.

        Args:
            input_data: Validated email classification input.

        Returns:
            A structured classification result with category scores.

        Raises:
            ClassifierNotReadyError: If the model has not been loaded.
            ClassificationInputError: If the input text is empty.
            ClassificationInferenceError: If the underlying pipeline fails.
            LowConfidenceError: If the best category score is below threshold.
        """
        self.load()
        self._assert_ready()

        text = self._assert_input_has_text(input_data)
        cleaned_text = _strip_invisible_unicode(text)
        pipeline = cast(Callable[..., object], self.__class__._pipeline)

        try:
            raw_output = pipeline(
                cleaned_text,
                candidate_labels=EMAIL_CATEGORIES,
                hypothesis_template="This email is about {}.",
                multi_label=False,
            )
        except Exception as exc:  # noqa: BLE001
            raise ClassificationInferenceError(
                self.__class__.__name__,
                "Zero-shot inference failed.",
                cause=exc,
            ) from exc

        scores = self._normalize_predictions(raw_output)
        best_score = scores[0]
        if best_score.score < self._confidence_threshold:
            raise LowConfidenceError(
                self.__class__.__name__,
                best_score.category,
                best_score.score,
                self._confidence_threshold,
            )

        return ClassificationResult(
            gmail_message_id=input_data.gmail_message_id,
            category=best_score.category,
            confidence_score=best_score.score,
            all_scores=scores,
            method=self.method_name,
        )

    def _normalize_predictions(self, raw_output: object) -> list[CategoryScore]:
        """Normalize HuggingFace output into sorted category scores.

        Args:
            raw_output: Raw pipeline response.

        Returns:
            A non-empty list of category scores sorted by descending confidence.

        Raises:
            ClassificationInferenceError: If the response shape is unexpected.
        """
        predictions = self._coerce_prediction_items(raw_output)

        scores = [
            CategoryScore(category=item["label"], score=float(item["score"]))
            for item in predictions
        ]
        scores.sort(key=lambda item: item.score, reverse=True)
        if not scores:
            raise ClassificationInferenceError(
                self.__class__.__name__,
                "Zero-shot inference returned no label scores.",
            )
        if any(score.category not in EMAIL_CATEGORIES for score in scores):
            raise ClassificationInferenceError(
                self.__class__.__name__,
                "Zero-shot inference returned an unexpected label.",
            )
        return scores

    def _coerce_prediction_items(self, raw_output: object) -> list[_LabelScore]:
        """Coerce the pipeline output into a flat list of label-score items.

        The HuggingFace zero-shot-classification pipeline always returns:

        * **Single-string input** → a ``dict`` with keys
          ``"sequence"``, ``"labels"`` (list), ``"scores"`` (list).
        * **Batch input** (list of strings) → a ``list`` of such dicts.

        Both shapes are handled here; the former is the normal code path.
        """
        if isinstance(raw_output, dict):
            return self._coerce_result_dict(raw_output)

        if isinstance(raw_output, list):
            if not raw_output:
                return []
            first_item = raw_output[0]
            if isinstance(first_item, dict):
                return self._coerce_result_dict(
                    cast(dict[str, object], first_item)
                )

        raise ClassificationInferenceError(
            self.__class__.__name__,
            "Zero-shot inference returned an unsupported response shape.",
        )

    def _coerce_result_dict(self, result: dict[str, object]) -> list[_LabelScore]:
        """Convert a single pipeline result dict into a list of label-score pairs.

        The pipeline result has the shape::

            {
                "sequence": str,
                "labels":   list[str],   # sorted descending by score
                "scores":   list[float],
            }

        Args:
            result: One pipeline result dict.

        Returns:
            A list of :class:`_LabelScore` items, one per candidate label.

        Raises:
            ClassificationInferenceError: When required keys are missing or
                the label/score lists are not the same length.
        """
        labels = result.get("labels")
        scores = result.get("scores")

        if not isinstance(labels, list) or not isinstance(scores, list):
            raise ClassificationInferenceError(
                self.__class__.__name__,
                (
                    "Zero-shot inference result dict is missing 'labels' or 'scores' "
                    f"lists. Got keys: {list(result.keys())}"
                ),
            )

        if len(labels) != len(scores):
            raise ClassificationInferenceError(
                self.__class__.__name__,
                (
                    f"'labels' ({len(labels)}) and 'scores' ({len(scores)}) "
                    "lists have different lengths."
                ),
            )

        items: list[_LabelScore] = []
        for label, score in zip(labels, scores):
            if not isinstance(label, str) or not isinstance(score, (int, float)):
                raise ClassificationInferenceError(
                    self.__class__.__name__,
                    f"Malformed label-score pair: label={label!r}, score={score!r}.",
                )
            items.append(_LabelScore(label=label, score=float(score)))
        return items