"""
Email routes.

Exposes paginated email listing and individual email retrieval.
Supports filtering by classification and minimum priority score.
"""

from typing import List, Optional
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps.auth import get_current_user
from api.deps.database import get_db
from api.deps.pagination import PaginationParams, get_pagination
from core.logging import get_logger
from infrastructure.database.models.user import User
from infrastructure.database.repositories.email_repository import EmailRepository

logger = get_logger(__name__)
router = APIRouter()


class EmailSummary(BaseModel):
    """Lightweight email representation for list views."""

    id: UUID
    subject: Optional[str]
    sender_name: Optional[str]
    sender_email: str
    received_at: datetime
    classification: Optional[str]
    confidence_score: Optional[float]
    priority_score: Optional[int]
    summary: Optional[str]
    is_action_required: Optional[bool]
    snippet: Optional[str]

    model_config = {"from_attributes": True}


class EmailDetail(EmailSummary):
    """Full email representation including body content."""

    body_text: Optional[str]
    body_html: Optional[str]
    gmail_message_id: str
    gmail_thread_id: str

    model_config = {"from_attributes": True}


class EmailListResponse(BaseModel):
    """Paginated list response for emails."""

    items: List[EmailSummary]
    total: int
    page: int
    page_size: int


@router.get(
    "",
    response_model=EmailListResponse,
    summary="List emails",
    description="Returns a paginated list of emails for the authenticated user.",
)
async def list_emails(
    classification: Optional[str] = Query(default=None, description="Filter by classification label"),
    priority_min: Optional[int] = Query(default=None, ge=0, le=100, description="Minimum priority score"),
    pagination: PaginationParams = Depends(get_pagination),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EmailListResponse:
    """
    Return a paginated, optionally filtered list of emails for the current user.

    Args:
        classification: Optional classification label to filter by.
        priority_min: Optional minimum priority score threshold.
        pagination: Validated pagination parameters.
        current_user: The authenticated User ORM instance.
        db: Injected async database session.

    Returns:
        EmailListResponse: Paginated email list with total count.
    """
    repo = EmailRepository(db)
    items, total = await repo.list_for_user(
        user_id=current_user.id,
        classification=classification,
        priority_min=priority_min,
        offset=pagination.offset,
        limit=pagination.page_size,
    )
    return EmailListResponse(
        items=[EmailSummary.model_validate(e) for e in items],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.get(
    "/{email_id}",
    response_model=EmailDetail,
    summary="Get email detail",
    description="Returns full detail for a single email.",
)
async def get_email(
    email_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EmailDetail:
    """
    Return full detail for a single email owned by the current user.

    Args:
        email_id: UUID of the email to retrieve.
        current_user: The authenticated User ORM instance.
        db: Injected async database session.

    Returns:
        EmailDetail: Complete email record.

    Raises:
        HTTPException: 404 if the email does not exist or belongs to another user.
    """
    repo = EmailRepository(db)
    email = await repo.get_for_user(email_id=email_id, user_id=current_user.id)

    if email is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Email not found")

    return EmailDetail.model_validate(email)
