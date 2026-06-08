"""SQLAlchemy ORM model for the ProcessingJob entity."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.constants import JOB_STATUS_PENDING
from infrastructure.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from infrastructure.database.models.email import Email


class ProcessingJob(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Tracks the execution state of a single pipeline stage for an email.

    One ProcessingJob record exists per email per pipeline stage. The Celery
    worker updates ``status``, ``error_message``, and ``completed_at`` as
    it progresses through the processing pipeline.
    """

    __tablename__ = "processing_jobs"

    email_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("emails.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    pipeline_stage: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=JOB_STATUS_PENDING,
        server_default=JOB_STATUS_PENDING,
    )
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------

    email: Mapped[Email] = relationship(
        "Email",
        back_populates="processing_jobs",
        lazy="select",
    )

    __table_args__ = (
        Index("ix_processing_jobs_email_id", "email_id"),
        Index("ix_processing_jobs_status", "status"),
        Index("ix_processing_jobs_pipeline_stage", "pipeline_stage"),
    )

    def __repr__(self) -> str:
        """Return a debug representation of the ProcessingJob instance."""
        return (
            f"<ProcessingJob id={self.id} "
            f"email_id={self.email_id} "
            f"stage={self.pipeline_stage!r} "
            f"status={self.status!r}>"
        )
