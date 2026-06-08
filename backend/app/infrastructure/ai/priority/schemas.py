"""Data-transfer objects and value types for the priority scoring subsystem."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field

from core.constants import PRIORITY_SCORE_MAX, PRIORITY_SCORE_MIN

# ---------------------------------------------------------------------------
# Value types
# ---------------------------------------------------------------------------

PriorityScore = Annotated[
    int,
    Field(
        ge=PRIORITY_SCORE_MIN,
        le=PRIORITY_SCORE_MAX,
        description="Priority score in the inclusive range [0, 100].",
    ),
]

PriorityFactorWeight = Annotated[
    float,
    Field(
        ge=0.0,
        le=1.0,
        description="Relative weight assigned to a priority factor in the range [0.0, 1.0].",
    ),
]


# ---------------------------------------------------------------------------
# Input schema
# ---------------------------------------------------------------------------


class PriorityScoreInput(BaseModel):
    """Carries the signals required to compute an email priority score.

    The scorer should treat this model as a pure contract.  It contains only
    the normalized email attributes that downstream scoring strategies may
    inspect when determining priority.
    """

    email_id: UUID = Field(
        description="Database identifier for the email being scored."
    )
    sender_email: str = Field(
        min_length=1,
        description="Sender email address used for reputation-based signals.",
    )
    subject: str | None = Field(
        default=None,
        description="Email subject line, when available.",
    )
    body_text: str | None = Field(
        default=None,
        description="Plain-text email body, when available.",
    )
    classification: str | None = Field(
        default=None,
        description="Current email classification category, when available.",
    )
    confidence_score: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Classification confidence score in the range [0.0, 1.0].",
    )
    is_action_required: bool | None = Field(
        default=None,
        description="Whether the email has been flagged as action required.",
    )
    received_at: datetime = Field(
        description="UTC timestamp indicating when the email was received.",
    )

    model_config = {"str_strip_whitespace": True}


# ---------------------------------------------------------------------------
# Output schema
# ---------------------------------------------------------------------------


class PriorityFactor(BaseModel):
    """Represents one scored factor contributing to the final priority result."""

    name: str = Field(
        min_length=1,
        description="Canonical factor name, such as sender reputation or deadline detection.",
    )
    score: PriorityScore = Field(
        description="Factor score in the inclusive range [0, 100].",
    )
    weight: PriorityFactorWeight = Field(
        description="Relative weight assigned to this factor.",
    )
    explanation: str | None = Field(
        default=None,
        description="Human-readable explanation describing why the factor was assigned.",
    )

    model_config = {"frozen": True, "str_strip_whitespace": True}


class PriorityScoreResult(BaseModel):
    """Encapsulates the output of a single priority scoring invocation."""

    email_id: UUID = Field(
        description="Database identifier for the email that was scored."
    )
    priority_score: PriorityScore = Field(
        description="Final priority score in the inclusive range [0, 100].",
    )
    factors: list[PriorityFactor] = Field(
        default_factory=list,
        description="Factor breakdown used to produce the final score.",
    )
    method: str = Field(
        min_length=1,
        description="Canonical scoring method identifier used to produce this result.",
    )
    scored_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=timezone.utc),
        description="UTC timestamp of when the score was computed.",
    )

    model_config = {"frozen": True, "str_strip_whitespace": True}
