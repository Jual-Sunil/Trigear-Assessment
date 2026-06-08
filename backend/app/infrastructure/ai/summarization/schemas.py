"""Data-transfer objects for the email summarization subsystem."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

# ---------------------------------------------------------------------------
# Value types
# ---------------------------------------------------------------------------

SummaryText = Annotated[
    str,
    Field(
        min_length=1,
        description="Human-readable summary text.",
    ),
]

SummaryPoint = Annotated[
    str,
    Field(
        min_length=1,
        description="A concise bullet-point summary item.",
    ),
]

ActionItem = Annotated[
    str,
    Field(
        min_length=1,
        description="A concise actionable follow-up item.",
    ),
]


# ---------------------------------------------------------------------------
# Request schema
# ---------------------------------------------------------------------------


class EmailSummaryRequest(BaseModel):
    """Carries the email content required to generate a structured summary."""

    email_id: UUID | None = Field(
        default=None,
        description="Optional database identifier for the email being summarised.",
    )
    subject: str | None = Field(
        default=None,
        description="Email subject line, when available.",
    )
    sender: str | None = Field(
        default=None,
        description="Sender display name or sender email address, when available.",
    )
    body: str | None = Field(
        default=None,
        description="Plain-text email body, when available.",
    )
    received_at: datetime | None = Field(
        default=None,
        description="Optional UTC timestamp indicating when the email was received.",
    )

    @model_validator(mode="after")
    def require_content(self) -> "EmailSummaryRequest":
        """Ensure the request contains at least one usable content field.

        Returns:
            The validated model instance.

        Raises:
            ValueError: When ``subject``, ``sender``, and ``body`` are all empty or missing.
        """
        has_subject = bool(self.subject and self.subject.strip())
        has_sender = bool(self.sender and self.sender.strip())
        has_body = bool(self.body and self.body.strip())
        if not (has_subject or has_sender or has_body):
            raise ValueError(
                "At least one of 'subject', 'sender', or 'body' must contain text."
            )
        return self

    model_config = {"str_strip_whitespace": True}


# ---------------------------------------------------------------------------
# Response schema
# ---------------------------------------------------------------------------


class EmailSummaryResult(BaseModel):
    """Encapsulates a structured email summary produced by the AI layer."""

    email_id: UUID | None = Field(
        default=None,
        description="Optional database identifier for the summarized email.",
    )
    summary: SummaryText = Field(
        description="Concise natural-language summary of the email.",
    )
    key_points: list[SummaryPoint] = Field(
        default_factory=list,
        description="Important facts or themes extracted from the email.",
    )
    action_items: list[ActionItem] = Field(
        default_factory=list,
        description="Actionable follow-up items extracted from the email.",
    )
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=timezone.utc),
        description="UTC timestamp when the summary was generated.",
    )

    @field_validator("key_points", "action_items")
    @classmethod
    def items_must_not_be_blank(cls, value: list[str]) -> list[str]:
        """Reject blank list entries in structured summary fields.

        Args:
            value: Raw list of key points or action items.

        Returns:
            The validated list with whitespace-only entries rejected.

        Raises:
            ValueError: When any entry contains only whitespace.
        """
        for item in value:
            if not item.strip():
                raise ValueError("Summary list items must not be empty.")
        return value

    model_config = {"frozen": True, "str_strip_whitespace": True}
