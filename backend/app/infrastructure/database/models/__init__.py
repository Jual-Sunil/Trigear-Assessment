"""ORM model registry.

Importing this package ensures all SQLAlchemy models are registered with the
declarative ``Base`` metadata before Alembic or application code references
``Base.metadata`` for table creation or migration generation.
"""

from infrastructure.database.models.email import Email
from infrastructure.database.models.email_classification_audit import (
    EmailClassificationAudit,
)
from infrastructure.database.models.email_sync_state import EmailSyncState
from infrastructure.database.models.interview import Interview
from infrastructure.database.models.job_opportunity import JobOpportunity
from infrastructure.database.models.oauth_token import OAuthToken
from infrastructure.database.models.processing_job import ProcessingJob
from infrastructure.database.models.task import Task
from infrastructure.database.models.user import User

__all__ = [
    "Email",
    "EmailClassificationAudit",
    "EmailSyncState",
    "Interview",
    "JobOpportunity",
    "OAuthToken",
    "ProcessingJob",
    "Task",
    "User",
]
