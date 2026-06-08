"""
Repository dependencies.

Factory functions that construct repository instances bound to the
request-scoped database session. Consumed via FastAPI dependency injection.
"""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps.database import get_db
from infrastructure.database.repositories.email_sync_state_repository import (
    EmailSyncStateRepository,
)
from infrastructure.database.repositories.email_repository import EmailRepository
from infrastructure.database.repositories.interview_repository import (
    InterviewRepository,
)
from infrastructure.database.repositories.job_opportunity_repository import (
    JobOpportunityRepository,
)
from infrastructure.database.repositories.oauth_token_repository import (
    OAuthTokenRepository,
)
from infrastructure.database.repositories.processing_job_repository import (
    ProcessingJobRepository,
)
from infrastructure.database.repositories.task_repository import TaskRepository
from infrastructure.database.repositories.user_repository import UserRepository


def get_user_repository(db: AsyncSession = Depends(get_db)) -> UserRepository:
    """
    Construct a UserRepository bound to the current request session.

    Args:
        db: Injected async database session.

    Returns:
        UserRepository: Repository instance for User operations.
    """
    return UserRepository(db)


def get_oauth_token_repository(
    db: AsyncSession = Depends(get_db),
) -> OAuthTokenRepository:
    """
    Construct an OAuthTokenRepository bound to the current request session.

    Args:
        db: Injected async database session.

    Returns:
        OAuthTokenRepository: Repository instance for OAuthToken operations.
    """
    return OAuthTokenRepository(db)


def get_email_sync_state_repository(
    db: AsyncSession = Depends(get_db),
) -> EmailSyncStateRepository:
    """
    Construct an EmailSyncStateRepository bound to the current request session.

    Args:
        db: Injected async database session.

    Returns:
        EmailSyncStateRepository: Repository instance for EmailSyncState operations.
    """
    return EmailSyncStateRepository(db)


def get_email_repository(db: AsyncSession = Depends(get_db)) -> EmailRepository:
    """
    Construct an EmailRepository bound to the current request session.

    Args:
        db: Injected async database session.

    Returns:
        EmailRepository: Repository instance for Email operations.
    """
    return EmailRepository(db)


def get_task_repository(db: AsyncSession = Depends(get_db)) -> TaskRepository:
    """
    Construct a TaskRepository bound to the current request session.

    Args:
        db: Injected async database session.

    Returns:
        TaskRepository: Repository instance for Task operations.
    """
    return TaskRepository(db)


def get_job_repository(
    db: AsyncSession = Depends(get_db),
) -> JobOpportunityRepository:
    """
    Construct a JobOpportunityRepository bound to the current request session.

    Args:
        db: Injected async database session.

    Returns:
        JobOpportunityRepository: Repository instance for JobOpportunity operations.
    """
    return JobOpportunityRepository(db)


def get_interview_repository(
    db: AsyncSession = Depends(get_db),
) -> InterviewRepository:
    """
    Construct an InterviewRepository bound to the current request session.

    Args:
        db: Injected async database session.

    Returns:
        InterviewRepository: Repository instance for Interview operations.
    """
    return InterviewRepository(db)


def get_processing_job_repository(
    db: AsyncSession = Depends(get_db),
) -> ProcessingJobRepository:
    """
    Construct a ProcessingJobRepository bound to the current request session.

    Args:
        db: Injected async database session.

    Returns:
        ProcessingJobRepository: Repository instance for ProcessingJob operations.
    """
    return ProcessingJobRepository(db)
