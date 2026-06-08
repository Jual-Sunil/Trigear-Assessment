"""Repository for JobOpportunity entity persistence operations."""

import uuid
from datetime import datetime, timezone, timedelta


from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.models.job_opportunity import JobOpportunity
from infrastructure.database.repositories.base import BaseRepository


class JobOpportunityRepository(BaseRepository[JobOpportunity]):
    """Provides JobOpportunity-specific database query operations.

    Extends :class:`BaseRepository` with lookup and filtering methods used
    by the jobs dashboard and extraction deduplication logic.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialise the repository with an active async session.

        Args:
            session: An active async SQLAlchemy session for the current request.
        """
        super().__init__(session, JobOpportunity)

    async def get_by_email_id(self, email_id: uuid.UUID) -> list[JobOpportunity]:
        """Fetch all job opportunities linked to a specific email.

        Args:
            email_id: The UUID of the parent :class:`Email`.

        Returns:
            A list of :class:`JobOpportunity` instances for the email.
        """
        return await self.get_all(
            filters=[JobOpportunity.email_id == email_id],
            order_by=[JobOpportunity.deadline.asc().nulls_last()],
            limit=100,
        )

    async def get_by_user_emails(
        self,
        email_ids: list[uuid.UUID],
        *,
        offset: int = 0,
        limit: int = 20,
    ) -> list[JobOpportunity]:
        """Fetch job opportunities belonging to a set of email IDs owned by a user.

        Used by the dashboard to retrieve all job opportunities for a given
        user without a direct user_id foreign key on the JobOpportunity model.

        Args:
            email_ids: List of email UUIDs to scope the query.
            offset: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            A list of :class:`JobOpportunity` instances ordered by deadline ascending.
        """
        if not email_ids:
            return []
        stmt = (
            select(JobOpportunity)
            .where(JobOpportunity.email_id.in_(email_ids))
            .order_by(JobOpportunity.deadline.asc().nulls_last())
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_active_by_user_emails(
        self,
        email_ids: list[uuid.UUID],
        *,
        offset: int = 0,
        limit: int = 20,
    ) -> list[JobOpportunity]:
        """Fetch job opportunities whose deadline has not yet passed.

        A job opportunity is considered active when its ``deadline`` is either
        ``NULL`` (no deadline set) or still in the future.

        Args:
            email_ids: List of email UUIDs to scope the query.
            offset: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            A list of active :class:`JobOpportunity` instances.
        """
        if not email_ids:
            return []
        now = datetime.now(tz=timezone.utc)
        stmt = (
            select(JobOpportunity)
            .where(
                JobOpportunity.email_id.in_(email_ids),
                (JobOpportunity.deadline.is_(None)) | (JobOpportunity.deadline > now),
            )
            .order_by(JobOpportunity.deadline.asc().nulls_last())
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def count_active_by_email_ids(self, email_ids: list[uuid.UUID]) -> int:
        """Return the count of active job opportunities across a set of email IDs.

        Args:
            email_ids: List of email UUIDs to scope the query.

        Returns:
            Integer count of opportunities whose deadline is in the future or unset.
        """
        if not email_ids:
            return 0
        now = datetime.now(tz=timezone.utc)
        return await self.count(
            filters=[
                JobOpportunity.email_id.in_(email_ids),
                (JobOpportunity.deadline.is_(None)) | (JobOpportunity.deadline > now),
            ]
        )

    async def bulk_create(self, instances: list[JobOpportunity]) -> list[JobOpportunity]:
        """Persist multiple JobOpportunity instances efficiently.

        Args:
            instances: List of not-yet-persisted :class:`JobOpportunity` objects.

        Returns:
            The same instances after flush/refresh.
        """
        if not instances:
            return []
        self._session.add_all(instances)
        await self._session.flush()
        for instance in instances:
            await self._session.refresh(instance)
        return instances

    async def get_active_opportunities(
        self,
        *,
        email_ids: list[uuid.UUID],
        offset: int = 0,
        limit: int = 20,
    ) -> list[JobOpportunity]:
        """Fetch job opportunities whose deadline has not yet passed.

        A job opportunity is considered active when its ``deadline`` is either
        ``NULL`` (no deadline set) or still in the future.

        Args:
            email_ids: List of email UUIDs to scope the query.
            offset: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            A list of active :class:`JobOpportunity` instances.
        """
        if not email_ids:
            return []
        now = datetime.now(tz=timezone.utc)
        stmt = (
            select(JobOpportunity)
            .where(
                JobOpportunity.email_id.in_(email_ids),
                (JobOpportunity.deadline.is_(None))
                | (JobOpportunity.deadline > now),
            )
            .order_by(JobOpportunity.deadline.asc().nulls_last())
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_upcoming_deadlines(
        self,
        *,
        email_ids: list[uuid.UUID],
        days: int = 14,
        offset: int = 0,
        limit: int = 20,
    ) -> list[JobOpportunity]:
        """Fetch job opportunities with deadlines upcoming within a time window.

        Deadline-based jobs are considered upcoming when:
        - deadline is not NULL
        - deadline is within [now, now + days]

        Args:
            email_ids: List of email UUIDs to scope the query.
            days: Number of days ahead to consider as upcoming.
            offset: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            A list of job opportunities with upcoming deadlines ordered by deadline.
        """
        if not email_ids:
            return []
        
        now = datetime.now(tz=timezone.utc)
        upper = now + timedelta(days=days)

        stmt = (
            select(JobOpportunity)
            .where(
                JobOpportunity.email_id.in_(email_ids),
                JobOpportunity.deadline.is_not(None),
                JobOpportunity.deadline >= now,
                JobOpportunity.deadline <= upper,
            )
            .order_by(JobOpportunity.deadline.asc())
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def email_has_job_opportunity(self, email_id: uuid.UUID) -> bool:
        """Return True if at least one job opportunity is linked to the given email.

        Used by the extraction service to prevent duplicate record creation.

        Args:
            email_id: The UUID of the parent :class:`Email`.

        Returns:
            ``True`` if one or more records exist for the email, otherwise ``False``.
        """
        return await self.exists([JobOpportunity.email_id == email_id])
    
    async def list_for_user(
        self,
        user_id: uuid.UUID,
        *,
        offset: int = 0,
        limit: int = 50,
    ) -> list[JobOpportunity]:
        """Fetch all job opportunities belonging to a user via their emails.

        Args:
            user_id: The UUID of the owning :class:`User`.
            offset: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            A list of :class:`JobOpportunity` instances ordered by deadline ascending.
        """
        from infrastructure.database.models.email import Email

        stmt = (
            select(JobOpportunity)
            .join(Email, JobOpportunity.email_id == Email.id)
            .where(Email.user_id == user_id)
            .order_by(JobOpportunity.deadline.asc().nulls_last())
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())


    async def count_active_for_user(self, user_id: uuid.UUID) -> int:
        """Return the count of active job opportunities for a user via their emails.

        A job opportunity is active when its ``deadline`` is ``NULL`` or in the future.

        Args:
            user_id: The UUID of the owning :class:`User`.

        Returns:
            Integer count of active job opportunities.
        """
        from sqlalchemy import func
        from infrastructure.database.models.email import Email

        now = datetime.now(tz=timezone.utc)
        stmt = (
            select(func.count())
            .select_from(JobOpportunity)
            .join(Email, JobOpportunity.email_id == Email.id)
            .where(
                Email.user_id == user_id,
                (JobOpportunity.deadline.is_(None)) | (JobOpportunity.deadline > now),
            )
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()

