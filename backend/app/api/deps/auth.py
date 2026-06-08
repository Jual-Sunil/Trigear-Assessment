"""
Authentication dependencies.

Resolves the currently authenticated user from the session cookie or
Authorization header. Provides both a required and an optional variant
for use across protected and semi-protected endpoints.
"""

from typing import Optional
from uuid import UUID

from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps.database import get_db
from core.logging import get_logger
from infrastructure.database.repositories.user_repository import UserRepository
from infrastructure.database.models.user import User

logger = get_logger(__name__)

_SESSION_COOKIE = "session_user_id"


async def get_current_user(
    session_user_id: Optional[str] = Cookie(default=None, alias=_SESSION_COOKIE),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Resolve and return the authenticated User from the session cookie.

    Reads the user ID stored in the session cookie, queries the database,
    and returns the User ORM instance. Raises HTTP 401 when the session is
    absent or the user cannot be found.

    Args:
        session_user_id: User UUID read from the session cookie.
        db: Injected async database session.

    Returns:
        User: The authenticated user ORM instance.

    Raises:
        HTTPException: 401 when the session is missing or the user is not found.
    """
    if not session_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    try:
        user_id = UUID(session_user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session",
        )

    repo = UserRepository(db)
    user = await repo.get_by_id(user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return user


async def get_optional_current_user(
    session_user_id: Optional[str] = Cookie(default=None, alias=_SESSION_COOKIE),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """
    Resolve the authenticated user if a valid session exists, otherwise None.

    Intended for endpoints that behave differently for authenticated vs
    anonymous users without blocking unauthenticated requests outright.

    Args:
        session_user_id: User UUID read from the session cookie.
        db: Injected async database session.

    Returns:
        Optional[User]: The User ORM instance, or None if unauthenticated.
    """
    if not session_user_id:
        return None

    try:
        user_id = UUID(session_user_id)
    except ValueError:
        return None

    repo = UserRepository(db)
    return await repo.get_by_id(user_id)
