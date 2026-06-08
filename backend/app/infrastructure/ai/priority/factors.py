"""Deterministic factor scorers used by the priority scoring subsystem."""

from __future__ import annotations

import re
from abc import ABC
from typing import Final

from core.constants import (
    EMAIL_CATEGORY_FINANCE,
    EMAIL_CATEGORY_INTERVIEW,
    EMAIL_CATEGORY_JOB_OPPORTUNITY,
    EMAIL_CATEGORY_NEWSLETTER,
    EMAIL_CATEGORY_OTHER,
    EMAIL_CATEGORY_PERSONAL,
    EMAIL_CATEGORY_PROMOTION,
    EMAIL_CATEGORY_SPAM,
    EMAIL_CATEGORY_WORK,
    PRIORITY_SCORE_HIGH_THRESHOLD,
    PRIORITY_SCORE_MAX,
    PRIORITY_SCORE_MEDIUM_THRESHOLD,
)
from infrastructure.ai.priority.base import BasePriorityScorer
from infrastructure.ai.priority.schemas import PriorityFactor, PriorityScoreInput

SENDER_REPUTATION_FACTOR_NAME: Final[str] = "sender_reputation"
DEADLINE_DETECTION_FACTOR_NAME: Final[str] = "deadline_detection"
ACTION_REQUIRED_FACTOR_NAME: Final[str] = "action_required"
CLASSIFICATION_WEIGHT_FACTOR_NAME: Final[str] = "classification_weight"

SENDER_REPUTATION_FACTOR_WEIGHT: Final[float] = 0.30
DEADLINE_DETECTION_FACTOR_WEIGHT: Final[float] = 0.25
ACTION_REQUIRED_FACTOR_WEIGHT: Final[float] = 0.25
CLASSIFICATION_WEIGHT_FACTOR_WEIGHT: Final[float] = 0.20

URGENT_KEYWORDS: Final[tuple[str, ...]] = (
    "urgent",
    "asap",
    "deadline",
    "due",
    "by ",
    "before ",
    "respond by",
    "apply by",
    "final notice",
)

ACTION_KEYWORDS: Final[tuple[str, ...]] = (
    "action required",
    "please reply",
    "please respond",
    "need your input",
    "please review",
    "approval needed",
    "confirm",
    "schedule",
    "follow up",
)

DATE_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"(?i)\b(?:"
    r"\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?"
    r"|(?:mon|tue|wed|thu|fri|sat|sun)(?:day)?"
    r"|today|tomorrow|tonight|next week|next month"
    r")\b"
)

NO_REPLY_PATTERNS: Final[tuple[str, ...]] = (
    "no-reply",
    "noreply",
    "do-not-reply",
    "donotreply",
    "mailer-daemon",
    "postmaster",
)

PUBLIC_EMAIL_DOMAINS: Final[tuple[str, ...]] = (
    "gmail.com",
    "outlook.com",
    "hotmail.com",
    "live.com",
    "yahoo.com",
    "icloud.com",
)


def _combine_text(input_data: PriorityScoreInput) -> str:
    """Build a normalised searchable text blob from the available email fields."""
    parts: list[str] = []

    if input_data.subject and input_data.subject.strip():
        parts.append(input_data.subject.strip())

    if input_data.body_text and input_data.body_text.strip():
        parts.append(input_data.body_text.strip())

    return " ".join(parts).lower()


def _count_matches(text: str, keywords: tuple[str, ...]) -> int:
    """Count how many distinct keyword signals are present in the text."""
    return sum(1 for keyword in keywords if keyword in text)


def _bounded_score(score: int) -> int:
    """Clamp a score to the accepted priority range."""
    return max(0, min(PRIORITY_SCORE_MAX, score))


class _BaseFactorScorer(BasePriorityScorer, ABC):
    """Shared deterministic scorer behaviour for standalone priority factors."""

    @property
    def is_ready(self) -> bool:  # type: ignore[override]
        """Return ``True`` because these scorers are stateless and ready by default."""
        return True

    def _make_factor(
        self,
        *,
        name: str,
        score: int,
        weight: float,
        explanation: str,
    ) -> PriorityFactor:
        """Create a validated :class:`PriorityFactor` instance."""
        validated_score = self._assert_score_in_range(_bounded_score(score))
        return PriorityFactor(
            name=name,
            score=validated_score,
            weight=weight,
            explanation=explanation,
        )

    def load(self) -> None:
        """Keep the default no-op lifecycle hook explicit for deterministic scorers."""
        super().load()

    def unload(self) -> None:
        """Keep the default no-op lifecycle hook explicit for deterministic scorers."""
        super().unload()


class SenderReputationFactor(_BaseFactorScorer):
    """Score emails based on sender address signals that imply sender reputation."""

    @property
    def method_name(self) -> str:
        """Return the canonical method name for sender reputation scoring."""
        return SENDER_REPUTATION_FACTOR_NAME

    def score(self, input_data: PriorityScoreInput) -> PriorityFactor:
        """Score sender reputation signals and return a factor contribution."""
        self._assert_ready()

        sender_email = input_data.sender_email.strip().lower()
        local_part, _, domain = sender_email.partition("@")

        score = 55
        explanation = "Neutral sender reputation signal."

        if not domain:
            score = 20
            explanation = "Sender email is malformed or missing a domain."
        else:
            if any(pattern in sender_email for pattern in NO_REPLY_PATTERNS):
                score = 20
                explanation = "Automated no-reply sender detected."
            elif domain in PUBLIC_EMAIL_DOMAINS:
                score = 45
                explanation = "Sender uses a common public email provider."
            elif domain.count(".") >= 1:
                score = 75
                explanation = "Sender appears to use a structured domain."
            if local_part and "." in local_part and score >= 55:
                score = min(PRIORITY_SCORE_MAX, score + 10)
                explanation = "Sender address resembles a named mailbox."

        return self._make_factor(
            name=SENDER_REPUTATION_FACTOR_NAME,
            score=score,
            weight=SENDER_REPUTATION_FACTOR_WEIGHT,
            explanation=explanation,
        )


