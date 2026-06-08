"""Gemini provider implementation for LLM-based email summarization."""

from __future__ import annotations

import json
from json import JSONDecodeError
from typing import Any

import google.generativeai as genai

from core.config import Settings, get_settings
from infrastructure.ai.llm.base import BaseLLMProvider
from infrastructure.ai.llm.exceptions import (
    LLMProviderError,
    LLMProviderInputError,
    LLMProviderNotReadyError,
    LLMProviderResponseValidationError,
)
from infrastructure.ai.llm.schemas import SummaryRequest, SummaryResponse

GEMINI_PROVIDER_NAME = "gemini"


class GeminiProvider(BaseLLMProvider):
    """Summarize emails using the official Google Generative AI SDK."""

    def __init__(self, settings: Settings | None = None) -> None:
        """Initialise the provider from application settings."""
        self._settings = settings or get_settings()
        self._model = self._build_model()

    def summarize(self, request: SummaryRequest) -> SummaryResponse:
        """Generate a validated email summary for the supplied request."""
        self._assert_ready()

        try:
            response = self._model.generate_content(
                self._build_prompt(request),
                generation_config={
                    "temperature": self._settings.llm_temperature,
                    "max_output_tokens": self._settings.llm_max_tokens,
                    "response_mime_type": "application/json",
                },
            )
            payload = self._parse_json_payload(self._extract_text(response))
            return SummaryResponse(
                email_id=request.email_id,
                summary=self._extract_summary(payload),
                provider=GEMINI_PROVIDER_NAME,
                model=self._settings.gemini_model,
            )
        except LLMProviderError:
            raise
        except Exception as exc:  # pragma: no cover - defensive SDK wrapping
            raise LLMProviderError("Gemini summarization failed.", cause=exc) from exc

    def health_check(self) -> bool:
        """Report whether the Gemini provider is configured and reachable."""
        if not self._model:
            return False

        try:
            genai.list_models()
            return True
        except Exception:
            return False
    
    def complete(self, system_prompt: str, user_prompt: str) -> str:
        """Send a raw prompt pair to Gemini and return the model's text output.

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
            combined_prompt = f"{system_prompt}\n\n{user_prompt}"
            response = self._model.generate_content(
                combined_prompt,
                generation_config={
                    "temperature": self._settings.llm_temperature,
                    "max_output_tokens": self._settings.llm_max_tokens,
                },
            )
            return self._extract_text(response)
        except LLMProviderError:
            raise
        except Exception as exc:
            raise LLMProviderError(
                "Gemini complete() call failed.",
                cause=exc,
            ) from exc

    def _assert_ready(self) -> None:
        """Ensure the provider is configured before attempting a summary call."""
        if not self._model or not self._settings.gemini_api_key.strip():
            raise LLMProviderNotReadyError(self.__class__.__name__)

    def _build_model(self) -> genai.GenerativeModel | None:
        """Create a Gemini model instance when an API key is configured."""
        api_key = self._settings.gemini_api_key.strip()
        if not api_key:
            return None

        genai.configure(api_key=api_key)
        return genai.GenerativeModel(self._settings.gemini_model)

    def _build_prompt(self, request: SummaryRequest) -> str:
        """Construct the prompt containing email context and content."""
        if not request.subject and not request.body_text:
            raise LLMProviderInputError(
                "Summary requests must include either subject or body text."
            )

        return (
            "You are an email summarization assistant. "
            "Return only valid JSON with a single key named 'summary'. "
            "Keep the summary concise, factual, and free of markdown.\n\n"
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

    def _extract_text(self, response: Any) -> str:
        """Extract response text from the Gemini SDK response object."""
        text = getattr(response, "text", None)
        if isinstance(text, str) and text.strip():
            return text.strip()

        candidates = getattr(response, "candidates", None) or []
        text_parts: list[str] = []
        for candidate in candidates:
            content = getattr(candidate, "content", None)
            parts = getattr(content, "parts", None) or []
            for part in parts:
                part_text = getattr(part, "text", None)
                if isinstance(part_text, str) and part_text.strip():
                    text_parts.append(part_text.strip())

        combined = "".join(text_parts).strip()
        if not combined:
            raise LLMProviderResponseValidationError(
                GEMINI_PROVIDER_NAME,
                "The model response did not contain text content.",
            )
        return combined

    def _parse_json_payload(self, content: str) -> dict[str, Any]:
        """Parse the Gemini response text into a JSON payload."""
        try:
            payload = json.loads(content)
        except JSONDecodeError as exc:
            raise LLMProviderResponseValidationError(
                GEMINI_PROVIDER_NAME,
                "The model response was not valid JSON.",
                cause=exc,
            ) from exc

        if not isinstance(payload, dict):
            raise LLMProviderResponseValidationError(
                GEMINI_PROVIDER_NAME,
                "The model response JSON must be an object.",
            )
        return payload

    def _extract_summary(self, payload: dict[str, Any]) -> str:
        """Extract the summary text from a validated response payload."""
        summary = payload.get("summary")
        if not isinstance(summary, str) or not summary.strip():
            raise LLMProviderResponseValidationError(
                GEMINI_PROVIDER_NAME,
                "The model response must include a non-empty 'summary' field.",
            )
        return summary.strip()
