"""Exception hierarchy for the career extraction subsystem."""

from __future__ import annotations


class CareerExtractionError(Exception):
    """Base exception for all career extraction failures."""

    def __init__(
        self,
        message: str,
        *,
        cause: BaseException | None = None,
    ) -> None:
        """Initialise the exception with an optional chained cause.

        Args:
            message: Human-readable description of the failure.
            cause: Original exception that triggered this error, if any.
        """
        super().__init__(message)
        self.__cause__ = cause


class CareerExtractionFailureError(CareerExtractionError):
    """Raised when career extraction fails due to an upstream error."""

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


class CareerExtractionValidationError(CareerExtractionError):
    """Raised when extracted career data fails schema validation."""

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


class CareerExtractionMalformedResponseError(CareerExtractionError):
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

