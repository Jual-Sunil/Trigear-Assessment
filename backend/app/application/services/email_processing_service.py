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

import logging
from uuid import UUID

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
from infrastructure.database.repositories.email_repository import EmailRepository
from infrastructure.database.repositories.interview_repository import (
    InterviewRepository,
)
from infrastructure.database.repositories.job_opportunity_repository import (
    JobOpportunityRepository,
)
from infrastructure.database.repositories.task_repository import TaskRepository

logger = logging.getLogger(__name__)


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

        Stages are executed in dependency order. Each stage's output is
        persisted before the next stage begins. Failures in task extraction
        or career extraction are logged and do not abort the pipeline.

        Args:
            email: The :class:`~infrastructure.database.models.email.Email`
                ORM entity to process.
        """
        logger.info(
            "email_processing_started",
            extra={
                "email_id": str(email.id),
                "gmail_message_id": email.gmail_message_id,
            },
        )

        classification_result = await self._run_classification(email)
        if classification_result is not None:
            await self._persist_classification(email, classification_result)

        priority_result = await self._run_priority_scoring(email)
        if priority_result is not None:
            await self._persist_priority_score(email, priority_result)

        summary_result = await self._run_summarization(email)
        if summary_result is not None:
            await self._persist_summary(email, summary_result)

        await self._run_task_extraction(email, summary_result)
        await self._run_career_extraction(email, summary_result)

        logger.info(
            "email_processing_completed",
            extra={"email_id": str(email.id)},
        )

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
            result = self._classification_service.classify(input_data)
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

    async def _persist_classification(
        self,
        email: Email,
        result: ClassificationResult,
    ) -> None:
        """Persist classification and confidence score to the email record.

        Mutates ``email.classification`` and ``email.confidence_score`` so
        that subsequent stages within the same processing call see the
        updated values without requiring a database reload.

        Args:
            email: The email entity to update.
            result: The classification result to persist.
        """
        await self._email_repo.update_classification(
            email.gmail_message_id,
            result.category,
            result.confidence_score,
        )
        email.classification = result.category
        email.confidence_score = result.confidence_score
        logger.debug(
            "classification_persisted",
            extra={"email_id": str(email.id), "category": result.category},
        )

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
            result = self._priority_service.score(email)
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

    async def _persist_priority_score(
        self,
        email: Email,
        result: PriorityScoreResult,
    ) -> None:
        """Persist the computed priority score to the email record.

        Mutates ``email.priority_score`` so subsequent in-process reads
        reflect the updated value.

        Args:
            email: The email entity to update.
            result: The priority score result to persist.
        """
        await self._email_repo.update_priority_score(
            email.gmail_message_id,
            result.priority_score,
        )
        email.priority_score = result.priority_score
        logger.debug(
            "priority_score_persisted",
            extra={"email_id": str(email.id), "score": result.priority_score},
        )

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
            result = self._summarization_service.summarize(request)
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

    async def _persist_summary(
        self,
        email: Email,
        result: EmailSummaryResult,
    ) -> None:

        logger.info(
            "persist_summary_started",
            extra={
                "email_id": str(email.id),
                "gmail_message_id": email.gmail_message_id,
            },
        )

        await self._email_repo.update_summary(
            email.gmail_message_id,
            result.summary,
        )

        logger.info(
            "persist_summary_db_update_completed",
            extra={
                "email_id": str(email.id),
            },
        )

        email.summary = result.summary

        logger.info(
            "summary_persisted",
            extra={
                "email_id": str(email.id),
            },
        )

    # ------------------------------------------------------------------
    # Stage 4 — Task Extraction
    # ------------------------------------------------------------------

    async def _run_task_extraction(
        self,
        email: Email,
        summary_result: EmailSummaryResult | None,
    ) -> None:
        """Extract and persist tasks from the email.

        Uses the generated summary as the primary description context when
        available; falls back to the raw email body otherwise.

        Skips extraction when tasks already exist for the email to prevent
        duplicate records across retries.

        Failures are logged as warnings and do not abort the pipeline.

        Args:
            email: The email entity to extract tasks from.
            summary_result: The summary produced in stage 3, or ``None``.
        """
        try:
            already_has_tasks = await self._task_repo.email_has_tasks(email.id)
            if already_has_tasks:
                logger.debug(
                    "task_extraction_skipped_tasks_exist",
                    extra={"email_id": str(email.id)},
                )
                return

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

            result: TaskExtractionResult = (
                self._task_extraction_service.extract_tasks(
                    request,
                    source_title=email.subject,
                )
            )

            if result.tasks:
                await self._persist_tasks(email.id, result)
                logger.info(
                    "task_extraction_succeeded",
                    extra={
                        "email_id": str(email.id),
                        "task_count": result.extracted_task_count,
                    },
                )
            else:
                logger.debug(
                    "task_extraction_no_tasks_found",
                    extra={"email_id": str(email.id)},
                )

        except TaskExtractionFailureError as exc:
            logger.warning(
                "task_extraction_failed",
                extra={"email_id": str(email.id), "error": str(exc)},
            )
        except Exception as exc:
            logger.warning(
                "task_extraction_failed_unexpected",
                extra={"email_id": str(email.id), "error": str(exc)},
                exc_info=True,
            )

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

    async def _run_career_extraction(
        self,
        email: Email,
        summary_result: EmailSummaryResult | None,
    ) -> None:
        """Extract and persist job opportunities and interviews from the email.

        Skips whichever sub-type (jobs or interviews) already has records
        for this email to prevent duplicates across retries.

        Failures are logged as warnings and do not abort the pipeline.

        Args:
            email: The email entity to extract career data from.
            summary_result: The summary produced in stage 3, or ``None``.
        """
        try:
            has_job = await self._job_repo.email_has_job_opportunity(email.id)
            has_interview = await self._interview_repo.email_has_interview(email.id)

            if has_job and has_interview:
                logger.debug(
                    "career_extraction_skipped_records_exist",
                    extra={"email_id": str(email.id)},
                )
                return

            # Career extraction requires the raw email content to extract
            # structured fields (company, role, apply_link, salary, location).
            # Summaries collapse job alert emails to one-liners that lose all
            # structured data. Use body_text when available, fall back to the
            # summary only when no body content exists at all.
            body_context = (
                email.body_text
                if email.body_text
                else summary_result.summary
                if summary_result is not None
                else None
            )

            request = CareerExtractionRequest(
                subject=email.subject,
                sender=email.sender_email,
                body=body_context,
            )

            result: CareerExtractionResult = (
                self._career_extraction_service.extract_career(request)
            )

            if not has_job and result.job_opportunities:
                await self._persist_job_opportunities(email.id, result)

            if not has_interview and result.interviews:
                await self._persist_interviews(email.id, result)

            logger.info(
                "career_extraction_succeeded",
                extra={
                    "email_id": str(email.id),
                    "jobs": len(result.job_opportunities),
                    "interviews": len(result.interviews),
                },
            )

        except CareerExtractionFailureError as exc:
            logger.warning(
                "career_extraction_failed",
                extra={"email_id": str(email.id), "error": str(exc)},
            )
        except Exception as exc:
            logger.warning(
                "career_extraction_failed_unexpected",
                extra={"email_id": str(email.id), "error": str(exc)},
                exc_info=True,
            )

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