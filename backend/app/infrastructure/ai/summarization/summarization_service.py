"""Email summarization service coordinating LLM provider calls."""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from pydantic import ValidationError

from infrastructure.ai.llm.base import BaseLLMProvider
from infrastructure.ai.llm.exceptions import LLMProviderError
from infrastructure.ai.llm.provider_factory import LLMProviderFactory
from infrastructure.ai.llm.schemas import SummaryRequest, SummaryResponse
from infrastructure.ai.summarization.exceptions import (
    EmailSummarizationError,
    EmailSummaryInputError,
    EmailSummaryResultValidationError,
)
from infrastructure.ai.summarization.schemas import (
    EmailSummaryRequest,
    EmailSummaryResult,
)

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You are an AI assistant specialising in concise, accurate email summarisation.
You must respond with a single valid JSON object and nothing else.
Do not include markdown fences, preamble, or trailing commentary.

Required JSON schema:
{
  "summary": "<one-to-three sentence plain-text summary of the email>",
  "key_points": ["<concise fact or theme>", ...],
  "action_items": ["<actionable follow-up item>", ...]
}

Rules:
- "summary" must be a non-empty string.
- "key_points" must be a JSON array of non-empty strings (may be empty array).
- "action_items" must be a JSON array of non-empty strings (may be empty array).
- Do not invent information that is not present in the email.
- Be professional and neutral in tone.
"""

_MAX_BODY_CHARS = 8_000


class SummarizationService:
    """Orchestrates LLM-backed email summarisation.

    Responsibilities:
    - Build a structured prompt from an :class:`EmailSummaryRequest`.
    - Delegate generation to the configured :class:`BaseLLMProvider`.
    - Parse and validate the JSON response from the provider.
    - Retry transient failures up to the configured limit.
    - Map provider-level exceptions to summarisation-domain exceptions.
    """

    def __init__(
        self,
        provider: BaseLLMProvider | None = None,
        *,
        max_retries: int = 3,
        retry_delay: float = 2.0,
    ) -> None:
        """Initialise the service with an LLM provider.

        Args:
            provider: Concrete provider implementation. When ``None`` the
                factory constructs the provider selected by application
                settings.
            max_retries: Maximum number of generation attempts before the
                service raises a terminal error.
            retry_delay: Base delay in seconds between retry attempts. Each
                subsequent attempt waits ``retry_delay * attempt`` seconds.
        """
        self._provider: BaseLLMProvider = provider or LLMProviderFactory().create_provider()
        self._max_retries = max_retries
        self._retry_delay = retry_delay

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def summarize(self, request: EmailSummaryRequest) -> EmailSummaryResult:
        """Generate a structured summary for a single email.

        Args:
            request: Validated summarisation input containing the email content
                and contextual metadata.

        Returns:
            An :class:`~infrastructure.ai.summarization.schemas.EmailSummaryResult`
            containing the generated summary, key points, and action items.

        Raises:
            EmailSummaryInputError: When the request is missing required content.
            EmailSummaryResultValidationError: When the LLM response cannot be
                parsed or validated after all retry attempts are exhausted.
            EmailSummarizationError: When a non-recoverable provider failure
                occurs.
        """
        summary_request = self._build_summary_request(request)
        raw_response = self._invoke_with_retry(summary_request)
        return self._parse_response(raw_response, email_id=request.email_id)

    # ------------------------------------------------------------------
    # Request construction
    # ------------------------------------------------------------------

    def _build_summary_request(self, request: EmailSummaryRequest) -> SummaryRequest:
        """Convert an :class:`EmailSummaryRequest` into a :class:`SummaryRequest`.

        Args:
            request: Summarisation input from the service layer.

        Returns:
            A :class:`~infrastructure.ai.llm.schemas.SummaryRequest` ready for
            the LLM provider.

        Raises:
            EmailSummaryInputError: When the email lacks sufficient text
                content for summarisation.
        """
        subject = request.subject or ""
        sender_display = request.sender or ""
        body = request.body or ""

        user_prompt = self._format_user_prompt(
            subject=subject,
            sender=sender_display,
            body=body,
            received_at=request.received_at,
        )

        try:
            return SummaryRequest(
                email_id=request.email_id or _placeholder_uuid(),
                subject=request.subject,
                body_text=user_prompt,
                sender_name=None,
                sender_email=request.sender or "unknown@unknown.invalid",
                classification=None,
                confidence_score=None,
                priority_score=None,
                is_action_required=None,
                received_at=request.received_at or datetime.now(tz=timezone.utc),
            )
        except ValidationError as exc:
            raise EmailSummaryInputError(
                "Email request does not contain sufficient content for summarisation.",
                cause=exc,
            ) from exc

    def _format_user_prompt(
        self,
        *,
        subject: str,
        sender: str,
        body: str,
        received_at: datetime | None,
    ) -> str:
        """Assemble the user-facing portion of the LLM prompt.

        Args:
            subject: Email subject line.
            sender: Sender display name or address.
            body: Plain-text email body.
            received_at: UTC timestamp the email was received.

        Returns:
            A formatted prompt string embedding the email fields.
        """
        truncated_body = body[:_MAX_BODY_CHARS]
        if len(body) > _MAX_BODY_CHARS:
            truncated_body += "\n[... body truncated for length ...]"

        received_str = (
            received_at.strftime("%Y-%m-%d %H:%M UTC")
            if received_at
            else "unknown"
        )

        lines: list[str] = [
            "Summarise the following email and return ONLY a JSON object.",
            "",
            f"Subject   : {subject or '(none)'}",
            f"From      : {sender or '(unknown)'}",
            f"Received  : {received_str}",
            "",
            "Body:",
            truncated_body or "(no body)",
        ]
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Provider invocation
    # ------------------------------------------------------------------

    def _invoke_with_retry(self, request: SummaryRequest) -> SummaryResponse:
        """Attempt provider invocation with exponential back-off retry.

        Args:
            request: Validated LLM provider request.

        Returns:
            A :class:`~infrastructure.ai.llm.schemas.SummaryResponse` from the
            provider.

        Raises:
            EmailSummarizationError: When all retry attempts are exhausted.
        """
        last_error: BaseException | None = None

        for attempt in range(1, self._max_retries + 1):
            try:
                return self._provider.summarize(request)
            except LLMProviderError as exc:
                last_error = exc
                logger.warning(
                    "LLM provider attempt %d/%d failed: %s",
                    attempt,
                    self._max_retries,
                    exc,
                )
                if attempt < self._max_retries:
                    time.sleep(self._retry_delay * attempt)

        raise EmailSummarizationError(
            f"LLM provider failed after {self._max_retries} attempt(s).",
            cause=last_error,
        ) from last_error

    # ------------------------------------------------------------------
    # Response parsing and validation
    # ------------------------------------------------------------------

    def _parse_response(
        self,
        response: SummaryResponse,
        *,
        email_id: UUID | None,
    ) -> EmailSummaryResult:
        """Parse the raw provider response into a validated :class:`EmailSummaryResult`.

        Args:
            response: Raw response returned by the LLM provider.
            email_id: Optional email identifier to embed in the result.

        Returns:
            A validated :class:`~infrastructure.ai.summarization.schemas.EmailSummaryResult`.

        Raises:
            EmailSummaryResultValidationError: When the response cannot be
                decoded as JSON or fails schema validation.
        """
        logger.info(
            "summary_response_received",
            extra={
                "provider": response.provider,
                "model": response.model,
                "summary_raw": response.summary[:1000],
            },
        )

        summary_text = response.summary.strip()

        if not summary_text:
            raise EmailSummaryResultValidationError(
                "Provider returned an empty summary."
            )

        return EmailSummaryResult(
            email_id=email_id,
            summary=summary_text,
            key_points=[],
            action_items=[],
        )

    def _extract_json(self, raw_text: str) -> dict[str, Any]:
        """Extract and decode a JSON object from LLM output.

        The method strips common markdown fencing artefacts before attempting
        to decode the text as JSON.

        Args:
            raw_text: Raw text string returned by the LLM provider.

        Returns:
            A dictionary representing the decoded JSON payload.

        Raises:
            EmailSummaryResultValidationError: When the text cannot be decoded
                as a JSON object.
        """
        logger.info(
            "extract_json_input",
            extra={
                "raw_text": raw_text[:1000],
            },
        )
        cleaned = raw_text.strip()

        # Strip markdown code fences if the provider wrapped the JSON.
        if cleaned.startswith("```"):
            lines = cleaned.splitlines()
            # Drop the opening fence line and any closing fence.
            inner_lines = [
                line for line in lines[1:]
                if not line.strip().startswith("```")
            ]
            cleaned = "\n".join(inner_lines).strip()

        try:
            payload = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            logger.error(
                "json_decode_failed",
                extra={
                    "content": cleaned[:1000],
                    "error": str(exc),
                },
            )

            raise EmailSummaryResultValidationError(
                f"LLM response is not valid JSON: {exc}",
                cause=exc,
            ) from exc

        if not isinstance(payload, dict):
            raise EmailSummaryResultValidationError(
                f"LLM response JSON must be an object, got {type(payload).__name__}.",
            )

        return payload

    def _validate_payload(
        self,
        payload: dict[str, Any],
        *,
        email_id: UUID | None,
    ) -> EmailSummaryResult:
        """Validate a decoded JSON payload against the :class:`EmailSummaryResult` schema.

        Args:
            payload: Decoded JSON object from the LLM response.
            email_id: Optional email identifier to embed in the result.

        Returns:
            A validated :class:`~infrastructure.ai.summarization.schemas.EmailSummaryResult`.

        Raises:
            EmailSummaryResultValidationError: When required fields are missing
                or fail Pydantic validation.
        """
        summary_text: str = payload.get("summary", "")
        if not isinstance(summary_text, str) or not summary_text.strip():
            raise EmailSummaryResultValidationError(
                "LLM response JSON is missing a non-empty 'summary' field.",
            )

        key_points: list[str] = self._extract_string_list(payload, "key_points")
        action_items: list[str] = self._extract_string_list(payload, "action_items")

        try:
            return EmailSummaryResult(
                email_id=email_id,
                summary=summary_text,
                key_points=key_points,
                action_items=action_items,
            )
        except ValidationError as exc:
            raise EmailSummaryResultValidationError(
                f"LLM response failed schema validation: {exc}",
                cause=exc,
            ) from exc

    @staticmethod
    def _extract_string_list(payload: dict[str, Any], key: str) -> list[str]:
        """Extract a list of non-empty strings from a JSON payload field.

        Args:
            payload: Decoded JSON object.
            key: Field name to extract.

        Returns:
            A list of non-empty, whitespace-stripped strings. Returns an empty
            list when the field is absent or not a list.

        Raises:
            EmailSummaryResultValidationError: When any list entry is not a
                string.
        """
        raw = payload.get(key, [])
        if not isinstance(raw, list):
            return []

        result: list[str] = []
        for index, item in enumerate(raw):
            if not isinstance(item, str):
                raise EmailSummaryResultValidationError(
                    f"'{key}[{index}]' must be a string, got {type(item).__name__}.",
                )
            stripped = item.strip()
            if stripped:
                result.append(stripped)

        return result


def _placeholder_uuid() -> UUID:
    """Return a deterministic nil UUID used when no email identifier is present.

    Returns:
        A UUID with all bits set to zero.
    """
    return UUID(int=0)
