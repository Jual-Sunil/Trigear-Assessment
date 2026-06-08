"""Exception hierarchy for the priority scoring subsystem."""


class PriorityScoringError(Exception):
    """Base exception for all priority scoring failures.

    All priority scorer implementations must raise subclasses of this exception
    so callers can handle scoring-specific errors uniformly.
    """

    def __init__(self, message: str, *, cause: BaseException | None = None) -> None:
        """Initialise the exception with an optional chained cause.

        Args:
            message: Human-readable description of the failure.
            cause: Original exception that triggered this error, if any.
        """
        super().__init__(message)
        self.__cause__ = cause


class PriorityScorerNotReadyError(PriorityScoringError):
    """Raised when a scorer is invoked before it has been initialised."""

    def __init__(self, scorer_name: str) -> None:
        """Initialise with the name of the unready scorer.

        Args:
            scorer_name: Identifier of the scorer that is not ready.
        """
        super().__init__(
            f"Priority scorer '{scorer_name}' is not ready. "
            "Ensure the scorer has been loaded before calling score()."
        )
        self.scorer_name = scorer_name


class PriorityScoringInputError(PriorityScoringError):
    """Raised when the input provided to a scorer is invalid."""

    def __init__(self, message: str, *, cause: BaseException | None = None) -> None:
        """Initialise with a description of the invalid input.

        Args:
            message: Description of why the input is invalid.
            cause: Original exception that triggered this error, if any.
        """
        super().__init__(message, cause=cause)


class PriorityScoringInferenceError(PriorityScoringError):
    """Raised when scoring fails during execution."""

    def __init__(
        self,
        scorer_name: str,
        message: str,
        *,
        cause: BaseException | None = None,
    ) -> None:
        """Initialise with the scorer name and a description of the failure.

        Args:
            scorer_name: Identifier of the scorer that failed.
            message: Description of the scoring failure.
            cause: Original exception that triggered this error, if any.
        """
        super().__init__(
            f"Inference error in scorer '{scorer_name}': {message}",
            cause=cause,
        )
        self.scorer_name = scorer_name


class PriorityScoringTimeoutError(PriorityScoringError):
    """Raised when a scoring call exceeds the configured timeout."""

    def __init__(self, scorer_name: str, timeout_seconds: float) -> None:
        """Initialise with the scorer name and the elapsed timeout.

        Args:
            scorer_name: Identifier of the scorer that timed out.
            timeout_seconds: The timeout value that was exceeded, in seconds.
        """
        super().__init__(
            f"Priority scorer '{scorer_name}' timed out after {timeout_seconds}s."
        )
        self.scorer_name = scorer_name
        self.timeout_seconds = timeout_seconds


class LowPriorityConfidenceError(PriorityScoringError):
    """Raised when no scoring outcome meets the minimum confidence threshold."""

    def __init__(
        self,
        scorer_name: str,
        best_score: int,
        threshold: int,
    ) -> None:
        """Initialise with scoring context that explains the failure.

        Args:
            scorer_name: Identifier of the scorer that returned low confidence.
            best_score: The highest score that was produced.
            threshold: The minimum score threshold that was not met.
        """
        super().__init__(
            f"Priority scorer '{scorer_name}' best score {best_score} is "
            f"below the required threshold of {threshold}."
        )
        self.scorer_name = scorer_name
        self.best_score = best_score
        self.threshold = threshold
