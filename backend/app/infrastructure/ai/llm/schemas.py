"""Data-transfer objects for the LLM summarization provider contract."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

# ---------------------------------------------------------------------------
# Value types
# ---------------------------------------------------------------------------

ConfidenceScore = Annotated[
    float,
    Field(
        ge=0.0,
        le=1.0,
        description="Normalised confidence score in the range [0.0, 1.0].",
    ),
]

PriorityScore = Annotated[
    int,
    Field(
        ge=0,
        le=100,
        description="Priority score in the inclusive range [0, 100].",
    ),
]


# ---------------------------------------------------------------------------
# Request schema
# ---------------------------------------------------------------------------


class SummaryRequest(BaseModel):
    """Carries the data required to generate an email summary."""

    email_id: UUID = Field(
        description="Database identifier for the email being summarised."
    )
    subject: str | None = Field(
        default=None,
        description="Email subject line, when available.",
    )
    body_text: str | None = Field(
        default=None,
        description="Plain-text body content, when available.",
    )
    sender_name: str | None = Field(
        default=None,
        description="Display name of the sender, when available.",
    )
    sender_email: str = Field(
        min_length=1,
        description="Sender email address used as a contextual signal.",
    )
    classification: str | None = Field(
        default=None,
        description="Current email classification category, when available.",
    )
    confidence_score: ConfidenceScore | None = Field(
        default=None,
        description="Classification confidence score in the range [0.0, 1.0].",
    )
    priority_score: PriorityScore | None = Field(
        default=None,
        description="Computed priority score in the range [0, 100].",
    )
    is_action_required: bool | None = Field(
        default=None,
        description="Whether the email has been flagged as action required.",
    )
    received_at: datetime = Field(
        description="UTC timestamp indicating when the message was received.",
    )

    @model_validator(mode="after")
    def require_email_text(self) -> "SummaryRequest":
        """Ensure the request contains at least one usable text field.

        Returns:
            The validated model instance.

        Raises:
            ValueError: When both ``subject`` and ``body_text`` are empty or missing.
        """
        has_subject = bool(self.subject and self.subject.strip())
        has_body = bool(self.body_text and self.body_text.strip())
        if not (has_subject or has_body):
            raise ValueError(
                "At least one of 'subject' or 'body_text' must contain text."
            )
        return self

    model_config = {"str_strip_whitespace": True}


# ---------------------------------------------------------------------------
# Response schema
# ---------------------------------------------------------------------------


class SummaryResponse(BaseModel):
    """Encapsulates a validated LLM-generated summary."""

    email_id: UUID = Field(
        description="Database identifier for the email that was summarised."
    )
    summary: str = Field(
        min_length=1,
        description="Human-readable summary produced by the LLM provider.",
    )
    provider: str = Field(
        min_length=1,
        description="Canonical provider identifier that generated the summary.",
    )
    model: str = Field(
        min_length=1,
        description="Underlying model identifier used for generation.",
    )
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=timezone.utc),
        description="UTC timestamp when the summary was generated.",
    )

    @field_validator("summary")
    @classmethod
    def summary_must_not_be_empty(cls, value: str) -> str:
        """Reject blank summary text.

        Args:
            value: Raw summary text returned by the provider.

        Returns:
            The validated summary text.

        Raises:
            ValueError: When the summary contains only whitespace.
        """
        if not value.strip():
            raise ValueError("Summary text must not be empty.")
        return value

    model_config = {"frozen": True, "str_strip_whitespace": True}
