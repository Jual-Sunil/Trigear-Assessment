"""Exception hierarchy for the LLM summarization provider subsystem."""


class LLMProviderError(Exception):
    """Base exception for all LLM provider failures.

    All provider implementations must raise subclasses of this exception so
    callers can handle summarization-specific failures uniformly.
    """

    def __init__(self, message: str, *, cause: BaseException | None = None) -> None:
        """Initialise the exception with an optional chained cause.

        Args:
            message: Human-readable description of the failure.
            cause: Original exception that triggered this error, if any.
        """
        super().__init__(message)
        self.__cause__ = cause


class LLMProviderNotReadyError(LLMProviderError):
    """Raised when a provider is invoked before it is ready."""

    def __init__(self, provider_name: str) -> None:
        """Initialise with the name of the unready provider.

        Args:
            provider_name: Identifier of the provider that is not ready.
        """
        super().__init__(
            f"LLM provider '{provider_name}' is not ready. "
            "Ensure the provider has been configured before calling summarize()."
        )
        self.provider_name = provider_name


class LLMProviderInputError(LLMProviderError):
    """Raised when the input provided to a provider is invalid."""

    def __init__(self, message: str, *, cause: BaseException | None = None) -> None:
        """Initialise with a description of the invalid input.

        Args:
            message: Description of why the input is invalid.
            cause: Original exception that triggered this error, if any.
        """
        super().__init__(message, cause=cause)


class LLMProviderResponseValidationError(LLMProviderError):
    """Raised when provider output cannot be validated against the response schema."""

    def __init__(
        self,
        provider_name: str,
        message: str,
        *,
        cause: BaseException | None = None,
    ) -> None:
        """Initialise with the provider name and validation failure details.

        Args:
            provider_name: Identifier of the provider that returned invalid output.
            message: Description of the validation failure.
            cause: Original exception that triggered this error, if any.
        """
        super().__init__(
            f"Response validation error in provider '{provider_name}': {message}",
            cause=cause,
        )
        self.provider_name = provider_name


class LLMProviderTimeoutError(LLMProviderError):
    """Raised when a provider call exceeds the configured timeout."""

    def __init__(self, provider_name: str, timeout_seconds: float) -> None:
        """Initialise with the provider name and the elapsed timeout.

        Args:
            provider_name: Identifier of the provider that timed out.
            timeout_seconds: The timeout value that was exceeded, in seconds.
        """
        super().__init__(
            f"LLM provider '{provider_name}' timed out after {timeout_seconds}s."
        )
        self.provider_name = provider_name
        self.timeout_seconds = timeout_seconds


class LLMProviderHealthCheckError(LLMProviderError):
    """Raised when a provider health check fails."""

    def __init__(
        self,
        provider_name: str,
        message: str,
        *,
        cause: BaseException | None = None,
    ) -> None:
        """Initialise with the provider name and health check failure details.

        Args:
            provider_name: Identifier of the provider whose health check failed.
            message: Description of the health check failure.
            cause: Original exception that triggered this error, if any.
        """
        super().__init__(
            f"Health check error in provider '{provider_name}': {message}",
            cause=cause,
        )
        self.provider_name = provider_name