class DeadlineDetectionFactor(_BaseFactorScorer):
    """Score emails that mention deadlines, dates, or time-sensitive language."""

    @property
    def method_name(self) -> str:
        """Return the canonical method name for deadline detection scoring."""
        return DEADLINE_DETECTION_FACTOR_NAME

    def score(self, input_data: PriorityScoreInput) -> PriorityFactor:
        """Score deadline-related signals and return a factor contribution."""
        self._assert_ready()

        text = _combine_text(input_data)
        keyword_hits = _count_matches(text, URGENT_KEYWORDS)
        action_hits = _count_matches(text, ACTION_KEYWORDS)
        date_hits = len(DATE_PATTERN.findall(text))

        score = 0
        if keyword_hits or date_hits:
            score = 30 + (keyword_hits * 15) + (date_hits * 20) + (action_hits * 5)

        if "deadline" in text and date_hits:
            score = min(PRIORITY_SCORE_MAX, score + 15)

        if score >= PRIORITY_SCORE_HIGH_THRESHOLD:
            explanation = "Explicit deadline language and date cues were detected."
        elif score >= PRIORITY_SCORE_MEDIUM_THRESHOLD:
            explanation = "Time-sensitive wording was detected in the email."
        elif score > 0:
            explanation = "Weak deadline-related signals were detected."
        else:
            explanation = "No deadline-related signals were detected."

        return self._make_factor(
            name=DEADLINE_DETECTION_FACTOR_NAME,
            score=score,
            weight=DEADLINE_DETECTION_FACTOR_WEIGHT,
            explanation=explanation,
        )


class ActionRequiredFactor(_BaseFactorScorer):
    """Score emails that explicitly ask the recipient to act or respond."""

    @property
    def method_name(self) -> str:
        """Return the canonical method name for action-required scoring."""
        return ACTION_REQUIRED_FACTOR_NAME

    def score(self, input_data: PriorityScoreInput) -> PriorityFactor:
        """Score action-request signals and return a factor contribution."""
        self._assert_ready()

        text = _combine_text(input_data)
        keyword_hits = _count_matches(text, ACTION_KEYWORDS)
        action_flag = 1 if input_data.is_action_required else 0

        score = 10 + (keyword_hits * 18) + (action_flag * 50)
        if action_flag and keyword_hits:
            score = min(PRIORITY_SCORE_MAX, score + 10)

        if score >= PRIORITY_SCORE_HIGH_THRESHOLD:
            explanation = "The email explicitly requires action from the recipient."
        elif score >= PRIORITY_SCORE_MEDIUM_THRESHOLD:
            explanation = "The email likely requires a response or follow-up."
        elif score > 0:
            explanation = "Limited action-oriented language was detected."
        else:
            explanation = "No action-required signals were detected."

        if not action_flag and keyword_hits == 0:
            score = 0

        return self._make_factor(
            name=ACTION_REQUIRED_FACTOR_NAME,
            score=score,
            weight=ACTION_REQUIRED_FACTOR_WEIGHT,
            explanation=explanation,
        )


class ClassificationWeightFactor(_BaseFactorScorer):
    """Score emails using the existing classification category and confidence."""

    CLASSIFICATION_BASE_SCORES: Final[dict[str, int]] = {
        EMAIL_CATEGORY_INTERVIEW: 100,
        EMAIL_CATEGORY_JOB_OPPORTUNITY: 92,
        EMAIL_CATEGORY_WORK: 80,
        EMAIL_CATEGORY_FINANCE: 72,
        EMAIL_CATEGORY_PERSONAL: 55,
        EMAIL_CATEGORY_PROMOTION: 30,
        EMAIL_CATEGORY_NEWSLETTER: 20,
        EMAIL_CATEGORY_OTHER: 45,
        EMAIL_CATEGORY_SPAM: 0,
    }

    @property
    def method_name(self) -> str:
        """Return the canonical method name for classification weighting."""
        return CLASSIFICATION_WEIGHT_FACTOR_NAME

    def score(self, input_data: PriorityScoreInput) -> PriorityFactor:
        """Score category weighting and return a factor contribution."""
        self._assert_ready()

        category = (input_data.classification or EMAIL_CATEGORY_OTHER).strip()
        base_score = self.CLASSIFICATION_BASE_SCORES.get(category, 45)
        confidence_multiplier = input_data.confidence_score if input_data.confidence_score is not None else 0.5

        score = round(base_score * confidence_multiplier)
        explanation = (
            f"Classification '{category}' with confidence "
            f"{confidence_multiplier:.2f} produced a weighted contribution."
        )

        if category not in self.CLASSIFICATION_BASE_SCORES:
            explanation = "Unknown classification category was treated as a neutral signal."

        return self._make_factor(
            name=CLASSIFICATION_WEIGHT_FACTOR_NAME,
            score=score,
            weight=CLASSIFICATION_WEIGHT_FACTOR_WEIGHT,
            explanation=explanation,
        )
