"""FastAPI dependency providers.

All injectable dependencies are defined here and consumed via
``Depends()`` in route handlers.  This module is the single source of
truth for dependency wiring across the application.
"""

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import Settings, get_settings
from infrastructure.database.session import get_session

# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------


def settings_dependency() -> Settings:
    """Return the application settings singleton.

    Returns:
        The cached :class:`Settings` instance.
    """
    return get_settings()


SettingsDep = Annotated[Settings, Depends(settings_dependency)]

# ---------------------------------------------------------------------------
# Database Session
# ---------------------------------------------------------------------------


async def db_session_dependency(
    session: AsyncSession = Depends(get_session),
) -> AsyncGenerator[AsyncSession, None]:
    """Yield the active async database session for the current request.

    Args:
        session: Provided by the :func:`get_session` generator dependency.

    Yields:
        An :class:`AsyncSession` scoped to the current request lifecycle.
    """
    yield session


DbSessionDep = Annotated[AsyncSession, Depends(db_session_dependency)]
