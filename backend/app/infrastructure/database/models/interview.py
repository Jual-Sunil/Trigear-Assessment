"""SQLAlchemy ORM model for the Interview entity."""

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


class Interview(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Represents an interview event extracted from an email.

    Populated by the InterviewExtractionService when an email is classified
    as an Interview. Provides structured data for the Interviews dashboard.
    """

    __tablename__ = "interviews"

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
    interview_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    meeting_link: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------

    email: Mapped[Email] = relationship(
        "Email",
        back_populates="interviews",
        lazy="select",
    )

    __table_args__ = (
        Index("ix_interviews_email_id", "email_id"),
        Index("ix_interviews_company", "company"),
        Index("ix_interviews_interview_date", "interview_date"),
    )

    def __repr__(self) -> str:
        """Return a debug representation of the Interview instance."""
        return (
            f"<Interview id={self.id} "
            f"company={self.company!r} "
            f"interview_date={self.interview_date!r}>"
        )
