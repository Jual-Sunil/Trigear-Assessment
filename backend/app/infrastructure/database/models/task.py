"""SQLAlchemy ORM model for the Task entity."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.constants import TASK_STATUS_PENDING
from infrastructure.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from infrastructure.database.models.email import Email


class Task(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Represents an actionable task extracted from an email.

    Tasks are created by the TaskExtractionService and linked to the source
    email. Status transitions are managed by the application layer.
    """

    __tablename__ = "tasks"

    email_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("emails.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    priority: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=TASK_STATUS_PENDING,
        server_default=TASK_STATUS_PENDING,
    )
    due_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------

    email: Mapped[Email] = relationship(
        "Email",
        back_populates="tasks",
        lazy="select",
    )

    __table_args__ = (
        Index("ix_tasks_email_id", "email_id"),
        Index("ix_tasks_status", "status"),
        Index("ix_tasks_due_date", "due_date"),
    )

    def __repr__(self) -> str:
        """Return a debug representation of the Task instance."""
        return f"<Task id={self.id} title={self.title!r} status={self.status!r}>"
