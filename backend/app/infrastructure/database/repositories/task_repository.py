"""Repository for Task entity persistence operations."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from infrastructure.database.models.task import Task
from infrastructure.database.repositories.base import BaseRepository


class TaskRepository(BaseRepository[Task]):
    """Provides Task-specific database query operations.

    Extends :class:`BaseRepository` with lookup and filtering methods used
    by the task dashboard and extraction deduplication logic.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialise the repository with an active async session.

        Args:
            session: An active async SQLAlchemy session for the current request.
        """
        super().__init__(session, Task)

    async def get_by_email_id(self, email_id: uuid.UUID) -> list[Task]:
        """Fetch all tasks linked to a specific email.

        Args:
            email_id: The UUID of the parent :class:`Email`.

        Returns:
            A list of :class:`Task` instances associated with the email.
        """
        return await self.get_all(
            filters=[Task.email_id == email_id],
            order_by=[Task.due_date.asc().nulls_last()],
            limit=100,
        )

    async def get_by_status(
        self,
        status: str,
        *,
        offset: int = 0,
        limit: int = 20,
    ) -> list[Task]:
        """Fetch a paginated list of tasks filtered by status.

        Args:
            status: The task status value to filter on (e.g. ``"pending"``).
            offset: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            A list of matching :class:`Task` instances ordered by due date ascending.
        """
        return await self.get_all(
            offset=offset,
            limit=limit,
            filters=[Task.status == status],
            order_by=[Task.due_date.asc().nulls_last()],
        )

    async def get_by_user_emails(
        self,
        email_ids: list[uuid.UUID],
        *,
        offset: int = 0,
        limit: int = 20,
    ) -> list[Task]:
        """Fetch tasks belonging to a set of email IDs owned by a user.

        Used by the dashboard to retrieve all tasks for a given user without
        a direct user_id foreign key on the Task model.

        Args:
            email_ids: List of email UUIDs to scope the query.
            offset: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            A list of :class:`Task` instances ordered by due date ascending.
        """
        if not email_ids:
            return []
        stmt = (
            select(Task)
            .where(Task.email_id.in_(email_ids))
            .order_by(Task.due_date.asc().nulls_last())
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def count_pending_by_email_ids(self, email_ids: list[uuid.UUID]) -> int:
        """Return the count of pending tasks across a set of email IDs.

        Args:
            email_ids: List of email UUIDs to scope the query.

        Returns:
            Integer count of tasks with status ``"pending"``.
        """
        if not email_ids:
            return 0
        return await self.count(
            filters=[
                Task.email_id.in_(email_ids),
                Task.status == "pending",
            ]
        )

    async def bulk_create_tasks(
        self,
        tasks: list[Task],
    ) -> None:
        """Bulk insert tasks.

        Args:
            tasks: List of :class:`Task` instances to persist.

        Returns:
            None
        """
        if not tasks:
            return
        self._session.add_all(tasks)
        await self._session.flush()

    async def get_pending_tasks(
        self,
        *,
        offset: int = 0,
        limit: int = 20,
    ) -> list[Task]:
        """Fetch pending tasks.

        Args:
            offset: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            A list of pending :class:`Task` instances ordered by due date.
        """
        return await self.get_all(
            offset=offset,
            limit=limit,
            filters=[Task.status == "pending"],
            order_by=[Task.due_date.asc().nulls_last()],
        )

    async def get_high_priority_tasks(
        self,
        *,
        min_priority: int,
        offset: int = 0,
        limit: int = 20,
    ) -> list[Task]:
        """Fetch high-priority tasks.

        Args:
            min_priority: Minimum priority threshold (inclusive).
            offset: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            A list of tasks meeting the priority threshold.
        """
        return await self.get_all(
            offset=offset,
            limit=limit,
            filters=[
                Task.status == "pending",
                Task.priority >= min_priority,
            ],
            order_by=[Task.priority.desc(), Task.due_date.asc().nulls_last()],
        )

    async def get_due_tasks(
        self,
        *,
        now: "object",
        offset: int = 0,
        limit: int = 20,
    ) -> list[Task]:
        """Fetch due tasks.

        A due task is a pending task with a due_date less than or equal to
        ``now``.

        Args:
            now: A datetime used as the due-date cutoff.
            offset: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            A list of matching :class:`Task` instances ordered by due date.
        """
        return await self.get_all(
            offset=offset,
            limit=limit,
            filters=[
                Task.status == "pending",
                Task.due_date.is_not(None),
                Task.due_date <= now,
            ],
            order_by=[Task.due_date.asc().nulls_last()],
        )

    async def email_has_tasks(self, email_id: uuid.UUID) -> bool:
        """Return True if at least one task is linked to the given email.


        Used by the extraction service to prevent duplicate task creation.

        Args:
            email_id: The UUID of the parent :class:`Email`.

        Returns:
            ``True`` if one or more tasks exist for the email, otherwise ``False``.
        """
        return await self.exists([Task.email_id == email_id])
    
    async def count_for_user(
        self,
        user_id: uuid.UUID,
        *,
        status: Optional[str] = None,
    ) -> int:
        """Return the count of tasks belonging to a user, optionally filtered by status.

        Args:
            user_id: The UUID of the owning :class:`User`.
            status: Optional status value to filter on.

        Returns:
            Integer count of matching tasks.
        """
        from sqlalchemy import select, func
        from infrastructure.database.models.email import Email

        stmt = (
            select(func.count())
            .select_from(Task)
            .join(Email, Task.email_id == Email.id)
            .where(Email.user_id == user_id)
        )
        if status is not None:
            stmt = stmt.where(Task.status == status)
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def list_for_user(
        self,
        user_id: uuid.UUID,
        *,
        offset: int = 0,
        limit: int = 50,
    ) -> list[Task]:
        """Fetch all tasks belonging to a user via their emails.

        Args:
            user_id: The UUID of the owning :class:`User`.
            offset: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            A list of :class:`Task` instances ordered by due date ascending.
        """
        from infrastructure.database.models.email import Email

        stmt = (
            select(Task)
            .join(Email, Task.email_id == Email.id)
            .where(Email.user_id == user_id)
            .order_by(Task.due_date.asc().nulls_last())
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())


    async def get_for_user(
        self,
        task_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Task | None:
        """Fetch a single task by ID, verifying ownership through the parent email.

        Args:
            task_id: The UUID of the :class:`Task` to fetch.
            user_id: The UUID of the owning :class:`User`.

        Returns:
            The :class:`Task` if found and owned by the user, otherwise ``None``.
        """
        from infrastructure.database.models.email import Email

        stmt = (
            select(Task)
            .join(Email, Task.email_id == Email.id)
            .where(Task.id == task_id, Email.user_id == user_id)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()