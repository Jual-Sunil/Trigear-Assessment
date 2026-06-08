"""Factory for creating configured LLM provider instances."""

from __future__ import annotations

from core.config import Settings, get_settings
from infrastructure.ai.llm.base import BaseLLMProvider
from infrastructure.ai.llm.exceptions import LLMProviderError
from infrastructure.ai.llm.providers.claude_provider import ClaudeProvider
from infrastructure.ai.llm.providers.gemini_provider import GeminiProvider
from infrastructure.ai.llm.providers.openai_provider import OpenAIProvider
from infrastructure.ai.llm.providers.openrouter_provider import OpenRouterProvider

PROVIDER_CLAUDE = "claude"
PROVIDER_OPENAI = "openai"
PROVIDER_GEMINI = "gemini"
PROVIDER_OPENROUTER = "openrouter"


class LLMProviderFactory:
    """Create a concrete LLM provider based on application settings."""

    def __init__(self, settings: Settings | None = None) -> None:
        """Initialise the factory with application settings.

        Args:
            settings: Optional settings instance for dependency injection. When
                omitted, the cached application settings are loaded.
        """
        self._settings = settings or get_settings()

    def create_provider(self) -> BaseLLMProvider:
        """Create the configured LLM provider.

        Returns:
            A concrete :class:`~infrastructure.ai.llm.base.BaseLLMProvider`
            implementation selected from application settings.

        Raises:
            LLMProviderError: When the configured provider name is unsupported.
        """
        provider_name = self._settings.llm_provider

        if provider_name == PROVIDER_OPENAI:
            return OpenAIProvider(self._settings)
        if provider_name == PROVIDER_CLAUDE:
            return ClaudeProvider(self._settings)
        if provider_name == PROVIDER_GEMINI:
            return GeminiProvider(self._settings)
        if provider_name == PROVIDER_OPENROUTER:
            return OpenRouterProvider(self._settings)

        raise LLMProviderError(
            f"Unsupported LLM provider '{provider_name}'. "
            f"Supported providers are: {PROVIDER_OPENAI}, {PROVIDER_CLAUDE}, {PROVIDER_GEMINI}, {PROVIDER_OPENROUTER}."
        )
