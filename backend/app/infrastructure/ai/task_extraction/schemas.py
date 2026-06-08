"""Data-transfer objects for the task extraction subsystem."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated

from pydantic import BaseModel, Field, field_validator, model_validator

# ---------------------------------------------------------------------------
# Value types
# ---------------------------------------------------------------------------

PriorityValue = Annotated[
    int,
    Field(
        ge=0,
        le=100,
        description="Task priority expressed as an integer score.",
    ),
]

ConfidenceScore = Annotated[
    float,
    Field(
        ge=0.0,
        le=1.0,
        description="Normalised extraction confidence score in the range [0.0, 1.0].",
    ),
]


# ---------------------------------------------------------------------------
# Request schema
# ---------------------------------------------------------------------------


class TaskExtractionRequest(BaseModel):
    """Carries the context required to extract tasks from an email."""

    title: str | None = Field(
        default=None,
        description="Email subject or title context, when available.",
    )
    description: str | None = Field(
        default=None,
        description="Email body/summary context, when available.",
    )
    source_sender: str = Field(
        min_length=1,
        description="Sender of the source message (email address and/or display name).",
    )
    source_company: str | None = Field(
        default=None,
        description="Associated company context when available.",
    )

    model_config = {"str_strip_whitespace": True}


# ---------------------------------------------------------------------------
# Extracted task schema
# ---------------------------------------------------------------------------


class ExtractedTask(BaseModel):
    """A single validated task extracted from a source message."""

    title: Annotated[
        str,
        Field(
            min_length=1,
            description="Human-readable task title.",
        ),
    ]
    description: str | None = Field(
        default=None,
        description="Optional longer description of the task.",
    )
    priority: PriorityValue = Field(
        ...,
        description="Task priority score in the inclusive range [0, 100].",
    )
    due_date: datetime | None = Field(
        default=None,
        description="Optional due date for the task.",
    )
    confidence_score: ConfidenceScore = Field(
        ...,
        description="Extraction confidence in the inclusive range [0.0, 1.0].",
    )
    # Optional: populated by the service layer from request metadata after
    # LLM response parsing; the model is not asked to emit this field.
    source_sender: str | None = Field(
        default=None,
        description="Sender of the source message used as extraction context.",
    )
    source_company: str | None = Field(
        default=None,
        description="Company of the source message used as extraction context.",
    )

    @field_validator("priority")
    @classmethod
    def validate_priority_values(cls, value: int) -> int:
        """Validate that priority is within the allowed range [0, 100]."""
        if value < 0 or value > 100:
            raise ValueError("priority must be an integer between 0 and 100.")
        return value

    @field_validator("confidence_score")
    @classmethod
    def validate_confidence_score_range(cls, value: float) -> float:
        """Validate that confidence_score is within [0.0, 1.0]."""
        if value < 0.0 or value > 1.0:
            raise ValueError(
                "confidence_score must be a float between 0.0 and 1.0."
            )
        return value

    @field_validator("title")
    @classmethod
    def validate_empty_titles(cls, value: str) -> str:
        """Reject empty or whitespace-only task titles."""
        if not value or not value.strip():
            raise ValueError("title must not be empty.")
        return value

    model_config = {"str_strip_whitespace": True, "frozen": True}


# ---------------------------------------------------------------------------
# Result schema
# ---------------------------------------------------------------------------


class TaskExtractionResult(BaseModel):
    """Encapsulates the task extraction output produced by the AI layer."""

    tasks: list[ExtractedTask] = Field(
        default_factory=list,
        description="List of extracted tasks.",
    )
    extraction_confidence: ConfidenceScore = Field(
        ...,
        description="Overall extraction confidence in the inclusive range [0.0, 1.0].",
    )
    extracted_task_count: int = Field(
        ...,
        description="Total number of extracted tasks.",
    )

    @model_validator(mode="after")
    def validate_extracted_task_count(self) -> "TaskExtractionResult":
        """Ensure extracted_task_count matches the number of returned tasks."""
        if self.extracted_task_count != len(self.tasks):
            raise ValueError(
                "extracted_task_count must match the number of items in tasks."
            )
        if self.extracted_task_count < 0:
            raise ValueError("extracted_task_count must be non-negative.")
        return self

    model_config = {"frozen": True, "str_strip_whitespace": True}


def _utcnow() -> datetime:
    """Return the current UTC time with timezone information."""
    return datetime.now(tz=timezone.utc)