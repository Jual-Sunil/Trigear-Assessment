"""
Job opportunity routes.

Exposes job opportunity listing for the authenticated user.
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps.auth import get_current_user
from api.deps.database import get_db
from core.logging import get_logger
from infrastructure.database.models.user import User
from infrastructure.database.repositories.job_opportunity_repository import JobOpportunityRepository

logger = get_logger(__name__)
router = APIRouter()


class JobResponse(BaseModel):
    """Job opportunity representation for API responses."""

    id: UUID
    email_id: UUID
    company: Optional[str]
    role: Optional[str]
    location: Optional[str]
    salary: Optional[str]
    apply_link: Optional[str]
    deadline: Optional[datetime]

    model_config = {"from_attributes": True}


class JobListResponse(BaseModel):
    """List response for job opportunities."""

    items: List[JobResponse]


@router.get(
    "",
    response_model=JobListResponse,
    summary="List job opportunities",
    description="Returns all job opportunities extracted from the current user's emails.",
)
async def list_jobs(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> JobListResponse:
    """
    Return all job opportunities belonging to the authenticated user.

    Args:
        current_user: The authenticated User ORM instance.
        db: Injected async database session.

    Returns:
        JobListResponse: List of job opportunity records.
    """
    repo = JobOpportunityRepository(db)
    jobs = await repo.list_for_user(user_id=current_user.id)
    return JobListResponse(items=[JobResponse.model_validate(j) for j in jobs])