"""Repository for OAuthToken entity persistence operations."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy import delete as sa_delete
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.models.oauth_token import OAuthToken
from infrastructure.database.repositories.base import BaseRepository


class OAuthTokenRepository(BaseRepository[OAuthToken]):
    """Provides OAuthToken-specific database query operations.

    Extends :class:`BaseRepository` with lookup and expiry-checking methods
    needed by the authentication and token-refresh flows.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialise the repository with an active async session.

        Args:
            session: An active async SQLAlchemy session for the current request.
        """
        super().__init__(session, OAuthToken)

    async def get_by_user_id(self, user_id: uuid.UUID) -> OAuthToken | None:
        """Fetch the most recently created OAuth token for a given user.

        When multiple token records exist for a user (e.g. after re-authentication),
        the newest record is returned so callers always operate on the current token.

        Args:
            user_id: The UUID of the owning :class:`User`.

        Returns:
            The latest :class:`OAuthToken` for the user, or ``None`` if absent.
        """
        stmt = (
            select(OAuthToken)
            .where(OAuthToken.user_id == user_id)
            .order_by(OAuthToken.created_at.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_valid_token(self, user_id: uuid.UUID) -> OAuthToken | None:
        """Fetch an unexpired OAuth token for a given user.

        Returns the most recently created token whose ``expires_at`` is still
        in the future. Returns ``None`` if no valid token exists, signalling
        that a token refresh is required before making API calls.

        Args:
            user_id: The UUID of the owning :class:`User`.

        Returns:
            A non-expired :class:`OAuthToken`, or ``None`` if all tokens are expired.
        """
        now = datetime.now(tz=timezone.utc).replace(tzinfo=None)
        stmt = (
            select(OAuthToken)
            .where(
                OAuthToken.user_id == user_id,
                OAuthToken.expires_at > now,
            )
            .order_by(OAuthToken.created_at.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def delete_all_for_user(self, user_id: uuid.UUID) -> None:
        """Delete all OAuth token records belonging to a user.

        Used during re-authentication flows to clear stale tokens before
        persisting a freshly issued set.

        Args:
            user_id: The UUID of the owning :class:`User`.
        """
        stmt = sa_delete(OAuthToken).where(OAuthToken.user_id == user_id)
        await self._session.execute(stmt)
        await self._session.flush()
