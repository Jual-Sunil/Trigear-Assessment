"""Claude provider implementation for LLM-based email summarization."""

from __future__ import annotations

import json
from json import JSONDecodeError
from typing import Any

from anthropic import Anthropic

from core.config import Settings, get_settings
from infrastructure.ai.llm.base import BaseLLMProvider
from infrastructure.ai.llm.exceptions import (
    LLMProviderError,
    LLMProviderInputError,
    LLMProviderNotReadyError,
    LLMProviderResponseValidationError,
)
from infrastructure.ai.llm.schemas import SummaryRequest, SummaryResponse

CLAUDE_PROVIDER_NAME = "claude"


class ClaudeProvider(BaseLLMProvider):
    """Summarize emails using the official Anthropic SDK."""

    def __init__(self, settings: Settings | None = None) -> None:
        """Initialise the provider from application settings."""
        self._settings = settings or get_settings()
        self._client = self._build_client()

    def summarize(self, request: SummaryRequest) -> SummaryResponse:
        """Generate a validated email summary for the supplied request."""
        self._assert_ready()

        try:
            message = self._client.messages.create(
                model=self._settings.anthropic_model,
                max_tokens=self._settings.llm_max_tokens,
                temperature=self._settings.llm_temperature,
                system=self._build_system_prompt(),
                messages=[
                    {
                        "role": "user",
                        "content": self._build_user_prompt(request),
                    }
                ],
            )
            content = self._extract_text_content(message.content)
            payload = self._parse_json_payload(content)
            return SummaryResponse(
                email_id=request.email_id,
                summary=self._extract_summary(payload),
                provider=CLAUDE_PROVIDER_NAME,
                model=self._settings.anthropic_model,
            )
        except LLMProviderError:
            raise
        except Exception as exc:  # pragma: no cover - defensive SDK wrapping
            raise LLMProviderError("Claude summarization failed.", cause=exc) from exc

    def health_check(self) -> bool:
        """Report whether the Claude provider is configured and reachable."""
        if not self._client:
            return False

        try:
            self._client.models.list()
            return True
        except Exception:
            return False
        
    def complete(self, system_prompt: str, user_prompt: str) -> str:
        """Send a raw prompt pair to Claude and return the model's text output.

        Args:
            system_prompt: Instruction context sent as the system role.
            user_prompt: The user-facing content of the request.

        Returns:
            Raw text string returned by the model.

        Raises:
            LLMProviderNotReadyError: When the API key is absent.
            LLMProviderResponseValidationError: When the response is empty or malformed.
            LLMProviderError: When any other unexpected error occurs.
        """
        self._assert_ready()

        try:
            message = self._client.messages.create(
                model=self._settings.anthropic_model,
                max_tokens=self._settings.llm_max_tokens,
                temperature=self._settings.llm_temperature,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
            return self._extract_text_content(message.content)
        except LLMProviderError:
            raise
        except Exception as exc:
            raise LLMProviderError(
                "Claude complete() call failed.",
                cause=exc,
            ) from exc

    def _assert_ready(self) -> None:
        """Ensure the provider is configured before attempting a summary call."""
        if not self._client or not self._settings.anthropic_api_key.strip():
            raise LLMProviderNotReadyError(self.__class__.__name__)

    def _build_client(self) -> Anthropic | None:
        """Create an Anthropic client when an API key is configured."""
        api_key = self._settings.anthropic_api_key.strip()
        if not api_key:
            return None
        return Anthropic(api_key=api_key)

    def _build_system_prompt(self) -> str:
        """Construct the system prompt used to request a JSON summary."""
        return (
            "You are an email summarization assistant. "
            "Return only valid JSON with a single key named 'summary'. "
            "Keep the summary concise, factual, and free of markdown."
        )

    def _build_user_prompt(self, request: SummaryRequest) -> str:
        """Construct the user prompt containing email context and content."""
        if not request.subject and not request.body_text:
            raise LLMProviderInputError(
                "Summary requests must include either subject or body text."
            )

        return (
            f"Email metadata:\n"
            f"- email_id: {request.email_id}\n"
            f"- sender_name: {request.sender_name or ''}\n"
            f"- sender_email: {request.sender_email}\n"
            f"- classification: {request.classification or ''}\n"
            f"- confidence_score: {request.confidence_score if request.confidence_score is not None else ''}\n"
            f"- priority_score: {request.priority_score if request.priority_score is not None else ''}\n"
            f"- is_action_required: {request.is_action_required if request.is_action_required is not None else ''}\n"
            f"- received_at: {request.received_at.isoformat()}\n\n"
            f"Subject:\n{request.subject or ''}\n\n"
            f"Body:\n{request.body_text or ''}\n"
        )

    def _extract_text_content(self, content: list[Any]) -> str:
        """Extract concatenated text blocks from the Claude response."""
        text_parts: list[str] = []
        for block in content:
            block_type = getattr(block, "type", None)
            block_text = getattr(block, "text", None)
            if block_type == "text" and isinstance(block_text, str):
                text_parts.append(block_text)

        text = "".join(text_parts).strip()
        if not text:
            raise LLMProviderResponseValidationError(
                CLAUDE_PROVIDER_NAME,
                "The model response did not contain text content.",
            )
        return text

    def _parse_json_payload(self, content: str) -> dict[str, Any]:
        """Parse the Claude response text into a JSON payload."""
        try:
            payload = json.loads(content)
        except JSONDecodeError as exc:
            raise LLMProviderResponseValidationError(
                CLAUDE_PROVIDER_NAME,
                "The model response was not valid JSON.",
                cause=exc,
            ) from exc

        if not isinstance(payload, dict):
            raise LLMProviderResponseValidationError(
                CLAUDE_PROVIDER_NAME,
                "The model response JSON must be an object.",
            )
        return payload

    def _extract_summary(self, payload: dict[str, Any]) -> str:
        """Extract the summary text from a validated response payload."""
        summary = payload.get("summary")
        if not isinstance(summary, str) or not summary.strip():
            raise LLMProviderResponseValidationError(
                CLAUDE_PROVIDER_NAME,
                "The model response must include a non-empty 'summary' field.",
            )
        return summary.strip()
