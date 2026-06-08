"""Repository for Email entity persistence operations."""

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from infrastructure.database.models.email import Email
from infrastructure.database.repositories.base import BaseRepository


class EmailRepository(BaseRepository[Email]):
    """Provides Email-specific database query operations.

    Extends :class:`BaseRepository` with lookup methods used by sync
    deduplication, classification, priority scoring, and dashboard queries.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialise the repository with an active async session.

        Args:
            session: An active async SQLAlchemy session for the current request.
        """
        super().__init__(session, Email)

    async def get_by_gmail_message_id(self, gmail_message_id: str) -> Email | None:
        """Fetch an email by its unique Gmail message identifier.

        Used during sync to detect duplicates before inserting a new record.

        Args:
            gmail_message_id: The Gmail API message ID string.

        Returns:
            The matching :class:`Email` instance, or ``None`` if not found.
        """
        stmt = select(Email).where(Email.gmail_message_id == gmail_message_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def gmail_message_exists(self, gmail_message_id: str) -> bool:
        """Return True if an email with the given Gmail message ID already exists.

        Provides a lightweight existence check during incremental sync without
        loading the full model instance.

        Args:
            gmail_message_id: The Gmail API message ID string.

        Returns:
            ``True`` if a matching record exists, otherwise ``False``.
        """
        return await self.exists([Email.gmail_message_id == gmail_message_id])

    async def get_by_user_id(
        self,
        user_id: uuid.UUID,
        *,
        offset: int = 0,
        limit: int = 20,
    ) -> list[Email]:
        """Fetch a paginated list of emails belonging to a user.

        Results are ordered newest-first by ``received_at``.

        Args:
            user_id: The UUID of the owning :class:`User`.
            offset: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            A list of :class:`Email` instances.
        """
        return await self.get_all(
            offset=offset,
            limit=limit,
            filters=[Email.user_id == user_id],
            order_by=[Email.received_at.desc()],
        )

    async def get_by_user_and_classification(
        self,
        user_id: uuid.UUID,
        classification: str,
        *,
        offset: int = 0,
        limit: int = 20,
    ) -> list[Email]:
        """Fetch emails for a user filtered by classification category.

        Args:
            user_id: The UUID of the owning :class:`User`.
            classification: The classification label to filter on (e.g. ``"Interview"``).
            offset: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            A list of matching :class:`Email` instances ordered newest-first.
        """
        return await self.get_all(
            offset=offset,
            limit=limit,
            filters=[
                Email.user_id == user_id,
                Email.classification == classification,
            ],
            order_by=[Email.received_at.desc()],
        )

    async def get_high_priority(
        self,
        user_id: uuid.UUID,
        min_priority: int,
        *,
        offset: int = 0,
        limit: int = 20,
    ) -> list[Email]:
        """Fetch emails for a user whose priority score meets or exceeds a threshold.

        Args:
            user_id: The UUID of the owning :class:`User`.
            min_priority: Minimum ``priority_score`` value (inclusive).
            offset: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            A list of :class:`Email` instances ordered by descending priority score.
        """
        return await self.get_all(
            offset=offset,
            limit=limit,
            filters=[
                Email.user_id == user_id,
                Email.priority_score >= min_priority,
            ],
            order_by=[Email.priority_score.desc()],
        )

    async def get_action_required(
        self,
        user_id: uuid.UUID,
        *,
        offset: int = 0,
        limit: int = 20,
    ) -> list[Email]:
        """Fetch emails for a user that require action.

        Args:
            user_id: The UUID of the owning :class:`User`.
            offset: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            A list of :class:`Email` instances ordered by descending priority score.
        """
        return await self.get_all(
            offset=offset,
            limit=limit,
            filters=[
                Email.user_id == user_id,
                Email.is_action_required.is_(True),
            ],
            order_by=[Email.priority_score.desc(), Email.received_at.desc()],
        )

    async def get_unclassified(
        self,
        *,
        offset: int = 0,
        limit: int = 20,
    ) -> list[Email]:
        """Fetch emails that have not yet been classified.

        Used by the classification pipeline to retrieve a batch of emails
        pending classification.

        Args:
            offset: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            A list of :class:`Email` instances with no ``classification`` value.
        """
        return await self.get_all(
            offset=offset,
            limit=limit,
            filters=[Email.classification.is_(None)],
            order_by=[Email.received_at.asc()],
        )

    async def get_by_classification(
        self,
        classification: str,
        *,
        offset: int = 0,
        limit: int = 20,
    ) -> list[Email]:
        """Fetch emails filtered by classification category.

        Args:
            classification: The classification label to filter on.
            offset: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            A list of matching :class:`Email` instances ordered newest-first.
        """
        return await self.get_all(
            offset=offset,
            limit=limit,
            filters=[Email.classification == classification],
            order_by=[Email.received_at.desc()],
        )

    async def update_classification(
        self,
        gmail_message_id: str,
        classification: str,
        confidence_score: float,
    ) -> Email:
        """Update an email's classification and confidence score.

        Args:
            gmail_message_id: The Gmail API message ID of the email to update.
            classification: The classification label to persist.
            confidence_score: The confidence score to persist.

        Returns:
            The updated :class:`Email` instance.

        Raises:
            ValueError: If no email exists for the given Gmail message ID.
        """
        email = await self.get_by_gmail_message_id(gmail_message_id)
        if email is None:
            raise ValueError(f"Email with gmail_message_id '{gmail_message_id}' was not found.")

        return await self.update(
            email,
            {
                "classification": classification,
                "confidence_score": confidence_score,
            },
        )

    async def update_confidence_score(
        self,
        gmail_message_id: str,
        confidence_score: float,
    ) -> Email:
        """Update only an email's confidence score.

        Args:
            gmail_message_id: The Gmail API message ID of the email to update.
            confidence_score: The confidence score to persist.

        Returns:
            The updated :class:`Email` instance.

        Raises:
            ValueError: If no email exists for the given Gmail message ID.
        """
        email = await self.get_by_gmail_message_id(gmail_message_id)
        if email is None:
            raise ValueError(f"Email with gmail_message_id '{gmail_message_id}' was not found.")

        return await self.update(
            email,
            {
                "confidence_score": confidence_score,
            },
        )

    async def update_priority_score(
        self,
        gmail_message_id: str,
        priority_score: int,
    ) -> Email:
        """Update only an email's priority score.

        Args:
            gmail_message_id: The Gmail API message ID of the email to update.
            priority_score: The priority score to persist.

        Returns:
            The updated :class:`Email` instance.

        Raises:
            ValueError: If no email exists for the given Gmail message ID.
        """
        email = await self.get_by_gmail_message_id(gmail_message_id)
        if email is None:
            raise ValueError(f"Email with gmail_message_id '{gmail_message_id}' was not found.")

        return await self.update(
            email,
            {
                "priority_score": priority_score,
            },
        )
    
    async def update_summary(
        self,
        gmail_message_id: str,
        summary: str,
    ) -> Email:
        """Update only an email's summary text.

        Args:
            gmail_message_id: The Gmail API message ID of the email to update.
            summary: The generated summary text to persist.

        Returns:
            The updated :class:`Email` instance.

        Raises:
            ValueError: If no email exists for the given Gmail message ID.
        """
        email = await self.get_by_gmail_message_id(gmail_message_id)
        if email is None:
            raise ValueError(f"Email with gmail_message_id '{gmail_message_id}' was not found.")

        return await self.update(
            email,
            {
                "summary": summary,
            },
        )

    async def get_without_embedding(
        self,
        *,
        offset: int = 0,
        limit: int = 20,
    ) -> list[Email]:
        """Fetch emails that have no stored pgvector embedding.

        Used by the embedding pipeline to identify records requiring vectorisation.

        Args:
            offset: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            A list of :class:`Email` instances with a ``None`` embedding.
        """
        return await self.get_all(
            offset=offset,
            limit=limit,
            filters=[Email.embedding.is_(None)],
            order_by=[Email.received_at.asc()],
        )
    
    async def get_without_summary(
        self,
        *,
        offset: int = 0,
        limit: int = 20,
    ) -> list[Email]:
        """Fetch emails that have not yet had a summary generated.

        Used by the summarisation pipeline to retrieve a batch of emails
        pending summary generation.

        Args:
            offset: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            A list of :class:`Email` instances with a ``None`` summary,
            ordered oldest-first by ``received_at``.
        """
        return await self.get_all(
            offset=offset,
            limit=limit,
            filters=[Email.summary.is_(None)],
            order_by=[Email.received_at.asc()],
        )

    async def count_by_user(self, user_id: uuid.UUID) -> int:
        """Return the total number of emails belonging to a user.

        Args:
            user_id: The UUID of the owning :class:`User`.

        Returns:
            Integer count of the user's emails.
        """
        return await self.count(filters=[Email.user_id == user_id])

    async def count_high_priority_by_user(
        self, user_id: uuid.UUID, min_priority: int
    ) -> int:
        """Return the count of high-priority emails for a user.

        Args:
            user_id: The UUID of the owning :class:`User`.
            min_priority: Minimum ``priority_score`` value (inclusive).

        Returns:
            Integer count of matching emails.
        """
        return await self.count(
            filters=[
                Email.user_id == user_id,
                Email.priority_score >= min_priority,
            ]
        )

    async def count_for_user(
        self,
        user_id: uuid.UUID,
        *,
        priority_min: Optional[int] = None,
    ) -> int:
        """Return the count of emails for a user, optionally filtered by minimum priority score.

        Args:
            user_id: The UUID of the owning :class:`User`.
            priority_min: Optional minimum ``priority_score`` (inclusive).

        Returns:
            Integer count of matching emails.
        """
        filters = [Email.user_id == user_id]
        if priority_min is not None:
            filters.append(Email.priority_score >= priority_min)
        return await self.count(filters=filters)
    
    async def list_for_user(
        self,
        user_id: uuid.UUID,
        *,
        classification: Optional[str] = None,
        priority_min: Optional[int] = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[Email], int]:
        """Fetch paginated emails for a user with optional filters.

        Args:
            user_id: The UUID of the owning :class:`User`.
            classification: Optional classification label to filter by.
            priority_min: Optional minimum priority score (inclusive).
            offset: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            A tuple (items, total_count) where items are :class:`Email` instances
            ordered by received_at descending.
        """
        filters = [Email.user_id == user_id]
        if classification is not None:
            filters.append(Email.classification == classification)
        if priority_min is not None:
            filters.append(Email.priority_score >= priority_min)

        items = await self.get_all(
            offset=offset,
            limit=limit,
            filters=filters,
            order_by=[Email.received_at.desc()],
        )
        total = await self.count(filters=filters)
        return items, total

    async def get_for_user(
        self,
        email_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Email | None:
        stmt = select(Email).where(
            Email.id == email_id,
            Email.user_id == user_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()