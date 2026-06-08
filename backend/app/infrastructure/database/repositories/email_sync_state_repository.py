"""Repository for EmailSyncState entity persistence operations."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.models.email_sync_state import EmailSyncState
from infrastructure.database.repositories.base import BaseRepository


class EmailSyncStateRepository(BaseRepository[EmailSyncState]):
    """Provides EmailSyncState-specific database query operations.

    Extends :class:`BaseRepository` with lookup and upsert methods used by
    the Gmail incremental sync pipeline to track per-user history cursors.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialise the repository with an active async session.

        Args:
            session: An active async SQLAlchemy session for the current request.
        """
        super().__init__(session, EmailSyncState)

    async def get_by_user_id(self, user_id: uuid.UUID) -> EmailSyncState | None:
        """Fetch the sync state record for a given user.

        Args:
            user_id: The UUID of the owning :class:`User`.

        Returns:
            The :class:`EmailSyncState` for the user, or ``None`` if no record
            exists yet (i.e. the user has never been synced).
        """
        stmt = select(EmailSyncState).where(EmailSyncState.user_id == user_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_or_create_for_user(self, user_id: uuid.UUID) -> EmailSyncState:
        """Return the existing sync state for a user, creating one if absent.

        This is the preferred entry point for the sync pipeline: it guarantees
        a :class:`EmailSyncState` row exists before any history cursor is read
        or written, without requiring the caller to handle the ``None`` case.

        Args:
            user_id: The UUID of the owning :class:`User`.

        Returns:
            The existing or newly created :class:`EmailSyncState` instance.
        """
        existing = await self.get_by_user_id(user_id)
        if existing is not None:
            return existing

        new_state = EmailSyncState(
            user_id=user_id,
            history_id=None,
            last_synced_at=None,
        )
        return await self.create(new_state)

    async def update_history_id(
        self,
        user_id: uuid.UUID,
        history_id: str,
    ) -> EmailSyncState:
        """Persist a new Gmail History API cursor for a user.

        Called at the end of each successful sync run so the next incremental
        fetch starts from the correct position.

        Args:
            user_id: The UUID of the owning :class:`User`.
            history_id: The new history cursor string returned by the Gmail API.

        Returns:
            The updated :class:`EmailSyncState` instance.
        """
        state = await self.get_or_create_for_user(user_id)
        return await self.update(state, {"history_id": history_id})

    async def update_last_synced_at(
        self,
        user_id: uuid.UUID,
        synced_at: datetime | None = None,
    ) -> EmailSyncState:
        """Record the wall-clock time of the most recent completed sync.

        Args:
            user_id: The UUID of the owning :class:`User`.
            synced_at: Explicit timestamp to store.  Defaults to the current
                UTC time when not supplied.

        Returns:
            The updated :class:`EmailSyncState` instance.
        """
        timestamp = synced_at if synced_at is not None else datetime.now(tz=timezone.utc)
        state = await self.get_or_create_for_user(user_id)
        return await self.update(state, {"last_synced_at": timestamp})
