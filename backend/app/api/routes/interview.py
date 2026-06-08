"""
Interview routes.

Exposes interview listing for the authenticated user.
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
from infrastructure.database.repositories.interview_repository import InterviewRepository

logger = get_logger(__name__)
router = APIRouter()


class InterviewResponse(BaseModel):
    """Interview representation for API responses."""

    id: UUID
    email_id: UUID
    company: Optional[str]
    role: Optional[str]
    interview_date: Optional[datetime]
    meeting_link: Optional[str]

    model_config = {"from_attributes": True}


class InterviewListResponse(BaseModel):
    """List response for interviews."""

    items: List[InterviewResponse]


@router.get(
    "",
    response_model=InterviewListResponse,
    summary="List interviews",
    description="Returns all interviews extracted from the current user's emails.",
)
async def list_interviews(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> InterviewListResponse:
    """
    Return all interviews belonging to the authenticated user.

    Args:
        current_user: The authenticated User ORM instance.
        db: Injected async database session.

    Returns:
        InterviewListResponse: List of interview records.
    """
    repo = InterviewRepository(db)
    interviews = await repo.list_for_user(user_id=current_user.id)
    return InterviewListResponse(items=[InterviewResponse.model_validate(i) for i in interviews])