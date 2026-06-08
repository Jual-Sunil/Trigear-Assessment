"""SQLAlchemy ORM model for the Email entity."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from infrastructure.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from infrastructure.database.models.email_classification_audit import (
        EmailClassificationAudit,
    )
    from infrastructure.database.models.interview import Interview
    from infrastructure.database.models.job_opportunity import JobOpportunity
    from infrastructure.database.models.processing_job import ProcessingJob
    from infrastructure.database.models.task import Task
    from infrastructure.database.models.user import User


class Email(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Represents a single Gmail message that has been synced and processed.

    Stores raw message content, AI-derived metadata (classification, priority,
    summary), and a pgvector embedding for semantic similarity search.
    """

    __tablename__ = "emails"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    gmail_message_id: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
    )
    gmail_thread_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    sender_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    sender_email: Mapped[str] = mapped_column(
        String(320),
        nullable=False,
    )
    subject: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    body_text: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    body_html: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    snippet: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    classification: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )
    confidence_score: Mapped[float | None] = mapped_column(
        Numeric(5, 4),
        nullable=True,
    )
    priority_score: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    is_action_required: Mapped[bool | None] = mapped_column(
        Boolean,
        nullable=True,
        default=False,
    )
    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(384),
        nullable=True,
    )

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------

    user: Mapped[User] = relationship(
        "User",
        back_populates="emails",
        lazy="select",
    )
    tasks: Mapped[list[Task]] = relationship(
        "Task",
        back_populates="email",
        cascade="all, delete-orphan",
        lazy="select",
    )
    job_opportunities: Mapped[list[JobOpportunity]] = relationship(
        "JobOpportunity",
        back_populates="email",
        cascade="all, delete-orphan",
        lazy="select",
    )
    interviews: Mapped[list[Interview]] = relationship(
        "Interview",
        back_populates="email",
        cascade="all, delete-orphan",
        lazy="select",
    )
    classification_audits: Mapped[list[EmailClassificationAudit]] = relationship(
        "EmailClassificationAudit",
        back_populates="email",
        cascade="all, delete-orphan",
        lazy="select",
    )
    processing_jobs: Mapped[list[ProcessingJob]] = relationship(
        "ProcessingJob",
        back_populates="email",
        cascade="all, delete-orphan",
        lazy="select",
    )

    __table_args__ = (
        Index("ix_emails_gmail_message_id", "gmail_message_id", unique=True),
        Index("ix_emails_gmail_thread_id", "gmail_thread_id"),
        Index("ix_emails_sender_email", "sender_email"),
        Index("ix_emails_classification", "classification"),
        Index("ix_emails_priority_score", "priority_score"),
        Index("ix_emails_received_at", "received_at"),
        Index("ix_emails_user_id", "user_id"),
    )

    def __repr__(self) -> str:
        """Return a debug representation of the Email instance."""
        return (
            f"<Email id={self.id} "
            f"gmail_message_id={self.gmail_message_id!r} "
            f"subject={self.subject!r}>"
        )
