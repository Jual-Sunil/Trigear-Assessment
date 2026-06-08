"""Exception hierarchy for the task extraction subsystem."""

from __future__ import annotations


class TaskExtractionError(Exception):
    """Base exception for all task extraction failures."""

    def __init__(self, message: str, *, cause: BaseException | None = None) -> None:
        """Initialise the exception with an optional chained cause.

        Args:
            message: Human-readable description of the failure.
            cause: Original exception that triggered this error, if any.
        """
        super().__init__(message)
        self.__cause__ = cause


class TaskExtractionFailureError(TaskExtractionError):
    """Raised when task extraction fails due to an upstream error."""

    def __init__(
        self,
        message: str,
        *,
        cause: BaseException | None = None,
    ) -> None:
        """Initialise the exception.

        Args:
            message: Description of the extraction failure.
            cause: Original exception that triggered this error, if any.
        """
        super().__init__(message, cause=cause)


class TaskExtractionValidationError(TaskExtractionError):
    """Raised when extracted data fails schema validation."""

    def __init__(
        self,
        message: str,
        *,
        cause: BaseException | None = None,
    ) -> None:
        """Initialise the exception.

        Args:
            message: Description of the validation failure.
            cause: Original exception that triggered this error, if any.
        """
        super().__init__(message, cause=cause)


class TaskExtractionMalformedResponseError(TaskExtractionError):
    """Raised when the AI provider returns a structurally malformed response."""

    def __init__(
        self,
        message: str,
        *,
        cause: BaseException | None = None,
    ) -> None:
        """Initialise the exception.

        Args:
            message: Description of why the response is malformed.
            cause: Original exception that triggered this error, if any.
        """
        super().__init__(message, cause=cause)

