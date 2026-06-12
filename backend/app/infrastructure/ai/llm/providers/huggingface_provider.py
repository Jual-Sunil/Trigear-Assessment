"""HuggingFace Inference API provider for LLM-based email summarization.

Exposes models hosted on HuggingFace's Inference API through their
OpenAI-compatible chat completions endpoint using a plain synchronous
``httpx.Client``.  The implementation mirrors :class:`OpenRouterProvider`
exactly in structure so that it can be swapped in transparently via the
factory.
"""

from __future__ import annotations

import json
import logging
from json import JSONDecodeError
from typing import Any

import httpx

from core.config import Settings, get_settings
from infrastructure.ai.llm.base import BaseLLMProvider
from infrastructure.ai.llm.exceptions import (
    LLMProviderError,
    LLMProviderInputError,
    LLMProviderNotReadyError,
    LLMProviderResponseValidationError,
    LLMProviderTimeoutError,
)
from infrastructure.ai.llm.schemas import SummaryRequest, SummaryResponse

logger = logging.getLogger(__name__)

HUGGINGFACE_PROVIDER_NAME = "huggingface"

_BASE_URL = "https://router.huggingface.co/v1"
_CHAT_ENDPOINT = "/chat/completions"

# HuggingFace Inference API can be slower for large models on shared
# infrastructure — keep the timeout generous.
_DEFAULT_TIMEOUT_SECONDS = 120.0


