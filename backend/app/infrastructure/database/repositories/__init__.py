"""Concrete repository implementations.

Importing this package exposes all repository classes for use in the
dependency injection layer. Each repository receives an :class:`AsyncSession`
at construction time and is scoped to the current request.
"""

from infrastructure.database.repositories.base import BaseRepository
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

__all__ = [
    "BaseRepository",
    "EmailRepository",
    "InterviewRepository",
    "JobOpportunityRepository",
    "OAuthTokenRepository",
    "ProcessingJobRepository",
    "TaskRepository",
    "UserRepository",
]
