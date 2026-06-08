"""Abstract base scorer contract for the email priority scoring subsystem."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod

from infrastructure.ai.priority.exceptions import (
    PriorityScorerNotReadyError,
    PriorityScoringInputError,
)
from infrastructure.ai.priority.schemas import (
    PriorityScoreInput,
    PriorityScoreResult,
)

logger = logging.getLogger(__name__)


class BasePriorityScorer(ABC):
    """Defines the interface that every priority scorer implementation must satisfy.

    Concrete scorers inherit from this class and implement :meth:`score` and
    :meth:`is_ready`.

    Design contract
    ---------------
    * :meth:`score` must only be callable when :meth:`is_ready` returns ``True``;
      otherwise it must raise
      :class:`~infrastructure.ai.priority.exceptions.PriorityScorerNotReadyError`.
    * :meth:`score` must always return a
      :class:`~infrastructure.ai.priority.schemas.PriorityScoreResult` whose
      ``method`` field matches :attr:`method_name`.
    * Implementations must never swallow exceptions silently; failures must
      propagate as subclasses of
      :class:`~infrastructure.ai.priority.exceptions.PriorityScoringError`.
    * Implementations must not log email content at any log level.
    """

    @property
    @abstractmethod
    def method_name(self) -> str:
        """Return the canonical method identifier for this scorer.

        The returned value should be a stable string suitable for persistence
        in audit logs and downstream processing.
        """

    @abstractmethod
    def is_ready(self) -> bool:
        """Report whether this scorer is initialised and ready to serve requests."""

    @abstractmethod
    def score(self, input_data: PriorityScoreInput) -> PriorityScoreResult:
        """Score a single email and return a structured priority result.

        Args:
            input_data: Validated input DTO carrying the email metadata required
                for priority scoring.

        Returns:
            A :class:`~infrastructure.ai.priority.schemas.PriorityScoreResult`
            with a valid score in the inclusive range ``[0, 100]``.

        Raises:
            PriorityScorerNotReadyError: When the scorer has not been initialised.
            PriorityScoringInputError: When ``input_data`` is invalid for scoring.
            PriorityScoringInferenceError: When the underlying scorer raises an
                unexpected error during scoring.
            PriorityScoringTimeoutError: When scoring exceeds the configured deadline.
            LowPriorityConfidenceError: When the scorer cannot produce a sufficiently
                confident result.
        """

    def load(self) -> None:
        """Load resources required by this scorer.

        Subclasses that require heavyweight initialisation should override this
        method. The default implementation is a no-op.
        """
        logger.debug("load() called on %s (no-op default).", self.__class__.__name__)

    def unload(self) -> None:
        """Release resources held by this scorer.

        Subclasses that hold references to large in-memory resources should
        override this method to free that memory. The default implementation
        is a no-op.
        """
        logger.debug("unload() called on %s (no-op default).", self.__class__.__name__)

    def _assert_ready(self) -> None:
        """Raise :class:`PriorityScorerNotReadyError` if the scorer is not ready."""
        if not self.is_ready():
            raise PriorityScorerNotReadyError(self.__class__.__name__)

    def _assert_score_in_range(self, score: int) -> int:
        """Validate the final score is within the accepted priority range.

        Args:
            score: Proposed priority score.

        Returns:
            The original score when it is inside the accepted range.

        Raises:
            PriorityScoringInputError: When the score is outside ``[0, 100]``.
        """
        if score < 0 or score > 100:
            raise PriorityScoringInputError(
                f"Priority score must be within [0, 100], got {score}."
            )
        return score

    def __repr__(self) -> str:
        """Return a debug representation of this scorer instance."""
        return (
            f"<{self.__class__.__name__} method={self.method_name!r} "
            f"ready={self.is_ready()}>"
        )
