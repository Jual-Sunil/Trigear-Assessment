"""
Task routes.

Exposes task listing and status update operations for the
authenticated user's extracted email tasks.
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps.auth import get_current_user
from api.deps.database import get_db
from core.logging import get_logger
from infrastructure.database.models.user import User
from infrastructure.database.repositories.task_repository import TaskRepository

logger = get_logger(__name__)
router = APIRouter()


class TaskResponse(BaseModel):
    """Task representation for API responses."""

    id: UUID
    email_id: UUID
    title: Optional[str]
    description: Optional[str]
    priority: Optional[int]
    status: Optional[str]
    due_date: Optional[datetime]

    model_config = {"from_attributes": True}


class TaskListResponse(BaseModel):
    """List response for tasks."""

    items: List[TaskResponse]


class TaskUpdateRequest(BaseModel):
    """Request body for partial task updates."""

    status: Optional[str] = None
    priority: Optional[int] = None
    due_date: Optional[datetime] = None


class TaskUpdateResponse(BaseModel):
    """Response confirming a task update."""

    success: bool


@router.get(
    "",
    response_model=TaskListResponse,
    summary="List tasks",
    description="Returns all tasks extracted from the current user's emails.",
)
async def list_tasks(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TaskListResponse:
    """
    Return all tasks belonging to the authenticated user.

    Args:
        current_user: The authenticated User ORM instance.
        db: Injected async database session.

    Returns:
        TaskListResponse: List of task records.
    """
    repo = TaskRepository(db)
    tasks = await repo.list_for_user(user_id=current_user.id)
    return TaskListResponse(items=[TaskResponse.model_validate(t) for t in tasks])


@router.patch(
    "/{task_id}",
    response_model=TaskUpdateResponse,
    summary="Update task",
    description="Partially updates a task's status, priority, or due date.",
)
async def update_task(
    task_id: UUID,
    payload: TaskUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TaskUpdateResponse:
    """
    Partially update a task owned by the current user.

    Only non-None fields in the request body are applied. Ownership is
    verified by joining through the email's user_id.

    Args:
        task_id: UUID of the task to update.
        payload: Fields to update on the task.
        current_user: The authenticated User ORM instance.
        db: Injected async database session.

    Returns:
        TaskUpdateResponse: Confirms the update was applied.

    Raises:
        HTTPException: 404 if the task does not exist or belongs to another user.
    """
    repo = TaskRepository(db)
    task = await repo.get_for_user(task_id=task_id, user_id=current_user.id)

    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    updates = payload.model_dump(exclude_none=True)
    await repo.update(task_id=task_id, updates=updates)
    return TaskUpdateResponse(success=True)