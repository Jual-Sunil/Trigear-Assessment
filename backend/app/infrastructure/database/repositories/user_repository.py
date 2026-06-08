"""Repository for User entity persistence operations."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.models.user import User
from infrastructure.database.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """Provides User-specific database query operations.

    Extends :class:`BaseRepository` with lookup methods keyed on the
    unique ``email`` and ``google_id`` columns used during OAuth login
    and user identification flows.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialise the repository with an active async session.

        Args:
            session: An active async SQLAlchemy session for the current request.
        """
        super().__init__(session, User)

    async def get_by_email(self, email: str) -> User | None:
        """Fetch a user by their unique email address.

        Args:
            email: The email address to look up.

        Returns:
            The matching :class:`User` instance, or ``None`` if not found.
        """
        stmt = select(User).where(User.email == email)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_google_id(self, google_id: str) -> User | None:
        """Fetch a user by their unique Google OAuth subject identifier.

        Args:
            google_id: The Google ``sub`` claim from the ID token.

        Returns:
            The matching :class:`User` instance, or ``None`` if not found.
        """
        stmt = select(User).where(User.google_id == google_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def email_exists(self, email: str) -> bool:
        """Return True if a user record with the given email already exists.

        Args:
            email: The email address to check.

        Returns:
            ``True`` if a matching record exists, otherwise ``False``.
        """
        return await self.exists([User.email == email])

    async def google_id_exists(self, google_id: str) -> bool:
        """Return True if a user record with the given Google ID already exists.

        Args:
            google_id: The Google OAuth subject identifier to check.

        Returns:
            ``True`` if a matching record exists, otherwise ``False``.
        """
        return await self.exists([User.google_id == google_id])
