"""Repository for Interview entity persistence operations."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.models.interview import Interview
from infrastructure.database.repositories.base import BaseRepository


class InterviewRepository(BaseRepository[Interview]):
    """Provides Interview-specific database query operations.

    Extends :class:`BaseRepository` with lookup and filtering methods used
    by the interviews dashboard and extraction deduplication logic.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialise the repository with an active async session.

        Args:
            session: An active async SQLAlchemy session for the current request.
        """
        super().__init__(session, Interview)

    async def get_by_email_id(self, email_id: uuid.UUID) -> list[Interview]:
        """Fetch all interviews linked to a specific email.

        Args:
            email_id: The UUID of the parent :class:`Email`.

        Returns:
            A list of :class:`Interview` instances for the email.
        """
        return await self.get_all(
            filters=[Interview.email_id == email_id],
            order_by=[Interview.interview_date.asc().nulls_last()],
            limit=100,
        )

    async def get_upcoming_by_user_emails(
        self,
        email_ids: list[uuid.UUID],
        *,
        offset: int = 0,
        limit: int = 20,
    ) -> list[Interview]:
        """Fetch upcoming interviews whose date is in the future.

        An interview is considered upcoming when its ``interview_date`` is either
        ``NULL`` (date not yet confirmed) or still in the future.

        Args:
            email_ids: List of email UUIDs to scope the query.
            offset: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            A list of upcoming :class:`Interview` instances ordered by date ascending.
        """
        if not email_ids:
            return []
        now = datetime.now(tz=timezone.utc)
        stmt = (
            select(Interview)
            .where(
                Interview.email_id.in_(email_ids),
                (Interview.interview_date.is_(None))
                | (Interview.interview_date > now),
            )
            .order_by(Interview.interview_date.asc().nulls_last())
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def count_upcoming_by_email_ids(self, email_ids: list[uuid.UUID]) -> int:
        """Return the count of upcoming interviews across a set of email IDs.

        Args:
            email_ids: List of email UUIDs to scope the query.

        Returns:
            Integer count of interviews whose date is in the future or unset.
        """
        if not email_ids:
            return 0
        now = datetime.now(tz=timezone.utc)
        return await self.count(
            filters=[
                Interview.email_id.in_(email_ids),
                (Interview.interview_date.is_(None))
                | (Interview.interview_date > now),
            ]
        )

    async def email_has_interview(self, email_id: uuid.UUID) -> bool:
        """Return True if at least one interview is linked to the given email.

        Used by the extraction service to prevent duplicate record creation.

        Args:
            email_id: The UUID of the parent :class:`Email`.

        Returns:
            ``True`` if one or more records exist for the email, otherwise ``False``.
        """
        return await self.exists([Interview.email_id == email_id])
    
    async def bulk_create(self, interviews: list[Interview]) -> list[Interview]:
        """Persist multiple Interview records in a single transaction.

        Each record is added to the session and flushed together so that
        all generated primary keys are available before the caller commits.

        Args:
            interviews: List of :class:`Interview` instances to persist.

        Returns:
            The same list with primary keys and timestamps populated.
        """
        for interview in interviews:
            self._session.add(interview)
        await self._session.flush()
        for interview in interviews:
            await self._session.refresh(interview)
        return interviews

    async def get_upcoming_interviews(
        self,
        email_ids: list[uuid.UUID],
        *,
        offset: int = 0,
        limit: int = 20,
    ) -> list[Interview]:
        """Fetch upcoming interviews whose date is in the future or unset.

        An interview is considered upcoming when its ``interview_date`` is either
        ``NULL`` (date not yet confirmed) or still in the future relative to
        the current UTC time.

        Args:
            email_ids: List of email UUIDs to scope the query.
            offset: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            A list of upcoming :class:`Interview` instances ordered by
            interview date ascending, with ``NULL`` dates sorted last.
        """
        if not email_ids:
            return []
        now = datetime.now(tz=timezone.utc)
        stmt = (
            select(Interview)
            .where(
                Interview.email_id.in_(email_ids),
                (Interview.interview_date.is_(None))
                | (Interview.interview_date > now),
            )
            .order_by(Interview.interview_date.asc().nulls_last())
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_next_interview(
        self,
        email_ids: list[uuid.UUID],
    ) -> Interview | None:
        """Return the single nearest upcoming interview across a set of email IDs.

        Selects the interview with the smallest ``interview_date`` that is
        strictly in the future.  Records with a ``NULL`` date are excluded
        because no concrete scheduling information is available for them.

        Args:
            email_ids: List of email UUIDs to scope the query.

        Returns:
            The nearest upcoming :class:`Interview`, or ``None`` if no
            scheduled future interview exists for the supplied email IDs.
        """
        if not email_ids:
            return None
        now = datetime.now(tz=timezone.utc)
        stmt = (
            select(Interview)
            .where(
                Interview.email_id.in_(email_ids),
                Interview.interview_date.is_not(None),
                Interview.interview_date > now,
            )
            .order_by(Interview.interview_date.asc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalars().first()

    async def get_by_user_emails(
        self,
        email_ids: list[uuid.UUID],
        *,
        offset: int = 0,
        limit: int = 20,
    ) -> list[Interview]:
        """Fetch interviews belonging to a set of email IDs owned by a user.

        Used by the dashboard to retrieve all interviews for a given user
        without a direct user_id foreign key on the Interview model.

        Args:
            email_ids: List of email UUIDs to scope the query.
            offset: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            A list of :class:`Interview` instances ordered by interview date ascending.
        """
        if not email_ids:
            return []
        stmt = (
            select(Interview)
            .where(Interview.email_id.in_(email_ids))
            .order_by(Interview.interview_date.asc().nulls_last())
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
    
    async def list_for_user(
        self,
        user_id: uuid.UUID,
        *,
        offset: int = 0,
        limit: int = 50,
    ) -> list[Interview]:
        """Fetch all interviews belonging to a user via their emails.

        Args:
            user_id: The UUID of the owning :class:`User`.
            offset: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            A list of :class:`Interview` instances ordered by interview date ascending.
        """
        from infrastructure.database.models.email import Email

        stmt = (
            select(Interview)
            .join(Email, Interview.email_id == Email.id)
            .where(Email.user_id == user_id)
            .order_by(Interview.interview_date.asc().nulls_last())
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())


    async def count_upcoming_for_user(self, user_id: uuid.UUID) -> int:
        """Return the count of upcoming interviews for a user via their emails.

        An interview is considered upcoming when its ``interview_date`` is
        either ``NULL`` or still in the future.

        Args:
            user_id: The UUID of the owning :class:`User`.

        Returns:
            Integer count of upcoming interviews.
        """
        from sqlalchemy import func
        from infrastructure.database.models.email import Email

        now = datetime.now(tz=timezone.utc)
        stmt = (
            select(func.count())
            .select_from(Interview)
            .join(Email, Interview.email_id == Email.id)
            .where(
                Email.user_id == user_id,
                (Interview.interview_date.is_(None)) | (Interview.interview_date > now),
            )
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()
