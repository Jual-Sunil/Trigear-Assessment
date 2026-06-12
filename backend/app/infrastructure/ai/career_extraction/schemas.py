"""Pydantic schemas for the career extraction subsystem.

This module defines the request and response contracts for extracting
job opportunities and interview details from email content.

No extraction logic is implemented here.
"""

from __future__ import annotations

import re
from typing import Annotated

from pydantic import BaseModel, EmailStr, Field, field_validator

from infrastructure.ai.career_extraction.exceptions import (
    CareerExtractionValidationError,
)


_URL_SCHEME_RE = re.compile(r"^https?://", re.IGNORECASE)


ConfidenceScore = Annotated[
    float,
    Field(
        ge=0.0,
        le=1.0,
        description="Normalised extraction confidence score in the range [0.0, 1.0].",
    ),
]


NonEmptyCompanyName = Annotated[
    str,
    Field(
        min_length=1,
        description="Company name associated with the extracted career item.",
    ),
]


def _validate_confidence_score_range(value: float) -> float:
    """Validate that confidence_score is within [0.0, 1.0].

    Args:
        value: Raw confidence score.

    Returns:
        The validated score.

    Raises:
        CareerExtractionValidationError: If the score is outside the allowed range.
    """
    if value < 0.0 or value > 1.0:
        raise CareerExtractionValidationError(
            "confidence_score must be a float between 0.0 and 1.0."
        )
    return value


def _validate_non_empty_company_name(value: str) -> str:
    """Reject empty or whitespace-only company names.

    Args:
        value: Raw company name.

    Returns:
        The validated company name.

    Raises:
        CareerExtractionValidationError: If the company name is empty.
    """
    if value is None or not str(value).strip():
        raise CareerExtractionValidationError("company must not be empty.")
    return value.strip()


def _validate_http_url(value: str, *, field_name: str) -> str:
    """Validate that the URL uses http/https scheme and is non-empty.

    Args:
        value: Raw URL string. Must not be None (callers guard for None first).
        field_name: Field name for error messaging.

    Returns:
        The validated URL.

    Raises:
        CareerExtractionValidationError: If the URL is malformed or unsupported.
    """
    url = value.strip()
    if not url:
        raise CareerExtractionValidationError(f"{field_name} must not be empty.")
    if not _URL_SCHEME_RE.match(url):
        raise CareerExtractionValidationError(
            f"{field_name} must be a valid URL starting with http:// or https://."
        )
    return url


class JobOpportunityData(BaseModel):
    """Validated job opportunity data extracted from an email."""

    company: NonEmptyCompanyName = Field(..., description="Company name.")
    role: str = Field(..., min_length=1, description="Role title.")
    location: str | None = Field(default=None, description="Job location.")
    salary: str | None = Field(default=None, description="Salary information.")
    apply_link: str | None = Field(default=None, description="HTTP(S) URL to apply.")
    deadline: str | None = Field(default=None, description="Optional application deadline.")
    confidence_score: ConfidenceScore = Field(
        default=0.5,
        description="Extraction confidence in the inclusive range [0.0, 1.0].",
    )

    @field_validator("company")
    @classmethod
    def validate_company(cls, value: str) -> str:
        """Validate that company name is not empty."""
        return _validate_non_empty_company_name(value)

    @field_validator("confidence_score")
    @classmethod
    def validate_confidence(cls, value: float) -> float:
        """Validate confidence score range."""
        return _validate_confidence_score_range(value)

    @field_validator("apply_link", mode="before")
    @classmethod
    def validate_apply_link(cls, value: object) -> object:
        """Validate apply_link is a valid http/https URL when present."""
        if value is None:
            return None
        return _validate_http_url(str(value), field_name="apply_link")

    model_config = {"str_strip_whitespace": True, "frozen": True}


class InterviewData(BaseModel):
    """Validated interview data extracted from an email."""

    company: NonEmptyCompanyName = Field(..., description="Company name.")
    role: str = Field(..., min_length=1, description="Role title.")
    interview_date: str | None = Field(
        default=None,
        description="Optional interview date (as extracted text).",
    )
    meeting_link: str | None = Field(default=None, description="HTTP(S) URL for the meeting.")
    confidence_score: ConfidenceScore = Field(
        default=0.5,
        description="Extraction confidence in the inclusive range [0.0, 1.0].",
    )

    @field_validator("company")
    @classmethod
    def validate_company(cls, value: str) -> str:
        """Validate that company name is not empty."""
        return _validate_non_empty_company_name(value)

    @field_validator("confidence_score")
    @classmethod
    def validate_confidence(cls, value: float) -> float:
        """Validate confidence score range."""
        return _validate_confidence_score_range(value)

    @field_validator("meeting_link", mode="before")
    @classmethod
    def validate_meeting_link(cls, value: object) -> object:
        """Validate meeting_link is a valid http/https URL when present."""
        if value is None:
            return None
        return _validate_http_url(str(value), field_name="meeting_link")

    model_config = {"str_strip_whitespace": True, "frozen": True}


class CareerExtractionRequest(BaseModel):
    """Carries the context required to extract jobs and interviews."""

    subject: str | None = Field(
        default=None,
        description="Email subject line, when available.",
    )
    sender: str | None = Field(
        default=None,
        description="Sender email address (or display context) when available.",
    )
    body: str | None = Field(
        default=None,
        description="Email body text or summary context.",
    )
    body_html: str | None = Field(
        default=None,
        description="Raw HTML body for link extraction when body_text is absent/useless.",
    )

    model_config = {"str_strip_whitespace": True, "frozen": True}


class CareerExtractionResult(BaseModel):
    """Encapsulates the validated career extraction output."""

    job_opportunities: list[JobOpportunityData] = Field(
        default_factory=list,
        description="List of extracted job opportunities.",
    )
    interviews: list[InterviewData] = Field(
        default_factory=list,
        description="List of extracted interviews.",
    )
    extraction_confidence: ConfidenceScore = Field(
        ...,
        description="Overall extraction confidence in the inclusive range [0.0, 1.0].",
    )

    @field_validator("extraction_confidence")
    @classmethod
    def validate_extraction_confidence(cls, value: float) -> float:
        """Validate overall extraction confidence range."""
        return _validate_confidence_score_range(value)

    model_config = {"frozen": True, "str_strip_whitespace": True}

