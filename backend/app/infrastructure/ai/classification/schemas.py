"""Data-transfer objects and value types for the classification subsystem."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated

from pydantic import BaseModel, Field, field_validator, model_validator

from core.constants import (
    CLASSIFICATION_METHOD_EMBEDDING,
    CLASSIFICATION_METHOD_LLM,
    CLASSIFICATION_METHOD_ZERO_SHOT,
    EMAIL_CATEGORIES,
)


# ---------------------------------------------------------------------------
# Value types
# ---------------------------------------------------------------------------

CategoryStr = Annotated[
    str,
    Field(description="One of the recognised email classification categories."),
]

ConfidenceScore = Annotated[
    float,
    Field(
        ge=0.0,
        le=1.0,
        description="Normalised confidence score in the range [0.0, 1.0].",
    ),
]

VALID_CLASSIFICATION_METHODS: frozenset[str] = frozenset(
    {
        CLASSIFICATION_METHOD_EMBEDDING,
        CLASSIFICATION_METHOD_ZERO_SHOT,
        CLASSIFICATION_METHOD_LLM,
    }
)


# ---------------------------------------------------------------------------
# Input schema
# ---------------------------------------------------------------------------


class EmailClassificationInput(BaseModel):
    """Carries the text content required for classifying a single email.

    The classifier uses ``subject`` and ``body_text`` together to build a
    representative snippet.  Both fields are optional because emails may
    arrive with missing content; at least one must be non-empty.
    """

    gmail_message_id: str = Field(
        description="Unique Gmail message identifier for the email being classified."
    )
    subject: str | None = Field(
        default=None,
        description="Email subject line.  May be absent for drafts or malformed messages.",
    )
    body_text: str | None = Field(
        default=None,
        description="Plain-text body content.  May be absent for HTML-only emails.",
    )
    snippet: str | None = Field(
        default=None,
        description="Short preview snippet provided by the Gmail API.",
    )
    sender_email: str = Field(
        description="Envelope sender address used as an optional signal by some classifiers.",
    )

    @model_validator(mode="after")
    def at_least_one_text_field_present(self) -> "EmailClassificationInput":
        """Ensure there is at least one non-empty text source for classification.

        Returns:
            The validated model instance.

        Raises:
            ValueError: When ``subject``, ``body_text``, and ``snippet`` are all
                absent or empty.
        """
        has_content = any(
            field is not None and field.strip()
            for field in (self.subject, self.body_text, self.snippet)
        )
        if not has_content:
            raise ValueError(
                "At least one of 'subject', 'body_text', or 'snippet' must contain text."
            )
        return self

    def build_classification_text(self, *, max_chars: int = 512) -> str:
        """Produce a single normalised string suitable for model input.

        Concatenates subject and body text with a separator, then truncates
        to ``max_chars`` to keep inference latency predictable.

        Args:
            max_chars: Maximum character length of the returned string.

        Returns:
            A non-empty string combining available text fields.
        """
        parts: list[str] = []

        if self.subject and self.subject.strip():
            parts.append(self.subject.strip())

        body = self.body_text or self.snippet or ""
        if body.strip():
            parts.append(body.strip())

        combined = " | ".join(parts)
        return combined[:max_chars]

    model_config = {"str_strip_whitespace": True}


# ---------------------------------------------------------------------------
# Result schema
# ---------------------------------------------------------------------------


class CategoryScore(BaseModel):
    """Holds the confidence score for a single candidate category.

    Returned as part of :class:`ClassificationResult` to allow callers to
    inspect the full score distribution produced by a classifier.
    """

    category: CategoryStr
    score: ConfidenceScore

    @field_validator("category")
    @classmethod
    def category_must_be_valid(cls, value: str) -> str:
        """Reject category values that are not in the canonical list.

        Args:
            value: Raw category string from the classifier.

        Returns:
            The validated category string.

        Raises:
            ValueError: When ``value`` is not in :data:`~core.constants.EMAIL_CATEGORIES`.
        """
        if value not in EMAIL_CATEGORIES:
            raise ValueError(
                f"'{value}' is not a recognised category. "
                f"Valid categories: {EMAIL_CATEGORIES}"
            )
        return value


class ClassificationResult(BaseModel):
    """Encapsulates the output produced by a single classifier invocation.

    Carries the winning category, its confidence score, the full score
    distribution, the method that produced the result, and a timestamp so
    audit records can be written without requiring additional context.
    """

    gmail_message_id: str = Field(
        description="Gmail message identifier that was classified."
    )
    category: CategoryStr = Field(
        description="The highest-confidence category assigned to the email."
    )
    confidence_score: ConfidenceScore = Field(
        description="Confidence of the winning category in the range [0.0, 1.0]."
    )
    all_scores: list[CategoryScore] = Field(
        default_factory=list,
        description=(
            "Full score distribution across all candidate categories, "
            "ordered by descending score."
        ),
    )
    method: str = Field(
        description=(
            "Classification method that produced this result.  "
            "One of the CLASSIFICATION_METHOD_* constants."
        )
    )
    classified_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=timezone.utc),
        description="UTC timestamp of when the classification was performed.",
    )

    @field_validator("category")
    @classmethod
    def category_must_be_valid(cls, value: str) -> str:
        """Reject category values that are not in the canonical list.

        Args:
            value: Raw category string from the classifier output.

        Returns:
            The validated category string.

        Raises:
            ValueError: When ``value`` is not in :data:`~core.constants.EMAIL_CATEGORIES`.
        """
        if value not in EMAIL_CATEGORIES:
            raise ValueError(
                f"'{value}' is not a recognised category. "
                f"Valid categories: {EMAIL_CATEGORIES}"
            )
        return value

    @field_validator("method")
    @classmethod
    def method_must_be_valid(cls, value: str) -> str:
        """Reject method identifiers that are not in the known set.

        Args:
            value: Raw method string from the classifier.

        Returns:
            The validated method string.

        Raises:
            ValueError: When ``value`` is not in :data:`VALID_CLASSIFICATION_METHODS`.
        """
        if value not in VALID_CLASSIFICATION_METHODS:
            raise ValueError(
                f"'{value}' is not a recognised classification method. "
                f"Valid methods: {sorted(VALID_CLASSIFICATION_METHODS)}"
            )
        return value

    @model_validator(mode="after")
    def winning_category_present_in_all_scores(self) -> "ClassificationResult":
        """Ensure the winning category appears in the full score distribution.

        Returns:
            The validated model instance.

        Raises:
            ValueError: When ``all_scores`` is non-empty and does not include
                the winning ``category``.
        """
        if self.all_scores:
            scored_categories = {cs.category for cs in self.all_scores}
            if self.category not in scored_categories:
                raise ValueError(
                    f"Winning category '{self.category}' must appear in 'all_scores'."
                )
        return self

    def is_high_confidence(self, threshold: float) -> bool:
        """Return ``True`` when the result meets or exceeds a confidence threshold.

        Args:
            threshold: Minimum acceptable confidence score in ``[0.0, 1.0]``.

        Returns:
            Boolean indicating whether ``confidence_score >= threshold``.
        """
        return self.confidence_score >= threshold

    model_config = {"frozen": True}
