"""
Email synchronization routes.

Exposes endpoints to trigger an incremental Gmail sync and to query
the current sync state for the authenticated user. The sync runs
directly via EmailSyncService without a background queue.
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps.auth import get_current_user
from api.deps.database import get_db
from core.logging import get_logger
from infrastructure.database.models.user import User
from infrastructure.database.repositories.email_sync_state_repository import (
    EmailSyncStateRepository,
)
from infrastructure.auth.auth_service import AuthService
from infrastructure.gmail.client import GmailClient
from infrastructure.gmail.sync_service import EmailSyncService
from infrastructure.database.repositories.email_repository import EmailRepository
from infrastructure.database.repositories.oauth_token_repository import OAuthTokenRepository
from infrastructure.database.repositories.user_repository import UserRepository
from infrastructure.database.repositories.task_repository import TaskRepository
from infrastructure.database.repositories.job_opportunity_repository import JobOpportunityRepository
from infrastructure.database.repositories.interview_repository import InterviewRepository
from application.services.email_processing_service import EmailProcessingService

logger = get_logger(__name__)
router = APIRouter()


class SyncTriggerResponse(BaseModel):
    """Response body returned when a sync completes or is initiated."""

    status: str
    user_id: str


class SyncStatusResponse(BaseModel):
    """Response body describing the current sync state for a user.

    Attributes:
        has_synced: True when at least one sync has completed for this user.
        history_id: The Gmail History API cursor from the last completed sync,
            or None if the user has never been synced.
        last_synced_at: UTC timestamp of the most recently completed sync,
            or None if no sync has run yet.
    """

    has_synced: bool
    history_id: Optional[str]
    last_synced_at: Optional[datetime]


@router.post(
    "",
    response_model=SyncTriggerResponse,
    status_code=status.HTTP_200_OK,
    summary="Trigger email synchronization",
    description=(
        "Runs an incremental Gmail sync for the authenticated user synchronously. "
        "Returns after the sync completes."
    ),
)
async def trigger_sync(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SyncTriggerResponse:
    """
    Execute a Gmail synchronization for the authenticated user.

    Runs the sync directly via EmailSyncService. The access token is
    obtained from the stored OAuth credentials and the sync strategy
    (full or incremental) is determined by the stored history cursor.

    Args:
        current_user: The authenticated User ORM instance.
        db: Injected async database session.

    Returns:
        SyncTriggerResponse: Confirms the sync has run with the user's ID.
    """
    
    logger.info(
        f"Starting sync for user_id={current_user.id} email={current_user.email}",
    )

    user_repo = UserRepository(db)
    token_repo = OAuthTokenRepository(db)
    logger.info("Creating AuthService")
    auth_service = AuthService(user_repo=user_repo, token_repo=token_repo)
    logger.info("Creating repositories")
    email_repo = EmailRepository(db)
    sync_state_repo = EmailSyncStateRepository(db)
    task_repo = TaskRepository(db)
    job_repo = JobOpportunityRepository(db)
    interview_repo = InterviewRepository(db)
    logger.info("Creating EmailProcessingService")
    email_processing_service = EmailProcessingService(
        email_repository=email_repo,
        task_repository=task_repo,
        job_opportunity_repository=job_repo,
        interview_repository=interview_repo,
        # AI services have default implementations (no args needed)
    )
    logger.info("Opening Gmail client")
    async with GmailClient(user_id=current_user.id, auth_service=auth_service) as gmail_client:
        sync_service = EmailSyncService(
            session=db,
            gmail_client=gmail_client,
            email_repository=email_repo,
            sync_state_repository=sync_state_repo,
            email_processing_service=email_processing_service,
        )
        logger.info("Starting EmailSyncService.sync()")
        await sync_service.sync(current_user.id)

    logger.info("Sync completed for user_id=%s", current_user.id)
    return SyncTriggerResponse(status="completed", user_id=str(current_user.id))


@router.get(
    "/status",
    response_model=SyncStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Get sync status",
    description=(
        "Returns the current Gmail synchronization state for the authenticated "
        "user, including the last completed sync timestamp and Gmail history cursor."
    ),
)
async def get_sync_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SyncStatusResponse:
    """
    Return the current sync state for the authenticated user.

    Reads the :class:`EmailSyncState` record for the user. If no record
    exists the user has never been synced, and all fields are returned as
    None with ``has_synced=False``.

    Args:
        current_user: The authenticated User ORM instance.
        db: Injected async database session.

    Returns:
        SyncStatusResponse: Current sync state including history cursor
            and last sync timestamp.
    """
    repo = EmailSyncStateRepository(db)
    state = await repo.get_by_user_id(current_user.id)

    if state is None:
        return SyncStatusResponse(
            has_synced=False,
            history_id=None,
            last_synced_at=None,
        )

    return SyncStatusResponse(
        has_synced=state.history_id is not None,
        history_id=state.history_id,
        last_synced_at=state.last_synced_at,
    )