class HuggingFaceProvider(BaseLLMProvider):
    """Summarize emails by calling HuggingFace's OpenAI-compatible chat API.

    The provider uses a synchronous ``httpx.Client`` that is created once and
    reused across calls.  This matches the synchronous contract of
    :class:`~infrastructure.ai.llm.base.BaseLLMProvider` and is consistent
    with all other providers in this codebase.

    Supported failure modes
    -----------------------
    * ``LLMProviderNotReadyError``  – API key missing or client not built.
    * ``LLMProviderInputError``     – Request carries no usable text.
    * ``LLMProviderTimeoutError``   – HTTP request exceeded the timeout.
    * ``LLMProviderResponseValidationError`` – Non-200 status, empty body,
      malformed JSON, or missing ``summary`` field.
    * ``LLMProviderError``          – Any other unexpected failure.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        """Initialise the provider from application settings.

        Args:
            settings: Optional settings instance for dependency injection.
                When omitted the cached application settings are loaded.
        """
        self._settings = settings or get_settings()
        self._client: httpx.Client | None = self._build_client()

    # ------------------------------------------------------------------
    # BaseLLMProvider contract
    # ------------------------------------------------------------------

    def summarize(self, request: SummaryRequest) -> SummaryResponse:
        """Generate a validated email summary via the HuggingFace Inference API.

        Args:
            request: Validated summarization input DTO.

        Returns:
            A :class:`~infrastructure.ai.llm.schemas.SummaryResponse` with the
            generated summary and provider metadata.

        Raises:
            LLMProviderNotReadyError: When the API key is absent or the client
                could not be constructed.
            LLMProviderInputError: When ``request`` contains no usable text.
            LLMProviderTimeoutError: When the HTTP request times out.
            LLMProviderResponseValidationError: When the API returns a non-200
                status, an empty response body, malformed JSON, or a payload
                that does not contain a non-empty ``summary`` field.
            LLMProviderError: When any other unexpected error occurs.
        """
        self._assert_ready()

        prompt = self._build_prompt(request)
        logger.debug(
            "huggingface_request_start",
            extra={
                "provider": HUGGINGFACE_PROVIDER_NAME,
                "model": self._settings.huggingface_model,
                "email_id": str(request.email_id),
            },
        )

        try:
            raw_response = self._call_api(prompt)
            text = self._extract_text(raw_response)
            summary = text.strip()

            if not summary:
                raise LLMProviderResponseValidationError(
                    HUGGINGFACE_PROVIDER_NAME,
                    "Model returned empty summary.",
                )

            logger.info(
                "huggingface_request_success",
                extra={
                    "provider": HUGGINGFACE_PROVIDER_NAME,
                    "model": self._settings.huggingface_model,
                    "email_id": str(request.email_id),
                },
            )

            return SummaryResponse(
                email_id=request.email_id,
                summary=summary,
                provider=HUGGINGFACE_PROVIDER_NAME,
                model=self._settings.huggingface_model,
            )

        except LLMProviderError:
            raise
        except Exception as exc:
            logger.error(
                "huggingface_request_unexpected_error",
                extra={
                    "provider": HUGGINGFACE_PROVIDER_NAME,
                    "email_id": str(request.email_id),
                    "error": str(exc),
                },
                exc_info=True,
            )
            raise LLMProviderError(
                "HuggingFace summarization failed due to an unexpected error.",
                cause=exc,
            ) from exc

    def health_check(self) -> bool:
        """Report whether the HuggingFace provider is reachable and configured.

        Performs a lightweight ``GET /models`` request.  Returns ``False``
        rather than raising so that the health-check caller can decide how to
        handle an unavailable provider.

        Returns:
            ``True`` when the provider is available, ``False`` otherwise.
        """
        if self._client is None:
            logger.warning(
                "huggingface_health_check_skipped_no_client",
                extra={"provider": HUGGINGFACE_PROVIDER_NAME},
            )
            return False

        try:
            response = self._client.get(
                f"{_BASE_URL}/models",
                timeout=10.0,
            )
            is_healthy = response.status_code == 200
            logger.debug(
                "huggingface_health_check_result",
                extra={
                    "provider": HUGGINGFACE_PROVIDER_NAME,
                    "status_code": response.status_code,
                    "healthy": is_healthy,
                },
            )
            return is_healthy
        except Exception as exc:
            logger.warning(
                "huggingface_health_check_failed",
                extra={
                    "provider": HUGGINGFACE_PROVIDER_NAME,
                    "error": str(exc),
                },
            )
            return False

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        """Send a raw prompt pair to HuggingFace and return the model's text output.

        Args:
            system_prompt: Instruction context sent as the system role.
            user_prompt: The user-facing content of the request.

        Returns:
            Raw text string returned by the model.

        Raises:
            LLMProviderNotReadyError: When the API key is absent.
            LLMProviderTimeoutError: When the HTTP request times out.
            LLMProviderResponseValidationError: When the response is empty or malformed.
            LLMProviderError: When any other unexpected error occurs.
        """
        self._assert_ready()
        assert self._client is not None

        payload: dict[str, Any] = {
            "model": self._settings.huggingface_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": self._settings.llm_temperature,
            "max_tokens": self._settings.llm_max_tokens,
        }

        try:
            response = self._client.post(
                f"{_BASE_URL}{_CHAT_ENDPOINT}",
                content=json.dumps(payload),
            )
        except httpx.TimeoutException as exc:
            raise LLMProviderTimeoutError(
                HUGGINGFACE_PROVIDER_NAME,
                _DEFAULT_TIMEOUT_SECONDS,
            ) from exc
        except httpx.RequestError as exc:
            raise LLMProviderError(
                f"HuggingFace HTTP request failed: {exc}",
                cause=exc,
            ) from exc

        if response.status_code >= 400:
            raise LLMProviderResponseValidationError(
                HUGGINGFACE_PROVIDER_NAME,
                f"API returned HTTP {response.status_code}: {response.text[:200]}",
            )

        try:
            raw = response.json()
        except JSONDecodeError as exc:
            raise LLMProviderResponseValidationError(
                HUGGINGFACE_PROVIDER_NAME,
                "The API response body was not valid JSON.",
                cause=exc,
            ) from exc

        text = self._extract_text(raw)
        if not text:
            raise LLMProviderResponseValidationError(
                HUGGINGFACE_PROVIDER_NAME,
                "Model returned empty content for complete() call.",
            )
        return text

    # ------------------------------------------------------------------
    # Initialisation helpers
    # ------------------------------------------------------------------

    def _assert_ready(self) -> None:
        """Raise :class:`LLMProviderNotReadyError` when the client is absent.

        Raises:
            LLMProviderNotReadyError: When ``_client`` is ``None``, which
                indicates the API key was not configured at startup.
        """
        if self._client is None or not self._settings.huggingface_api_key.strip():
            raise LLMProviderNotReadyError(self.__class__.__name__)

    def _build_client(self) -> httpx.Client | None:
        """Create a persistent ``httpx.Client`` when an API key is present.

        The client is pre-configured with the Authorization header and a
        default timeout so individual call sites do not need to repeat this
        boilerplate.

        Returns:
            A configured :class:`httpx.Client`, or ``None`` when the API key
            is absent or blank.
        """
        api_key = self._settings.huggingface_api_key.strip()
        if not api_key:
            logger.warning(
                "huggingface_client_not_built_missing_api_key",
                extra={"provider": HUGGINGFACE_PROVIDER_NAME},
            )
            return None

        return httpx.Client(
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            timeout=_DEFAULT_TIMEOUT_SECONDS,
        )

    # ------------------------------------------------------------------
    # Prompt construction
    # ------------------------------------------------------------------

    def _build_prompt(self, request: SummaryRequest) -> str:
        """Construct the full prompt that will be sent as the user message.

        Args:
            request: Validated summarization input DTO.

        Returns:
            A formatted string ready to be inserted into the ``user`` role.

        Raises:
            LLMProviderInputError: When both ``subject`` and ``body_text``
                are absent or blank.
        """
        if not request.subject and not request.body_text:
            raise LLMProviderInputError(
                "Summary requests must include either subject or body text."
            )

        return (
            "You are an email summarization assistant. "
            "Return only a concise email summary."
            "Do not use markdown."
            "Do not return JSON. "
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

    # ------------------------------------------------------------------
    # HTTP call
    # ------------------------------------------------------------------

    def _call_api(self, prompt: str) -> dict[str, Any]:
        """Send a chat-completion request to HuggingFace and return the raw JSON.

        Args:
            prompt: The fully assembled user-role prompt text.

        Returns:
            The parsed JSON response body as a plain ``dict``.

        Raises:
            LLMProviderTimeoutError: When the request exceeds the configured
                timeout.
            LLMProviderResponseValidationError: When the server returns a
                non-200 HTTP status or a body that is not valid JSON.
            LLMProviderError: When any other transport-level error occurs.
        """
        assert self._client is not None  # guarded by _assert_ready()

        payload: dict[str, Any] = {
            "model": self._settings.huggingface_model,
            "messages": [
                {"role": "user", "content": prompt},
            ],
            "temperature": self._settings.llm_temperature,
            "max_tokens": self._settings.llm_max_tokens,
        }

        try:
            response = self._client.post(
                f"{_BASE_URL}{_CHAT_ENDPOINT}",
                content=json.dumps(payload),
            )
        except httpx.TimeoutException as exc:
            logger.error(
                "huggingface_request_timeout",
                extra={
                    "provider": HUGGINGFACE_PROVIDER_NAME,
                    "timeout_seconds": _DEFAULT_TIMEOUT_SECONDS,
                    "error": str(exc),
                },
            )
            raise LLMProviderTimeoutError(
                HUGGINGFACE_PROVIDER_NAME,
                _DEFAULT_TIMEOUT_SECONDS,
            ) from exc
        except httpx.RequestError as exc:
            logger.error(
                "huggingface_request_transport_error",
                extra={
                    "provider": HUGGINGFACE_PROVIDER_NAME,
                    "error": str(exc),
                },
            )
            raise LLMProviderError(
                f"HuggingFace HTTP request failed: {exc}",
                cause=exc,
            ) from exc

        logger.debug(
            "huggingface_http_response",
            extra={
                "provider": HUGGINGFACE_PROVIDER_NAME,
                "status_code": response.status_code,
            },
        )

        if response.status_code == 429:
            logger.warning(
                "huggingface_rate_limit_hit",
                extra={
                    "provider": HUGGINGFACE_PROVIDER_NAME,
                    "status_code": response.status_code,
                    "response_body": response.text[:500],
                },
            )
            raise LLMProviderResponseValidationError(
                HUGGINGFACE_PROVIDER_NAME,
                f"Rate limit exceeded (HTTP 429): {response.text[:200]}",
            )

        if response.status_code >= 400:
            logger.error(
                "huggingface_http_error",
                extra={
                    "provider": HUGGINGFACE_PROVIDER_NAME,
                    "status_code": response.status_code,
                    "response_body": response.text[:500],
                },
            )
            raise LLMProviderResponseValidationError(
                HUGGINGFACE_PROVIDER_NAME,
                f"API returned HTTP {response.status_code}: {response.text[:200]}",
            )

        try:
            return response.json()
        except JSONDecodeError as exc:
            logger.error(
                "huggingface_response_not_json",
                extra={
                    "provider": HUGGINGFACE_PROVIDER_NAME,
                    "response_body": response.text[:500],
                    "error": str(exc),
                },
            )
            raise LLMProviderResponseValidationError(
                HUGGINGFACE_PROVIDER_NAME,
                "The API response body was not valid JSON.",
                cause=exc,
            ) from exc

    # ------------------------------------------------------------------
    # Response extraction
    # ------------------------------------------------------------------

    def _extract_text(self, response: dict[str, Any]) -> str:
        """Pull the assistant message content from the OpenAI-compatible envelope.

        HuggingFace's Inference API follows the OpenAI chat-completion schema::

            {
              "choices": [
                {
                  "message": {
                    "role": "assistant",
                    "content": "<text>"
                  }
                }
              ]
            }

        Args:
            response: Parsed JSON response body from the API.

        Returns:
            The stripped assistant message content string.

        Raises:
            LLMProviderResponseValidationError: When the expected structure is
                absent or the content field is empty.
        """
        choices = response.get("choices")
        if not isinstance(choices, list) or not choices:
            logger.error(
                "huggingface_response_missing_choices",
                extra={
                    "provider": HUGGINGFACE_PROVIDER_NAME,
                    "response_keys": list(response.keys()),
                },
            )
            raise LLMProviderResponseValidationError(
                HUGGINGFACE_PROVIDER_NAME,
                "The API response did not contain a 'choices' array.",
            )

        first_choice = choices[0]
        message = first_choice.get("message") if isinstance(first_choice, dict) else None
        content = message.get("content") if isinstance(message, dict) else None

        if not isinstance(content, str) or not content.strip():
            logger.error(
                "huggingface_response_empty_content",
                extra={
                    "provider": HUGGINGFACE_PROVIDER_NAME,
                    "first_choice": str(first_choice)[:200],
                },
            )
            raise LLMProviderResponseValidationError(
                HUGGINGFACE_PROVIDER_NAME,
                "The model response did not contain text content.",
            )

        return content.strip()

    def _parse_json_payload(self, content: str) -> dict[str, Any]:
        """Decode the model's text output as a JSON object.

        Args:
            content: Raw text content returned by the model.

        Returns:
            The decoded JSON object as a plain ``dict``.

        Raises:
            LLMProviderResponseValidationError: When the text cannot be decoded
                as JSON or the root value is not an object.
        """
        cleaned = content.strip()
        if cleaned.startswith("```"):
            lines = cleaned.splitlines()
            inner_lines = [
                line for line in lines[1:]
                if not line.strip().startswith("```")
            ]
            cleaned = "\n".join(inner_lines).strip()

        try:
            payload = json.loads(cleaned)
        except JSONDecodeError as exc:
            logger.error(
                "huggingface_response_json_parse_failure",
                extra={
                    "provider": HUGGINGFACE_PROVIDER_NAME,
                    "raw_content": content[:300],
                    "error": str(exc),
                },
            )
            raise LLMProviderResponseValidationError(
                HUGGINGFACE_PROVIDER_NAME,
                "The model response was not valid JSON.",
                cause=exc,
            ) from exc

        if not isinstance(payload, dict):
            logger.error(
                "huggingface_response_json_not_object",
                extra={
                    "provider": HUGGINGFACE_PROVIDER_NAME,
                    "type": type(payload).__name__,
                },
            )
            raise LLMProviderResponseValidationError(
                HUGGINGFACE_PROVIDER_NAME,
                "The model response JSON must be an object.",
            )

        return payload

    def _extract_summary(self, payload: dict[str, Any]) -> str:
        """Pull and validate the ``summary`` field from the decoded payload.

        Args:
            payload: Decoded JSON object from the model response.

        Returns:
            The stripped summary string.

        Raises:
            LLMProviderResponseValidationError: When ``summary`` is absent,
                not a string, or contains only whitespace.
        """
        summary = payload.get("summary")
        if not isinstance(summary, str) or not summary.strip():
            logger.error(
                "huggingface_response_missing_summary",
                extra={
                    "provider": HUGGINGFACE_PROVIDER_NAME,
                    "payload_keys": list(payload.keys()),
                },
            )
            raise LLMProviderResponseValidationError(
                HUGGINGFACE_PROVIDER_NAME,
                "The model response must include a non-empty 'summary' field.",
            )
        return summary.strip()
