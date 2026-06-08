"""Generic async base repository providing common CRUD operations.

All concrete repositories inherit from :class:`BaseRepository` and receive
a SQLAlchemy :class:`AsyncSession` through dependency injection.
"""

import uuid
from typing import Any, Generic, TypeVar

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    """Generic repository that wraps an :class:`AsyncSession`.

    Provides ``get``, ``get_all``, ``create``, ``update``, and ``delete``
    operations that are shared across all entity repositories.

    Type Parameters:
        ModelT: The SQLAlchemy ORM model class managed by this repository.
    """

    def __init__(self, session: AsyncSession, model: type[ModelT]) -> None:
        """Initialise the repository with an active session and model class.

        Args:
            session: An active async SQLAlchemy session for the current request.
            model: The ORM model class this repository manages.
        """
        self._session = session
        self._model = model

    async def get_by_id(self, record_id: uuid.UUID) -> ModelT | None:
        """Fetch a single record by primary key.

        Args:
            record_id: The UUID primary key of the record.

        Returns:
            The ORM instance if found, otherwise ``None``.
        """
        result = await self._session.get(self._model, record_id)
        return result

    async def get_all(
        self,
        *,
        offset: int = 0,
        limit: int = 20,
        filters: list[Any] | None = None,
        order_by: list[Any] | None = None,
    ) -> list[ModelT]:
        """Fetch a paginated list of records with optional filtering and ordering.

        Args:
            offset: Number of records to skip (for pagination).
            limit: Maximum number of records to return.
            filters: Optional list of SQLAlchemy column expressions to apply as
                WHERE clauses.
            order_by: Optional list of SQLAlchemy column expressions for ORDER BY.

        Returns:
            A list of ORM model instances.
        """
        stmt = select(self._model)
        if filters:
            stmt = stmt.where(*filters)
        if order_by:
            stmt = stmt.order_by(*order_by)
        stmt = stmt.offset(offset).limit(limit)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def count(self, filters: list[Any] | None = None) -> int:
        """Return the total count of records matching optional filters.

        Args:
            filters: Optional list of SQLAlchemy column expressions to apply as
                WHERE clauses.

        Returns:
            Integer count of matching rows.
        """
        stmt = select(func.count()).select_from(self._model)
        if filters:
            stmt = stmt.where(*filters)
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def create(self, instance: ModelT) -> ModelT:
        """Persist a new model instance.

        Args:
            instance: A not-yet-persisted ORM model instance.

        Returns:
            The persisted instance with database-assigned fields populated.
        """
        self._session.add(instance)
        await self._session.flush()
        await self._session.refresh(instance)
        return instance

    async def update(self, instance: ModelT, data: dict[str, Any]) -> ModelT:
        """Apply a dictionary of field updates to an existing model instance.

        Args:
            instance: The ORM instance to update.
            data: Dictionary mapping column names to new values.

        Returns:
            The updated instance after flushing changes to the database.
        """
        for field, value in data.items():
            setattr(instance, field, value)
        self._session.add(instance)
        await self._session.flush()
        await self._session.refresh(instance)
        return instance

    async def delete(self, instance: ModelT) -> None:
        """Delete an existing model instance.

        Args:
            instance: The ORM instance to remove from the database.
        """
        await self._session.delete(instance)
        await self._session.flush()

    async def exists(self, filters: list[Any]) -> bool:
        """Return True if at least one record matches the given filters.

        Args:
            filters: List of SQLAlchemy column expressions to apply as WHERE clauses.

        Returns:
            ``True`` if a matching record exists, otherwise ``False``.
        """
        stmt = select(func.count()).select_from(self._model).where(*filters)
        result = await self._session.execute(stmt)
        return result.scalar_one() > 0
