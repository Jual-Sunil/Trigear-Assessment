"""Repository for ProcessingJob entity persistence operations."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.models.processing_job import ProcessingJob
from infrastructure.database.repositories.base import BaseRepository


class ProcessingJobRepository(BaseRepository[ProcessingJob]):
    """Provides ProcessingJob-specific database query operations.

    Extends :class:`BaseRepository` with lookup methods used by the Celery
    pipeline to manage per-stage execution state for each email.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialise the repository with an active async session.

        Args:
            session: An active async SQLAlchemy session for the current request.
        """
        super().__init__(session, ProcessingJob)

    async def get_by_email_id(self, email_id: uuid.UUID) -> list[ProcessingJob]:
        """Fetch all processing job records linked to a specific email.

        Args:
            email_id: The UUID of the parent :class:`Email`.

        Returns:
            A list of :class:`ProcessingJob` instances for the email.
        """
        return await self.get_all(
            filters=[ProcessingJob.email_id == email_id],
            order_by=[ProcessingJob.created_at.asc()],
            limit=50,
        )

    async def get_by_email_and_stage(
        self,
        email_id: uuid.UUID,
        pipeline_stage: str,
    ) -> ProcessingJob | None:
        """Fetch the processing job for a specific email and pipeline stage.

        Each email should have at most one job record per stage. Returns the
        record if it exists, or ``None`` if the stage has not been created yet.

        Args:
            email_id: The UUID of the parent :class:`Email`.
            pipeline_stage: The pipeline stage identifier (e.g. ``"classification"``).

        Returns:
            The matching :class:`ProcessingJob`, or ``None`` if not found.
        """
        stmt = select(ProcessingJob).where(
            ProcessingJob.email_id == email_id,
            ProcessingJob.pipeline_stage == pipeline_stage,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_status(
        self,
        status: str,
        *,
        offset: int = 0,
        limit: int = 20,
    ) -> list[ProcessingJob]:
        """Fetch a paginated list of processing jobs filtered by status.

        Args:
            status: The job status to filter on (e.g. ``"pending"``).
            offset: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            A list of matching :class:`ProcessingJob` instances.
        """
        return await self.get_all(
            offset=offset,
            limit=limit,
            filters=[ProcessingJob.status == status],
            order_by=[ProcessingJob.created_at.asc()],
        )

    async def get_failed(
        self,
        *,
        offset: int = 0,
        limit: int = 20,
    ) -> list[ProcessingJob]:
        """Fetch a paginated list of processing jobs in a failed state.

        Args:
            offset: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            A list of failed :class:`ProcessingJob` instances.
        """
        return await self.get_by_status("failed", offset=offset, limit=limit)

    async def stage_completed(self, email_id: uuid.UUID, pipeline_stage: str) -> bool:
        """Return True if a pipeline stage has completed successfully for an email.

        Used by the pipeline to skip re-processing stages that have already run.

        Args:
            email_id: The UUID of the parent :class:`Email`.
            pipeline_stage: The pipeline stage identifier to check.

        Returns:
            ``True`` if a completed record exists for the stage, otherwise ``False``.
        """
        return await self.exists(
            [
                ProcessingJob.email_id == email_id,
                ProcessingJob.pipeline_stage == pipeline_stage,
                ProcessingJob.status == "completed",
            ]
        )

    async def mark_completed(
        self, email_id: uuid.UUID, pipeline_stage: str
    ) -> ProcessingJob | None:
        """Set the status of a pipeline stage job to completed.

        Fetches the existing record for the given email and stage, updates its
        ``status`` to ``"completed"`` and sets ``completed_at`` to the current
        UTC timestamp.

        Args:
            email_id: The UUID of the parent :class:`Email`.
            pipeline_stage: The pipeline stage identifier to mark as completed.

        Returns:
            The updated :class:`ProcessingJob` instance, or ``None`` if not found.
        """
        job = await self.get_by_email_and_stage(email_id, pipeline_stage)
        if job is None:
            return None
        return await self.update(
            job,
            {
                "status": "completed",
                "completed_at": datetime.now(tz=timezone.utc),
            },
        )

    async def mark_failed(
        self,
        email_id: uuid.UUID,
        pipeline_stage: str,
        error_message: str,
    ) -> ProcessingJob | None:
        """Set the status of a pipeline stage job to failed.

        Fetches the existing record for the given email and stage, updates its
        ``status`` to ``"failed"``, records the error message, and sets
        ``completed_at`` to the current UTC timestamp.

        Args:
            email_id: The UUID of the parent :class:`Email`.
            pipeline_stage: The pipeline stage identifier to mark as failed.
            error_message: The error detail to persist on the record.

        Returns:
            The updated :class:`ProcessingJob` instance, or ``None`` if not found.
        """
        job = await self.get_by_email_and_stage(email_id, pipeline_stage)
        if job is None:
            return None
        return await self.update(
            job,
            {
                "status": "failed",
                "error_message": error_message,
                "completed_at": datetime.now(tz=timezone.utc),
            },
        )
