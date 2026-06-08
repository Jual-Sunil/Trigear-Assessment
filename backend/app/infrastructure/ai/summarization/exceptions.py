"""Exception hierarchy for the email summarization subsystem."""


class EmailSummarizationError(Exception):
    """Base exception for all email summarization failures.

    All summarization implementations must raise subclasses of this exception
    so callers can handle summarization-specific failures uniformly.
    """

    def __init__(self, message: str, *, cause: BaseException | None = None) -> None:
        """Initialise the exception with an optional chained cause.

        Args:
            message: Human-readable description of the failure.
            cause: Original exception that triggered this error, if any.
        """
        super().__init__(message)
        self.__cause__ = cause


class EmailSummaryInputError(EmailSummarizationError):
    """Raised when the input provided to a summarization contract is invalid."""

    def __init__(self, message: str, *, cause: BaseException | None = None) -> None:
        """Initialise with a description of the invalid input.

        Args:
            message: Description of why the input is invalid.
            cause: Original exception that triggered this error, if any.
        """
        super().__init__(message, cause=cause)


class EmailSummaryResultValidationError(EmailSummarizationError):
    """Raised when generated summary output cannot be validated."""

    def __init__(
        self,
        message: str,
        *,
        cause: BaseException | None = None,
    ) -> None:
        """Initialise with a description of the validation failure.

        Args:
            message: Description of the validation failure.
            cause: Original exception that triggered this error, if any.
        """
        super().__init__(message, cause=cause)
