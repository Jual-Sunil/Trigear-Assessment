"""Email processing orchestration service.

Coordinates all AI processing stages for a single imported email entity.
Stages run in strict dependency order:

1. Classification
2. Priority Scoring  (requires classification)
3. Summarization     (requires classification)
4. Task Extraction   (uses summary when available)
5. Career Extraction (uses summary and email content)

Each stage persists its results immediately via repositories.
Task and career extraction failures are non-fatal; processing continues.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from time import perf_counter
from uuid import UUID

from core.constants import CAREER_ELIGIBLE_CATEGORIES

# Categories for which LLM-based summarization and task extraction are
# skipped because they almost never contain actionable content.
_SUMMARY_SKIP_CATEGORIES: frozenset[str] = frozenset({"Spam", "Promotion", "Newsletter"})
_TASK_SKIP_CATEGORIES: frozenset[str] = frozenset({"Spam", "Promotion", "Newsletter"})
from infrastructure.ai.career_extraction.career_extraction_service import (
    CareerExtractionService,
)
from infrastructure.ai.career_extraction.exceptions import CareerExtractionFailureError
from infrastructure.ai.career_extraction.schemas import (
    CareerExtractionRequest,
    CareerExtractionResult,
)
from infrastructure.ai.classification.classification_service import (
    ClassificationService,
)
from infrastructure.ai.classification.exceptions import ClassificationInputError
from infrastructure.ai.classification.schemas import (
    ClassificationResult,
    EmailClassificationInput,
)
from infrastructure.ai.priority.priority_scoring_service import PriorityScoringService
from infrastructure.ai.priority.schemas import PriorityScoreResult
from infrastructure.ai.summarization.exceptions import EmailSummarizationError
from infrastructure.ai.summarization.schemas import (
    EmailSummaryRequest,
    EmailSummaryResult,
)
from infrastructure.ai.summarization.summarization_service import SummarizationService
from infrastructure.ai.task_extraction.exceptions import TaskExtractionFailureError
from infrastructure.ai.task_extraction.schemas import (
    TaskExtractionRequest,
    TaskExtractionResult,
)
from infrastructure.ai.task_extraction.task_extraction_service import (
    TaskExtractionService,
)
from infrastructure.database.models.email import Email
from infrastructure.database.models.interview import Interview
from infrastructure.database.models.job_opportunity import JobOpportunity
from infrastructure.database.models.task import Task
from infrastructure.database.repositories.email_repository import (
    _UNSET,
    EmailRepository,
)
from infrastructure.database.repositories.interview_repository import (
    InterviewRepository,
)
from infrastructure.database.repositories.job_opportunity_repository import (
    JobOpportunityRepository,
)
from infrastructure.database.repositories.task_repository import TaskRepository

logger = logging.getLogger(__name__)


@contextmanager
def _stage_timer(timings: dict[str, float], stage: str) -> Iterator[None]:
    """Record the wall-clock duration of a pipeline stage into ``timings``.

    The duration is recorded even when the wrapped block raises, so failed
    stages still contribute timing data for bottleneck analysis.

    Args:
        timings: Mutable mapping to write the elapsed seconds into.
        stage: Key under which to store the elapsed duration.

    Yields:
        ``None``; the elapsed time is written on exit.
    """
    start = perf_counter()
    try:
        yield
    finally:
        timings[stage] = perf_counter() - start


@dataclass(slots=True)
class EmailProcessingOutcome:
    """Computed AI results for a single email, ready to be persisted.

    Produced by :meth:`EmailProcessingService.compute` (which performs no
    database writes) and consumed by :meth:`EmailProcessingService.persist`.
    Separating compute from persistence lets the compute phase run
    concurrently across many emails while database writes remain serialized on
    the shared, non-concurrency-safe :class:`AsyncSession`.

    Attributes:
        classification: Classification result, or ``None`` when skipped/failed.
        priority: Priority score result, or ``None`` when skipped/failed.
        summary: Summary result, or ``None`` when skipped/failed.
        task_result: Task extraction result, or ``None`` when skipped/failed.
        career_result: Career extraction result, or ``None`` when skipped/failed.
        skip_tasks: ``True`` when task persistence must be skipped (already present).
        skip_job: ``True`` when job persistence must be skipped (already present).
        skip_interview: ``True`` when interview persistence must be skipped.
        timings: Per-stage wall-clock durations in seconds.
    """

    classification: ClassificationResult | None = None
    priority: PriorityScoreResult | None = None
    summary: EmailSummaryResult | None = None
    task_result: TaskExtractionResult | None = None
    career_result: CareerExtractionResult | None = None
    skip_tasks: bool = False
    skip_job: bool = False
    skip_interview: bool = False
    timings: dict[str, float] = field(default_factory=dict)


class EmailProcessingService:
    """Orchestrate all AI processing stages for a single email entity.

    The service processes one :class:`~infrastructure.database.models.email.Email`
    ORM entity at a time, executing each AI stage in dependency order and
    persisting results via injected repositories.

    Skips any stage whose output already exists on the email to prevent
    redundant reprocessing during retry or requeue scenarios.

    Task extraction and career extraction failures are handled gracefully;
    a failure in either stage logs a warning and allows the pipeline to
    complete the remaining stages.
    """

    def __init__(
        self,
        *,
        email_repository: EmailRepository,
        task_repository: TaskRepository,
        job_opportunity_repository: JobOpportunityRepository,
        interview_repository: InterviewRepository,
        classification_service: ClassificationService | None = None,
        priority_scoring_service: PriorityScoringService | None = None,
        summarization_service: SummarizationService | None = None,
        task_extraction_service: TaskExtractionService | None = None,
        career_extraction_service: CareerExtractionService | None = None,
    ) -> None:
        """Initialise the service with repositories and optional AI service overrides.

        Args:
            email_repository: Repository for reading and updating email records.
            task_repository: Repository for persisting extracted tasks.
            job_opportunity_repository: Repository for persisting job opportunities.
            interview_repository: Repository for persisting interview records.
            classification_service: Optional classification service override.
            priority_scoring_service: Optional priority scoring service override.
            summarization_service: Optional summarization service override.
            task_extraction_service: Optional task extraction service override.
            career_extraction_service: Optional career extraction service override.
        """
        self._email_repo = email_repository
        self._task_repo = task_repository
        self._job_repo = job_opportunity_repository
        self._interview_repo = interview_repository

        self._classification_service = classification_service or ClassificationService()
        self._priority_service = priority_scoring_service or PriorityScoringService()
        self._summarization_service = summarization_service or SummarizationService()
        self._task_extraction_service = (
            task_extraction_service or TaskExtractionService()
        )
        self._career_extraction_service = (
            career_extraction_service or CareerExtractionService()
        )

    async def process(self, email: Email) -> None:
        """Execute the full AI processing pipeline for a single email.

        Convenience wrapper that runs :meth:`compute` followed by
        :meth:`persist`. Idempotency checks (existing tasks/jobs/interviews)
        are resolved up front so the compute phase performs no database access.

        Args:
            email: The :class:`~infrastructure.database.models.email.Email`
                ORM entity to process.
        """
        has_tasks = await self._task_repo.email_has_tasks(email.id)
        has_job = await self._job_repo.email_has_job_opportunity(email.id)
        has_interview = await self._interview_repo.email_has_interview(email.id)

        outcome = await self.compute(
            email,
            has_tasks=has_tasks,
            has_job=has_job,
            has_interview=has_interview,
        )
        await self.persist(email, outcome)

    async def compute(
        self,
        email: Email,
        *,
        has_tasks: bool,
        has_job: bool,
        has_interview: bool,
        precomputed_classification: ClassificationResult | None = None,
        classification_duration: float | None = None,
    ) -> EmailProcessingOutcome:
        """Run all AI stages for one email **without touching the database**.

        Stages run in dependency order: classification → priority → summary,
        then task and career extraction concurrently (both depend only on the
        summary/body). Synchronous, blocking AI/LLM calls are offloaded to
        worker threads via :func:`asyncio.to_thread` so that ``compute`` calls
        for different emails can overlap when scheduled concurrently.

        In-memory attributes on ``email`` (classification, confidence,
        priority, summary) are updated so dependent stages observe them; the
        corresponding database writes happen later in :meth:`persist`.

        Args:
            email: The email entity to process.
            has_tasks: Whether tasks already exist for this email.
            has_job: Whether a job opportunity already exists for this email.
            has_interview: Whether an interview already exists for this email.
            precomputed_classification: Optional classification result supplied
                by a batched classifier; when given, per-email classification
                inference is skipped.
            classification_duration: Optional per-email classification duration
                attributed to a batched classification call, for instrumentation.

        Returns:
            An :class:`EmailProcessingOutcome` carrying the computed results and
            per-stage timings.
        """
        logger.info(
            "email_processing_started",
            extra={
                "email_id": str(email.id),
                "gmail_message_id": email.gmail_message_id,
            },
        )

        timings: dict[str, float] = {}

        classification_result = precomputed_classification
        if precomputed_classification is not None:
            if classification_duration is not None:
                timings["classification"] = classification_duration
        elif email.classification is None:
            with _stage_timer(timings, "classification"):
                classification_result = await self._run_classification(email)
        if classification_result is not None:
            email.classification = classification_result.category
            email.confidence_score = classification_result.confidence_score

        # Priority scoring (deterministic) and summarization (LLM) are
        # independent once classification is known — run concurrently.
        need_priority = email.priority_score is None
        need_summary = (
            email.summary is None
            and email.classification not in _SUMMARY_SKIP_CATEGORIES
        )

        priority_result: PriorityScoreResult | None = None
        summary_result: EmailSummaryResult | None = None

        async def _priority_task() -> PriorityScoreResult | None:
            if not need_priority:
                return None
            with _stage_timer(timings, "priority"):
                return await self._run_priority_scoring(email)

        async def _summary_task() -> EmailSummaryResult | None:
            if not need_summary:
                if email.summary is None and email.classification in _SUMMARY_SKIP_CATEGORIES:
                    logger.debug(
                        "summarization_skipped_low_value_category",
                        extra={
                            "email_id": str(email.id),
                            "classification": email.classification,
                        },
                    )
                return None
            with _stage_timer(timings, "summarization"):
                return await self._run_summarization(email)

        priority_result, summary_result = await asyncio.gather(
            _priority_task(), _summary_task()
        )

        if priority_result is not None:
            email.priority_score = priority_result.priority_score
        if summary_result is not None:
            email.summary = summary_result.summary

        task_result, career_result = await asyncio.gather(
            self._timed_task_extraction(email, summary_result, has_tasks, timings),
            self._timed_career_extraction(
                email, summary_result, has_job, has_interview, timings
            ),
        )

        return EmailProcessingOutcome(
            classification=classification_result,
            priority=priority_result,
            summary=summary_result,
            task_result=task_result,
            career_result=career_result,
            skip_tasks=has_tasks,
            skip_job=has_job,
            skip_interview=has_interview,
            timings=timings,
        )

    async def persist(self, email: Email, outcome: EmailProcessingOutcome) -> float:
        """Persist a computed :class:`EmailProcessingOutcome` to the database.

        Writes must be serialized by the caller because the shared
        :class:`AsyncSession` is not safe for concurrent use. The AI scalar
        fields (classification, confidence, priority, summary) are written in a
        single update to minimise round trips.

        Args:
            email: The email entity whose results are being persisted.
            outcome: The computed results from :meth:`compute`.

        Returns:
            The wall-clock database persistence duration in seconds.
        """
        start = perf_counter()

        await self._email_repo.update_ai_fields(
            email,
            classification=(
                outcome.classification.category
                if outcome.classification is not None
                else _UNSET
            ),
            confidence_score=(
                outcome.classification.confidence_score
                if outcome.classification is not None
                else _UNSET
            ),
            priority_score=(
                outcome.priority.priority_score
                if outcome.priority is not None
                else _UNSET
            ),
            summary=(
                outcome.summary.summary if outcome.summary is not None else _UNSET
            ),
        )

        if outcome.task_result is not None and outcome.task_result.tasks:
            await self._persist_tasks(email.id, outcome.task_result)

        if outcome.career_result is not None:
            if not outcome.skip_job and outcome.career_result.job_opportunities:
                await self._persist_job_opportunities(email.id, outcome.career_result)
            if not outcome.skip_interview and outcome.career_result.interviews:
                await self._persist_interviews(email.id, outcome.career_result)

        duration = perf_counter() - start
        outcome.timings["db_persist"] = duration

        logger.info(
            "email_processing_completed",
            extra={
                "email_id": str(email.id),
                "timings_seconds": {
                    stage: round(value, 4)
                    for stage, value in outcome.timings.items()
                },
            },
        )
        return duration

    def classify_batch(
        self,
        emails: list[Email],
    ) -> list[ClassificationResult | None]:
        """Classify many emails in a single batched zero-shot inference call.

        This is a synchronous, CPU-bound operation (it runs the local zero-shot
        model) and should be offloaded to a worker thread by the caller. Emails
        that are already classified, or that produce no usable classification
        text, yield ``None`` at their matching index so the result aligns 1:1
        with ``emails``.

        Args:
            emails: The email entities to classify.

        Returns:
            A list aligned with ``emails`` of classification results (or
            ``None`` when skipped or on failure).
        """
        results: list[ClassificationResult | None] = [None] * len(emails)

        inputs: list[EmailClassificationInput] = []
        positions: list[int] = []
        for index, email in enumerate(emails):
            if email.classification is not None:
                continue
            try:
                inputs.append(
                    EmailClassificationInput(
                        gmail_message_id=email.gmail_message_id,
                        subject=email.subject,
                        body_text=email.body_text,
                        snippet=email.snippet,
                        sender_email=email.sender_email,
                    )
                )
                positions.append(index)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "classification_skipped_invalid_input",
                    extra={"email_id": str(email.id), "reason": str(exc)},
                )

        if not inputs:
            return results

        try:
            batch_results = self._classification_service.classify_batch(inputs)
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "classification_batch_failed",
                extra={"error": str(exc), "batch_size": len(inputs)},
                exc_info=True,
            )
            return results

        for position, result in zip(positions, batch_results):
            results[position] = result
        return results

    async def _timed_task_extraction(
        self,
        email: Email,
        summary_result: EmailSummaryResult | None,
        has_tasks: bool,
        timings: dict[str, float],
    ) -> TaskExtractionResult | None:
        """Run task extraction under a stage timer (concurrency-friendly wrapper)."""
        if has_tasks:
            logger.debug(
                "task_extraction_skipped_tasks_exist",
                extra={"email_id": str(email.id)},
            )
            return None
        if email.classification in _TASK_SKIP_CATEGORIES:
            logger.debug(
                "task_extraction_skipped_low_value_category",
                extra={
                    "email_id": str(email.id),
                    "classification": email.classification,
                },
            )
            return None
        with _stage_timer(timings, "task_extraction"):
            return await self._compute_task_extraction(email, summary_result)

    async def _timed_career_extraction(
        self,
        email: Email,
        summary_result: EmailSummaryResult | None,
        has_job: bool,
        has_interview: bool,
        timings: dict[str, float],
    ) -> CareerExtractionResult | None:
        """Run career extraction under a stage timer (concurrency-friendly wrapper).

        Career extraction is only executed for emails classified into one of
        the :data:`~core.constants.CAREER_ELIGIBLE_CATEGORIES` (Work,
        Interview, Job Opportunity).  All other categories are skipped to
        save LLM token usage.
        """
        if has_job and has_interview:
            logger.debug(
                "career_extraction_skipped_records_exist",
                extra={"email_id": str(email.id)},
            )
            return None

        if email.classification not in CAREER_ELIGIBLE_CATEGORIES:
            logger.debug(
                "career_extraction_skipped_ineligible_category",
                extra={
                    "email_id": str(email.id),
                    "classification": email.classification,
                },
            )
            return None

        with _stage_timer(timings, "career_extraction"):
            return await self._compute_career_extraction(email, summary_result)

    # ------------------------------------------------------------------
    # Stage 1 — Classification
    # ------------------------------------------------------------------

    async def _run_classification(
        self,
        email: Email,
    ) -> ClassificationResult | None:
        """Run email classification unless a result already exists.

        Args:
            email: The email entity to classify.

        Returns:
            A :class:`ClassificationResult` when classification succeeds,
            or ``None`` when the email is already classified or classification
            raises a non-recoverable error.
        """
        if email.classification is not None:
            logger.debug(
                "classification_skipped_already_classified",
                extra={"email_id": str(email.id)},
            )
            return None

        try:
            input_data = EmailClassificationInput(
                gmail_message_id=email.gmail_message_id,
                subject=email.subject,
                body_text=email.body_text,
                snippet=email.snippet,
                sender_email=email.sender_email,
            )
            result = await asyncio.to_thread(
                self._classification_service.classify, input_data
            )
            logger.info(
                "classification_succeeded",
                extra={
                    "email_id": str(email.id),
                    "category": result.category,
                    "confidence": result.confidence_score,
                },
            )
            return result
        except ClassificationInputError as exc:
            logger.warning(
                "classification_skipped_no_usable_text",
                extra={"email_id": str(email.id), "reason": str(exc)},
            )
            return None
        except Exception as exc:
            logger.error(
                "classification_failed_unexpected",
                extra={"email_id": str(email.id), "error": str(exc)},
                exc_info=True,
            )
            return None

    # ------------------------------------------------------------------
    # Stage 2 — Priority Scoring
    # ------------------------------------------------------------------

    async def _run_priority_scoring(
        self,
        email: Email,
    ) -> PriorityScoreResult | None:
        """Compute a priority score for the email unless one already exists.

        Classification must have been run and persisted before this stage
        so that the scorer can incorporate the classification category.

        Args:
            email: The email entity to score.

        Returns:
            A :class:`PriorityScoreResult` when scoring succeeds,
            or ``None`` when the score already exists or scoring fails.
        """
        if email.priority_score is not None:
            logger.debug(
                "priority_scoring_skipped_already_scored",
                extra={"email_id": str(email.id)},
            )
            return None

        try:
            result = await asyncio.to_thread(self._priority_service.score, email)
            logger.info(
                "priority_scoring_succeeded",
                extra={
                    "email_id": str(email.id),
                    "priority_score": result.priority_score,
                },
            )
            return result
        except Exception as exc:
            logger.error(
                "priority_scoring_failed",
                extra={"email_id": str(email.id), "error": str(exc)},
                exc_info=True,
            )
            return None

    # ------------------------------------------------------------------
    # Stage 3 — Summarization
    # ------------------------------------------------------------------

    async def _run_summarization(
        self,
        email: Email,
    ) -> EmailSummaryResult | None:
        """Generate a structured email summary unless one already exists.

        Args:
            email: The email entity to summarize.

        Returns:
            An :class:`EmailSummaryResult` when summarization succeeds,
            or ``None`` when a summary already exists or generation fails.
        """
        if email.summary is not None:
            logger.debug(
                "summarization_skipped_already_summarized",
                extra={"email_id": str(email.id)},
            )
            return None

        try:
            request = EmailSummaryRequest(
                email_id=email.id,
                subject=email.subject,
                sender=email.sender_name or email.sender_email,
                body=email.body_text,
                received_at=email.received_at,
            )
            result = await asyncio.to_thread(
                self._summarization_service.summarize, request
            )
            logger.info(
                "summarization_succeeded",
                extra={"email_id": str(email.id)},
            )
            return result
        except EmailSummarizationError as exc:
            logger.exception(
                "summarization_failed",
                extra={
                    "email_id": str(email.id),
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                },
            )
            return None
        except Exception as exc:
            logger.error(
                "summarization_failed_unexpected",
                extra={"email_id": str(email.id), "error": str(exc)},
                exc_info=True,
            )
            return None

    # ------------------------------------------------------------------
    # Stage 4 — Task Extraction
    # ------------------------------------------------------------------

    async def _compute_task_extraction(
        self,
        email: Email,
        summary_result: EmailSummaryResult | None,
    ) -> TaskExtractionResult | None:
        """Extract tasks from the email **without** persisting them.

        Uses the generated summary as the primary description context when
        available; falls back to the raw email body otherwise. The blocking
        LLM call is offloaded to a worker thread so it can overlap with career
        extraction (and with other emails' compute calls).

        Failures are logged as warnings and yield ``None`` so the pipeline
        continues.

        Args:
            email: The email entity to extract tasks from.
            summary_result: The summary produced in stage 3, or ``None``.

        Returns:
            A :class:`TaskExtractionResult` to be persisted later, or ``None``
            when extraction fails.
        """
        try:
            description = (
                summary_result.summary
                if summary_result is not None
                else email.body_text
            )

            request = TaskExtractionRequest(
                title=email.subject,
                description=description,
                source_sender=email.sender_email,
                source_company=None,
            )

            result: TaskExtractionResult = await asyncio.to_thread(
                self._task_extraction_service.extract_tasks,
                request,
                source_title=email.subject,
            )

            logger.info(
                "task_extraction_succeeded",
                extra={
                    "email_id": str(email.id),
                    "task_count": result.extracted_task_count,
                },
            )
            return result

        except TaskExtractionFailureError as exc:
            logger.warning(
                "task_extraction_failed",
                extra={"email_id": str(email.id), "error": str(exc)},
            )
            return None
        except Exception as exc:
            logger.warning(
                "task_extraction_failed_unexpected",
                extra={"email_id": str(email.id), "error": str(exc)},
                exc_info=True,
            )
            return None

    async def _persist_tasks(
        self,
        email_id: UUID,
        result: TaskExtractionResult,
    ) -> None:
        """Persist extracted task records to the database.

        Args:
            email_id: The UUID of the parent email.
            result: The validated task extraction result.
        """
        task_models = [
            Task(
                email_id=email_id,
                title=extracted.title,
                description=extracted.description,
                priority=extracted.priority,
                due_date=extracted.due_date,
            )
            for extracted in result.tasks
        ]
        await self._task_repo.bulk_create_tasks(task_models)
        logger.debug(
            "tasks_persisted",
            extra={"email_id": str(email_id), "count": len(task_models)},
        )

    # ------------------------------------------------------------------
    # Stage 5 — Career Extraction
    # ------------------------------------------------------------------

    async def _compute_career_extraction(
        self,
        email: Email,
        summary_result: EmailSummaryResult | None,
    ) -> CareerExtractionResult | None:
        """Extract job opportunities and interviews **without** persisting them.

        The blocking LLM call is offloaded to a worker thread so it can overlap
        with task extraction (and with other emails' compute calls).

        Failures are logged as warnings and yield ``None`` so the pipeline
        continues.

        Args:
            email: The email entity to extract career data from.
            summary_result: The summary produced in stage 3, or ``None``.

        Returns:
            A :class:`CareerExtractionResult` to be persisted later, or ``None``
            when extraction fails.
        """
        try:
            # Career extraction requires the raw email content to extract
            # structured fields (company, role, apply_link, salary, location).
            # Summaries collapse job alert emails to one-liners that lose all
            # structured data. Use body_text when available, fall back to the
            # summary only when no body content exists at all.
            #
            # Some emails have useless body_text (e.g. "Please Enable
            # Javascript") while all actual content is in body_html.  Treat
            # very short body_text (<50 chars) as absent so the link
            # extractor + snippet can fill the gap.
            usable_body = email.body_text
            if usable_body and len(usable_body.strip()) < 50:
                usable_body = None

            body_context = (
                usable_body
                if usable_body
                else email.snippet
                if email.snippet
                else summary_result.summary
                if summary_result is not None
                else None
            )

            request = CareerExtractionRequest(
                subject=email.subject,
                sender=email.sender_email,
                body=body_context,
                body_html=email.body_html,
            )

            result: CareerExtractionResult = await asyncio.to_thread(
                self._career_extraction_service.extract_career, request
            )

            logger.info(
                "career_extraction_succeeded",
                extra={
                    "email_id": str(email.id),
                    "jobs": len(result.job_opportunities),
                    "interviews": len(result.interviews),
                },
            )
            return result

        except CareerExtractionFailureError as exc:
            logger.warning(
                "career_extraction_failed",
                extra={"email_id": str(email.id), "error": str(exc)},
            )
            return None
        except Exception as exc:
            logger.warning(
                "career_extraction_failed_unexpected",
                extra={"email_id": str(email.id), "error": str(exc)},
                exc_info=True,
            )
            return None

    async def _persist_job_opportunities(
        self,
        email_id: UUID,
        result: CareerExtractionResult,
    ) -> None:
        """Persist extracted job opportunity records to the database.

        The ``deadline`` field from :class:`JobOpportunityData` is provided
        as a plain string by the extractor; the ORM column expects a
        ``datetime`` so it is omitted here and left ``None`` pending a
        dedicated parsing step in a future phase.

        Args:
            email_id: The UUID of the parent email.
            result: The validated career extraction result containing jobs.
        """
        job_models = [
            JobOpportunity(
                email_id=email_id,
                company=job.company,
                role=job.role,
                location=job.location,
                salary=job.salary,
                apply_link=job.apply_link,
                deadline=None,
            )
            for job in result.job_opportunities
        ]
        await self._job_repo.bulk_create(job_models)
        logger.debug(
            "job_opportunities_persisted",
            extra={"email_id": str(email_id), "count": len(job_models)},
        )

    async def _persist_interviews(
        self,
        email_id: UUID,
        result: CareerExtractionResult,
    ) -> None:
        """Persist extracted interview records to the database.

        The ``interview_date`` field from :class:`InterviewData` is provided
        as a plain string by the extractor; the ORM column expects a
        ``datetime`` so it is omitted here and left ``None`` pending a
        dedicated parsing step in a future phase.

        Args:
            email_id: The UUID of the parent email.
            result: The validated career extraction result containing interviews.
        """
        interview_models = [
            Interview(
                email_id=email_id,
                company=interview.company,
                role=interview.role,
                interview_date=None,
                meeting_link=interview.meeting_link,
            )
            for interview in result.interviews
        ]
        await self._interview_repo.bulk_create(interview_models)
        logger.debug(
            "interviews_persisted",
            extra={"email_id": str(email_id), "count": len(interview_models)},
        )