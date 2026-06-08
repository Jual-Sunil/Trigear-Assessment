"""SQLAlchemy ORM model for the JobOpportunity entity."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from infrastructure.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from infrastructure.database.models.email import Email


class JobOpportunity(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Represents a job opportunity extracted from an email.

    Populated by the JobExtractionService when an email is classified as
    a Job Opportunity. Stores structured metadata to power the Jobs dashboard.
    """

    __tablename__ = "job_opportunities"

    email_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("emails.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    company: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    role: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    location: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    salary: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    apply_link: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    deadline: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------

    email: Mapped[Email] = relationship(
        "Email",
        back_populates="job_opportunities",
        lazy="select",
    )

    __table_args__ = (
        Index("ix_job_opportunities_email_id", "email_id"),
        Index("ix_job_opportunities_company", "company"),
        Index("ix_job_opportunities_role", "role"),
        Index("ix_job_opportunities_deadline", "deadline"),
    )

    def __repr__(self) -> str:
        """Return a debug representation of the JobOpportunity instance."""
        return (
            f"<JobOpportunity id={self.id} "
            f"company={self.company!r} "
            f"role={self.role!r}>"
        )
