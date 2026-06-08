"""Async SQLAlchemy engine and session factory.

Creates a single engine and session factory per process.
All database access must go through :func:`get_session`.
"""

from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from core.config import get_settings
from core.logging import get_logger

logger = get_logger(__name__)

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def _build_engine_kwargs(settings: Any) -> dict[str, Any]:
    """Build SQLAlchemy engine keyword arguments from settings.

    Uses NullPool in test environments to avoid connection leakage
    between test cases.

    Args:
        settings: Application settings instance.

    Returns:
        Dictionary of keyword arguments for :func:`create_async_engine`.
    """
    kwargs: dict[str, Any] = {
        "echo": settings.database_echo,
        "pool_pre_ping": True,
    }
    if settings.environment == "development" and settings.debug:
        # NullPool is safe for tests and single-worker dev; avoids pool
        # exhaustion during rapid restarts.
        kwargs["poolclass"] = NullPool
    else:
        kwargs["pool_size"] = settings.database_pool_size
        kwargs["max_overflow"] = settings.database_max_overflow
        kwargs["pool_timeout"] = settings.database_pool_timeout
        kwargs["pool_recycle"] = 1800  # recycle connections every 30 min
    return kwargs


def get_engine() -> AsyncEngine:
    """Return the application-wide async SQLAlchemy engine.

    Creates the engine on first call and caches it for subsequent calls.

    Returns:
        The singleton :class:`AsyncEngine` instance.
    """
    global _engine  # noqa: PLW0603
    if _engine is None:
        settings = get_settings()
        kwargs = _build_engine_kwargs(settings)
        _engine = create_async_engine(str(settings.database_url), **kwargs)
        logger.info("database_engine_created", pool_size=settings.database_pool_size)
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return the application-wide async session factory.

    Creates the factory on first call using the singleton engine.

    Returns:
        The singleton :class:`async_sessionmaker` instance.
    """
    global _session_factory  # noqa: PLW0603
    if _session_factory is None:
        engine = get_engine()
        _session_factory = async_sessionmaker(
            bind=engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
        logger.info("session_factory_created")
    return _session_factory


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield a transactional database session.

    Intended for use as a FastAPI dependency.  Commits on success,
    rolls back on any exception, and always closes the session.

    Yields:
        An :class:`AsyncSession` bound to the current request.

    Raises:
        Exception: Re-raises any exception after rolling back the transaction.
    """
    factory = get_session_factory()

    async with factory() as session:
        try:
            yield session

            print("COMMITTING DATABASE TRANSACTION")
            await session.commit()
            print("DATABASE COMMIT COMPLETE")

        except Exception:
            print("ROLLING BACK DATABASE TRANSACTION")
            await session.rollback()
            raise


async def dispose_engine() -> None:
    """Dispose the engine connection pool.

    Should be called during application shutdown to release all database
    connections cleanly.
    """
    global _engine
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        logger.info("database_engine_disposed")
