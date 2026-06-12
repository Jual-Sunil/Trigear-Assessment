"""Celery tasks for email synchronisation.

Offloads the heavy AI-processing pipeline to a background worker so the
HTTP sync endpoint can return immediately.  The task builds its own
async session and service graph since it runs outside the FastAPI request
lifecycle.
"""

from __future__ import annotations

import asyncio
import logging
import uuid

from celery_app import celery

logger = logging.getLogger(__name__)


async def _run_sync(user_id_str: str) -> dict:
    """Async implementation for the Celery sync task.

    Creates a fresh database session, assembles the full service graph,
    and delegates to :class:`EmailSyncService`.

    Args:
        user_id_str: Stringified UUID of the user whose mailbox to sync.

    Returns:
        A plain-dict summary suitable for JSON serialisation.
    """
    from application.services.email_processing_service import EmailProcessingService
    from infrastructure.auth.auth_service import AuthService
    from infrastructure.database.repositories.email_repository import EmailRepository
    from infrastructure.database.repositories.email_sync_state_repository import (
        EmailSyncStateRepository,
    )
    from infrastructure.database.repositories.interview_repository import (
        InterviewRepository,
    )
    from infrastructure.database.repositories.job_opportunity_repository import (
        JobOpportunityRepository,
    )
    from infrastructure.database.repositories.oauth_token_repository import (
        OAuthTokenRepository,
    )
    from infrastructure.database.repositories.task_repository import TaskRepository
    from infrastructure.database.repositories.user_repository import UserRepository
    from infrastructure.database.session import get_session_factory
    from infrastructure.gmail.client import GmailClient
    from infrastructure.gmail.sync_service import EmailSyncService

    user_id = uuid.UUID(user_id_str)
    factory = get_session_factory()

    async with factory() as session:
        try:
            user_repo = UserRepository(session)
            token_repo = OAuthTokenRepository(session)
            auth_service = AuthService(user_repo=user_repo, token_repo=token_repo)
            email_repo = EmailRepository(session)
            sync_state_repo = EmailSyncStateRepository(session)
            task_repo = TaskRepository(session)
            job_repo = JobOpportunityRepository(session)
            interview_repo = InterviewRepository(session)

            from infrastructure.ai.llm.provider_factory import LLMProviderFactory
            from infrastructure.ai.summarization.summarization_service import (
                SummarizationService,
            )
            from infrastructure.ai.task_extraction.task_extraction_service import (
                TaskExtractionService,
            )
            from infrastructure.ai.career_extraction.career_extraction_service import (
                CareerExtractionService,
            )

            shared_provider = LLMProviderFactory().create_provider()
            email_processing_service = EmailProcessingService(
                email_repository=email_repo,
                task_repository=task_repo,
                job_opportunity_repository=job_repo,
                interview_repository=interview_repo,
                summarization_service=SummarizationService(provider=shared_provider),
                task_extraction_service=TaskExtractionService(provider=shared_provider),
                career_extraction_service=CareerExtractionService(provider=shared_provider),
            )

            async with GmailClient(
                user_id=user_id, auth_service=auth_service
            ) as gmail_client:
                sync_service = EmailSyncService(
                    session=session,
                    gmail_client=gmail_client,
                    email_repository=email_repo,
                    sync_state_repository=sync_state_repo,
                    email_processing_service=email_processing_service,
                )
                result = await sync_service.sync(user_id)

            await session.commit()

            return {
                "user_id": str(result.user_id),
                "synced": result.synced,
                "skipped": result.skipped,
                "failed": result.failed,
                "history_id": result.history_id,
                "full_sync": result.full_sync,
            }
        except Exception:
            await session.rollback()
            raise


@celery.task(
    name="tasks.sync_emails",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    acks_late=True,
)
def sync_emails(self, user_id: str) -> dict:  # type: ignore[override]
    """Celery task: run email sync for a user in the background.

    Args:
        user_id: Stringified UUID of the user.

    Returns:
        A plain-dict summary of the sync result.
    """
    logger.info("celery_sync_started", extra={"user_id": user_id})
    try:
        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(_run_sync(user_id))
        finally:
            loop.close()
        logger.info("celery_sync_completed", extra={"user_id": user_id, **result})
        return result
    except Exception as exc:
        logger.exception("celery_sync_failed", extra={"user_id": user_id})
        raise self.retry(exc=exc) from exc
