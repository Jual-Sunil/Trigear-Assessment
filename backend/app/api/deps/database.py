"""
Database session dependency.

Provides an async SQLAlchemy session scoped to the lifetime of a single
HTTP request. The session is committed on success and rolled back on error.
"""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.session import get_session_factory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Yield an async database session for the duration of a request.

    Commits the session on clean exit and rolls back on any exception,
    ensuring transactional integrity per request.

    Yields:
        AsyncSession: An active SQLAlchemy async session.

    Raises:
        Exception: Re-raises any exception after rolling back the session.
    """
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
