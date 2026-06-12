"""Task extraction service.

Implements the application-facing orchestration for the task extraction
pipeline stage.

Responsibilities:
- build extraction prompt
- call LLM provider via the BaseLLMProvider summarize interface
- parse JSON response
- validate extracted tasks
- calculate extraction confidence
- deduplicate tasks
- return :class:`~infrastructure.ai.task_extraction.schemas.TaskExtractionResult`

This module does not access the database or repositories.
"""

from __future__ import annotations

import json
import logging
import time
from json import JSONDecodeError
from typing import Any
from uuid import UUID

from core.config import Settings
from infrastructure.ai.llm.base import BaseLLMProvider
from infrastructure.ai.llm.exceptions import LLMProviderError
from infrastructure.ai.llm.provider_factory import LLMProviderFactory
from infrastructure.ai.task_extraction.deduplication import TaskDeduplicationService
from infrastructure.ai.task_extraction.exceptions import (
    TaskExtractionFailureError,
    TaskExtractionMalformedResponseError,
    TaskExtractionValidationError,
)
from infrastructure.ai.task_extraction.prompts import (
    TaskExtractionPrompt,
    build_task_extraction_prompts,
)
from infrastructure.ai.task_extraction.schemas import (
    ConfidenceScore,
    ExtractedTask,
    TaskExtractionRequest,
    TaskExtractionResult,
)

logger = logging.getLogger(__name__)

# Sentinel UUID used when no real email id is available at prompt-build time.
_NIL_UUID = UUID(int=0)


