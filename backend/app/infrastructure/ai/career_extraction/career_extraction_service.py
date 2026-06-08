"""Career extraction service.

Implements the orchestration for extracting job opportunities and
interview details from email content using an LLM provider.

This module does not access the database or repositories and does not
create any records.
"""

from __future__ import annotations

import json
import time
from json import JSONDecodeError
from typing import Any

from core.config import Settings
from infrastructure.ai.career_extraction.exceptions import (
    CareerExtractionFailureError,
    CareerExtractionMalformedResponseError,
    CareerExtractionValidationError,
)
from infrastructure.ai.career_extraction.prompts import (
    build_interview_extraction_prompt,
    build_job_opportunity_extraction_prompt,
)
from infrastructure.ai.career_extraction.schemas import (
    CareerExtractionRequest,
    CareerExtractionResult,
)
from infrastructure.ai.llm.base import BaseLLMProvider
from infrastructure.ai.llm.provider_factory import LLMProviderFactory


class CareerExtractionService:
    """Orchestrate career extraction using the configured LLM provider."""

    def __init__(
        self,
        *,
        provider: BaseLLMProvider | None = None,
        provider_factory: LLMProviderFactory | None = None,
        settings: Settings | None = None,
        max_retries: int | None = None,
        retry_delay_seconds: float | None = None,
    ) -> None:
        """Initialise the service.

        Args:
            provider: Optional injected LLM provider.
            provider_factory: Optional injected provider factory.
            settings: Optional app settings.
            max_retries: Optional override for retry count.
            retry_delay_seconds: Optional override for delay between retries.
        """
        self._settings = settings
        self._provider_factory = provider_factory or LLMProviderFactory(settings)
        self._provider = provider
        self._max_retries = max_retries
        self._retry_delay_seconds = retry_delay_seconds

    def extract_career(self, request: CareerExtractionRequest) -> CareerExtractionResult:
        """Extract job opportunities and interviews from the provided email.

        Args:
            request: Career extraction request DTO.

        Returns:
            Validated :class:`CareerExtractionResult`.

        Raises:
            CareerExtractionFailureError: When extraction fails after retries.
            CareerExtractionMalformedResponseError: When provider response cannot be parsed.
            CareerExtractionValidationError: When DTO validation fails.
        """
        provider = self._provider or self._provider_factory.create_provider()

        max_retries = self._max_retries
        retry_delay_seconds = self._retry_delay_seconds
        if max_retries is None:
            max_retries = (
                self._settings.llm_max_retries if self._settings is not None else 3
            )
        if retry_delay_seconds is None:
            retry_delay_seconds = (
                self._settings.llm_retry_delay if self._settings is not None else 2.0
            )

        last_exc: BaseException | None = None
        for attempt in range(max_retries):
            try:
                return self._extract_once(provider=provider, request=request)
            except (
                CareerExtractionMalformedResponseError,
                CareerExtractionValidationError,
            ) as exc:
                last_exc = exc
                if attempt >= max_retries - 1:
                    raise
            except Exception as exc:
                last_exc = exc
                if attempt >= max_retries - 1:
                    raise CareerExtractionFailureError(
                        "Career extraction failed after exhausting retries.",
                        cause=exc,
                    ) from exc

            time.sleep(retry_delay_seconds)

        assert last_exc is not None
        raise CareerExtractionFailureError(
            "Career extraction failed.",
            cause=last_exc,
        )

    def _extract_once(
        self,
        *,
        provider: BaseLLMProvider,
        request: CareerExtractionRequest,
    ) -> CareerExtractionResult:
        """Execute a single extraction attempt deterministically.

        Args:
            provider: Configured LLM provider instance.
            request: Career extraction request DTO.

        Returns:
            Validated :class:`CareerExtractionResult`.
        """
        job_system, job_user = build_job_opportunity_extraction_prompt(
            subject=request.subject,
            body=request.body,
        )
        interview_system, interview_user = build_interview_extraction_prompt(
            subject=request.subject,
            body=request.body,
        )

        job_payload_text = self._call_provider(
            provider, system_prompt=job_system, user_prompt=job_user
        )
        job_payload = self._parse_json_object(job_payload_text)

        interview_payload_text = self._call_provider(
            provider, system_prompt=interview_system, user_prompt=interview_user
        )
        interview_payload = self._parse_json_object(interview_payload_text)

        merged_payload: dict[str, Any] = {}

        merged_payload["job_opportunities"] = job_payload.get("job_opportunities", [])
        merged_payload["interviews"] = interview_payload.get("interviews", [])

        job_conf = job_payload.get("extraction_confidence", 0.0)
        interview_conf = interview_payload.get("extraction_confidence", 0.0)
        merged_payload["extraction_confidence"] = self._merge_confidence(
            job_conf=float(job_conf) if job_conf is not None else 0.0,
            interview_conf=float(interview_conf) if interview_conf is not None else 0.0,
        )

        try:
            return CareerExtractionResult.model_validate(merged_payload)
        except Exception as exc:
            import logging
            logging.getLogger(__name__).warning(
                "career_extraction_schema_validation_failed",
                extra={
                    "validation_error": str(exc),
                    "merged_payload_keys": list(merged_payload.keys()),
                    "job_count": len(merged_payload.get("job_opportunities", [])),
                    "interview_count": len(merged_payload.get("interviews", [])),
                },
            )
            raise CareerExtractionValidationError(
                "Career extraction result failed validation.",
                cause=exc,
            ) from exc

    def _merge_confidence(self, *, job_conf: float, interview_conf: float) -> float:
        """Merge per-branch confidence as the mean of two values.

        Args:
            job_conf: Confidence score from the job extraction branch.
            interview_conf: Confidence score from the interview extraction branch.

        Returns:
            Mean of the two confidence values in [0.0, 1.0].
        """
        return (job_conf + interview_conf) / 2.0

    def _parse_json_object(self, text: str) -> dict[str, Any]:
        """Parse a JSON object from provider output, stripping markdown fences if present.

        Args:
            text: Raw model output text.

        Returns:
            Parsed JSON object as a plain dict.

        Raises:
            CareerExtractionMalformedResponseError: When the text cannot be
                decoded as a JSON object.
        """
        cleaned = text.strip()
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
            raise CareerExtractionMalformedResponseError(
                "Career extraction response was not valid JSON.",
                cause=exc,
            ) from exc

        if not isinstance(payload, dict):
            raise CareerExtractionMalformedResponseError(
                "Career extraction response JSON must be an object."
            )
        return payload

    def _call_provider(
        self,
        provider: BaseLLMProvider,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        """Call the LLM provider via the standard complete() interface and return raw text.

        Uses :meth:`~infrastructure.ai.llm.base.BaseLLMProvider.complete` so
        that the career extraction service honours the same provider contract
        as task extraction, avoiding any dependency on summarization-specific
        DTOs.

        Args:
            provider: Configured LLM provider instance.
            system_prompt: Instruction context for the system role.
            user_prompt: User-facing extraction request.

        Returns:
            Raw text response from the model (expected to be a JSON object).

        Raises:
            CareerExtractionFailureError: When the provider call fails or returns
                an empty response.
        """
        try:
            raw_text = provider.complete(system_prompt, user_prompt)
        except Exception as exc:
            raise CareerExtractionFailureError(
                "LLM call for career extraction failed.",
                cause=exc,
            ) from exc

        raw_text = raw_text.strip()
        if not raw_text:
            raise CareerExtractionFailureError(
                "LLM provider returned an empty response for career extraction."
            )
        return raw_text