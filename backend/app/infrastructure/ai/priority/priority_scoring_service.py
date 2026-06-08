"""Priority scoring orchestration service."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from core.constants import PRIORITY_SCORE_MAX, PRIORITY_SCORE_MIN
from infrastructure.ai.priority.factors import (
    ActionRequiredFactor,
    ClassificationWeightFactor,
    DeadlineDetectionFactor,
    SenderReputationFactor,
)
from infrastructure.ai.priority.schemas import PriorityScoreInput, PriorityScoreResult
from infrastructure.database.models.email import Email

PRIORITY_SCORING_METHOD_NAME: Final[str] = "priority_scoring_service"


@dataclass(frozen=True, slots=True)
class PriorityScoringWeights:
    """Service-level weights used to combine factor scores."""

    sender_reputation: float = 0.30
    deadline_detection: float = 0.25
    action_required: float = 0.25
    classification_weight: float = 0.20

    def __post_init__(self) -> None:
        """Validate the configured weights."""
        weights = (
            self.sender_reputation,
            self.deadline_detection,
            self.action_required,
            self.classification_weight,
        )
        if any(weight < 0.0 for weight in weights):
            raise ValueError("Priority scoring weights must be non-negative.")
        if sum(weights) <= 0.0:
            raise ValueError("Priority scoring weights must sum to a value greater than zero.")

    def normalize(self) -> "PriorityScoringWeights":
        """Return weights scaled so their sum equals 1.0."""
        total = (
            self.sender_reputation
            + self.deadline_detection
            + self.action_required
            + self.classification_weight
        )
        if total == 1.0:
            return self

        return PriorityScoringWeights(
            sender_reputation=self.sender_reputation / total,
            deadline_detection=self.deadline_detection / total,
            action_required=self.action_required / total,
            classification_weight=self.classification_weight / total,
        )


class _ReadySenderReputationFactor(SenderReputationFactor):
    """Adapter that makes the imported factor usable with the base scorer contract."""

    def is_ready(self) -> bool:
        """Return ``True`` because the factor is stateless."""
        return True


class _ReadyDeadlineDetectionFactor(DeadlineDetectionFactor):
    """Adapter that makes the imported factor usable with the base scorer contract."""

    def is_ready(self) -> bool:
        """Return ``True`` because the factor is stateless."""
        return True


class _ReadyActionRequiredFactor(ActionRequiredFactor):
    """Adapter that makes the imported factor usable with the base scorer contract."""

    def is_ready(self) -> bool:
        """Return ``True`` because the factor is stateless."""
        return True


class _ReadyClassificationWeightFactor(ClassificationWeightFactor):
    """Adapter that makes the imported factor usable with the base scorer contract."""

    def is_ready(self) -> bool:
        """Return ``True`` because the factor is stateless."""
        return True


class PriorityScoringService:
    """Combine deterministic factor scorers into a final priority score."""

    def __init__(
        self,
        *,
        weights: PriorityScoringWeights | None = None,
        sender_reputation_factor: SenderReputationFactor | None = None,
        deadline_detection_factor: DeadlineDetectionFactor | None = None,
        action_required_factor: ActionRequiredFactor | None = None,
        classification_weight_factor: ClassificationWeightFactor | None = None,
    ) -> None:
        """Initialise the service with optional dependency overrides."""
        self._weights = (weights or PriorityScoringWeights()).normalize()
        self._sender_reputation_factor = sender_reputation_factor or _ReadySenderReputationFactor()
        self._deadline_detection_factor = deadline_detection_factor or _ReadyDeadlineDetectionFactor()
        self._action_required_factor = action_required_factor or _ReadyActionRequiredFactor()
        self._classification_weight_factor = (
            classification_weight_factor or _ReadyClassificationWeightFactor()
        )

    def score(self, email: Email) -> PriorityScoreResult:
        """Score an email and return a structured priority result."""
        input_data = self._build_input(email)
        factors = [
            self._sender_reputation_factor.score(input_data),
            self._deadline_detection_factor.score(input_data),
            self._action_required_factor.score(input_data),
            self._classification_weight_factor.score(input_data),
        ]
        priority_score = self._combine_scores(factors)

        return PriorityScoreResult(
            email_id=input_data.email_id,
            priority_score=priority_score,
            factors=factors,
            method=PRIORITY_SCORING_METHOD_NAME,
        )

    def _build_input(self, email: Email) -> PriorityScoreInput:
        """Convert an email entity into the scoring input contract."""
        return PriorityScoreInput(
            email_id=email.id,
            sender_email=email.sender_email,
            subject=email.subject,
            body_text=email.body_text,
            classification=email.classification,
            confidence_score=float(email.confidence_score) if email.confidence_score is not None else None,
            is_action_required=email.is_action_required,
            received_at=email.received_at,
        )

    def _combine_scores(self, factors: list) -> int:
        """Combine factor scores into a final bounded priority score."""
        weighted_score = (
            factors[0].score * self._weights.sender_reputation
            + factors[1].score * self._weights.deadline_detection
            + factors[2].score * self._weights.action_required
            + factors[3].score * self._weights.classification_weight
        )
        score = round(weighted_score)
        return max(PRIORITY_SCORE_MIN, min(PRIORITY_SCORE_MAX, score))
