"""Abstract base provider contract for the LLM summarization subsystem."""

from __future__ import annotations

from abc import ABC, abstractmethod

from infrastructure.ai.llm.schemas import SummaryRequest, SummaryResponse


class BaseLLMProvider(ABC):
    """Defines the interface that every LLM provider implementation must satisfy.

    Concrete providers (OpenAI, Claude, Gemini) inherit from this class and
    implement :meth:`summarize` and :meth:`health_check`.
    """

    @abstractmethod
    def summarize(self, request: SummaryRequest) -> SummaryResponse:
        """Generate a validated summary for a single email.

        Args:
            request: Validated summarization input DTO containing the email
                content and contextual metadata.

        Returns:
            A :class:`~infrastructure.ai.llm.schemas.SummaryResponse`
            containing the generated summary and provider metadata.

        Raises:
            LLMProviderNotReadyError: When the provider has not been configured.
            LLMProviderInputError: When the request cannot be converted into a
                valid provider prompt.
            LLMProviderResponseValidationError: When the provider returns data
                that cannot be parsed into the response schema.
            LLMProviderTimeoutError: When generation exceeds the configured deadline.
            LLMProviderError: When a provider-specific failure occurs.
        """
    
    @abstractmethod
    def complete(self, system_prompt: str, user_prompt: str) -> str:
        """Send a raw system/user prompt pair and return the model's text output.

        Unlike :meth:`summarize`, this method applies no additional prompt
        wrapping and returns the raw response text, allowing callers to handle
        parsing themselves.

        Args:
            system_prompt: Instruction context sent as the system role.
            user_prompt: The user-facing content of the request.

        Returns:
            Raw text string returned by the model.

        Raises:
            LLMProviderNotReadyError: When the provider has not been configured.
            LLMProviderTimeoutError: When generation exceeds the configured deadline.
            LLMProviderResponseValidationError: When the provider returns an empty
                or unparseable response.
            LLMProviderError: When a provider-specific failure occurs.
        """

    @abstractmethod
    def health_check(self) -> bool:
        """Report whether the provider is available and ready for use.

        Returns:
            ``True`` when the provider can accept summarization requests,
            otherwise ``False``.
        """