def _extract_json_object(text: str) -> dict[str, Any]:
    """Extract a JSON object from model output, stripping markdown fences if present.

    Args:
        text: Raw model output expected to contain a JSON object.

    Returns:
        Parsed JSON object as a plain dict.

    Raises:
        TaskExtractionMalformedResponseError: When the output cannot be parsed
            as a JSON object.
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
        raise TaskExtractionMalformedResponseError(
            f"Task extraction response was not valid JSON: {exc}",
            cause=exc,
        ) from exc

    if not isinstance(payload, dict):
        raise TaskExtractionMalformedResponseError(
            f"Task extraction response JSON must be an object, got {type(payload).__name__}.",
        )
    return payload


def _calculate_extraction_confidence(tasks: list[ExtractedTask]) -> float:
    """Calculate overall extraction confidence as the mean of individual scores.

    Args:
        tasks: Validated extracted tasks.

    Returns:
        Mean confidence in [0.0, 1.0], or 0.0 when the list is empty.
    """
    if not tasks:
        return 0.0
    return float(sum(t.confidence_score for t in tasks) / len(tasks))


class TaskExtractionService:
    """Orchestrates task extraction from an email using an LLM provider."""

    def __init__(
        self,
        *,
        provider: BaseLLMProvider | None = None,
        provider_factory: LLMProviderFactory | None = None,
        deduplication_service: TaskDeduplicationService | None = None,
        settings: Settings | None = None,
        max_retries: int | None = None,
    ) -> None:
        """Initialise the task extraction service.

        Args:
            provider: Optional injected LLM provider.
            provider_factory: Optional injected provider factory.
            deduplication_service: Optional injected deduplication service.
            settings: Optional app settings.
            max_retries: Optional override for retry count.
        """
        self._settings = settings
        self._provider_factory = provider_factory or LLMProviderFactory(settings)
        self._provider = provider
        self._deduper = deduplication_service or TaskDeduplicationService()
        self._max_retries = max_retries

    def extract_tasks(
        self,
        request: TaskExtractionRequest,
        *,
        source_title: str | None = None,
    ) -> TaskExtractionResult:
        """Extract tasks from an email using the configured LLM provider.

        Args:
            request: Task extraction request carrying email context.
            source_title: Optional explicit title override.

        Returns:
            A validated and deduplicated :class:`TaskExtractionResult`.

        Raises:
            TaskExtractionFailureError: When extraction fails after retries.
            TaskExtractionValidationError: When the response cannot be validated.
            TaskExtractionMalformedResponseError: When the response is malformed.
        """
        provider = self._provider or self._provider_factory.create_provider()

        max_retries = self._max_retries
        if max_retries is None:
            max_retries = (
                self._settings.llm_max_retries if self._settings is not None else None
            )
        if not max_retries:
            max_retries = 3

        prompt: TaskExtractionPrompt = build_task_extraction_prompts(
            email_title=source_title if source_title is not None else request.title,
            email_description=request.description,
            source_sender=request.source_sender,
            source_company=request.source_company,
        )

        last_exc: BaseException | None = None

        for attempt in range(1, max_retries + 1):
            try:
                raw_text = self._call_provider(provider, prompt)
                payload = _extract_json_object(raw_text)
                result = self._validate_and_process(payload, request)
                return result
            except (
                TaskExtractionMalformedResponseError,
                TaskExtractionValidationError,
            ) as exc:
                # Deterministic failures — retrying the same output will not help.
                last_exc = exc
                logger.warning(
                    "task_extraction_parse_error_attempt_%d",
                    attempt,
                    extra={"error": str(exc)},
                )
                raise
            except TaskExtractionFailureError:
                raise
            except Exception as exc:
                last_exc = exc
                logger.warning(
                    "task_extraction_provider_error_attempt_%d_of_%d",
                    attempt,
                    max_retries,
                    extra={"error": str(exc)},
                )
                if attempt >= max_retries:
                    raise TaskExtractionFailureError(
                        "Task extraction failed after exhausting retries.",
                        cause=exc,
                    ) from exc
                delay = min(2.0 * (2 ** (attempt - 1)), 8.0)
                time.sleep(delay)

        assert last_exc is not None
        raise TaskExtractionFailureError(
            "Task extraction failed.",
            cause=last_exc,
        )

    # ------------------------------------------------------------------
    # Provider invocation
    # ------------------------------------------------------------------

    def _call_provider(
        self,
        provider: BaseLLMProvider,
        prompt: TaskExtractionPrompt,
    ) -> str:
        """Call the LLM provider and return the raw model output text.

        Uses :meth:`~infrastructure.ai.llm.base.BaseLLMProvider.complete` to
        send the task extraction prompt pair directly, bypassing any
        summarization-specific prompt wrapping in the provider implementations.

        Args:
            provider: Configured LLM provider instance.
            prompt: Pre-built system/user prompt pair.

        Returns:
            Raw model output string (expected to be a JSON object).

        Raises:
            TaskExtractionFailureError: When the provider call fails or returns
                an empty response.
        """
        try:
            raw_text = provider.complete(prompt.system, prompt.user)
        except LLMProviderError as exc:
            raise TaskExtractionFailureError(
                f"LLM provider failed during task extraction: {exc}",
                cause=exc,
            ) from exc
        except Exception as exc:
            raise TaskExtractionFailureError(
                "Unexpected error calling LLM provider for task extraction.",
                cause=exc,
            ) from exc

        raw_text = raw_text.strip()
        if not raw_text:
            raise TaskExtractionFailureError(
                "LLM provider returned an empty response for task extraction."
            )

        logger.debug(
            "task_extraction_raw_response",
            extra={"preview": raw_text[:500]},
        )
        return raw_text

    # ------------------------------------------------------------------
    # Validation and post-processing
    # ------------------------------------------------------------------

    def _validate_and_process(
        self,
        payload: dict[str, Any],
        request: TaskExtractionRequest,
    ) -> TaskExtractionResult:
        """Validate the model payload and post-process deterministically.

        Injects ``source_sender`` and ``source_company`` from the original
        request into each raw task dict before Pydantic validation, because
        the LLM output schema does not include sender metadata.

        Args:
            payload: Parsed JSON payload from the model.
            request: The original extraction request carrying sender metadata.

        Returns:
            Validated :class:`TaskExtractionResult` with deduplicated tasks.

        Raises:
            TaskExtractionMalformedResponseError: When the payload shape is invalid.
            TaskExtractionValidationError: When DTO validation fails.
        """
        raw_tasks = payload.get("tasks")
        if raw_tasks is None or not isinstance(raw_tasks, list):
            raise TaskExtractionMalformedResponseError(
                "Task extraction payload must include a 'tasks' array.",
            )

        extracted_tasks: list[ExtractedTask] = []

        for index, item in enumerate(raw_tasks):
            if not isinstance(item, dict):
                raise TaskExtractionMalformedResponseError(
                    f"Task at index {index} must be a JSON object.",
                )

            # Inject request-level metadata the LLM does not emit.
            item.setdefault("source_sender", request.source_sender)
            item.setdefault("source_company", request.source_company)

            try:
                extracted_tasks.append(ExtractedTask.model_validate(item))
            except Exception as exc:
                raise TaskExtractionValidationError(
                    f"Task at index {index} failed validation: {exc}",
                    cause=exc,
                ) from exc

        deduped = self._deduper.deduplicate(extracted_tasks)

        extraction_confidence: ConfidenceScore = _calculate_extraction_confidence(deduped)

        try:
            return TaskExtractionResult(
                tasks=deduped,
                extraction_confidence=extraction_confidence,
                extracted_task_count=len(deduped),
            )
        except Exception as exc:
            raise TaskExtractionValidationError(
                f"Task extraction result failed validation: {exc}",
                cause=exc,
            ) from exc