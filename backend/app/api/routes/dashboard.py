"""
Dashboard routes.

Returns aggregated counts for the overview dashboard card set.
Counts are computed via targeted repository queries to avoid
loading full ORM objects for a summary-only endpoint.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps.auth import get_current_user
from api.deps.database import get_db
from core.logging import get_logger
from infrastructure.database.models.user import User
from infrastructure.database.repositories.email_repository import EmailRepository
from infrastructure.database.repositories.task_repository import TaskRepository
from infrastructure.database.repositories.job_opportunity_repository import JobOpportunityRepository
from infrastructure.database.repositories.interview_repository import InterviewRepository

logger = get_logger(__name__)
router = APIRouter()

_IMPORTANT_PRIORITY_THRESHOLD = 70
_PENDING_TASK_STATUS = "pending"


class DashboardResponse(BaseModel):
    """Aggregated counts for the dashboard overview."""

    total_emails: int
    important_emails: int
    pending_tasks: int
    upcoming_interviews: int
    active_jobs: int


@router.get(
    "",
    response_model=DashboardResponse,
    summary="Get dashboard overview",
    description="Returns aggregated counts for emails, tasks, interviews, and jobs.",
)
async def get_dashboard(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DashboardResponse:
    """
    Compute and return dashboard overview counts for the authenticated user.

    Executes four targeted count queries across emails, tasks, interviews,
    and job opportunities. All counts are scoped to the current user.

    Args:
        current_user: The authenticated User ORM instance.
        db: Injected async database session.

    Returns:
        DashboardResponse: Aggregated dashboard counts.
    """
    email_repo = EmailRepository(db)
    task_repo = TaskRepository(db)
    job_repo = JobOpportunityRepository(db)
    interview_repo = InterviewRepository(db)

    total_emails = await email_repo.count_for_user(user_id=current_user.id)
    important_emails = await email_repo.count_for_user(
        user_id=current_user.id,
        priority_min=_IMPORTANT_PRIORITY_THRESHOLD,
    )
    pending_tasks = await task_repo.count_for_user(
        user_id=current_user.id,
        status=_PENDING_TASK_STATUS,
    )
    upcoming_interviews = await interview_repo.count_upcoming_for_user(user_id=current_user.id)
    active_jobs = await job_repo.count_active_for_user(user_id=current_user.id)

    return DashboardResponse(
        total_emails=total_emails,
        important_emails=important_emails,
        pending_tasks=pending_tasks,
        upcoming_interviews=upcoming_interviews,
        active_jobs=active_jobs,
    )
