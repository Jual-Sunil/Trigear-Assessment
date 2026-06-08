"""SQLAlchemy ORM model for the EmailClassificationAudit entity."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from infrastructure.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from infrastructure.database.models.email import Email


class EmailClassificationAudit(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Records each classification attempt made against an email.

    Captures the method used (embedding similarity, zero-shot BART, or LLM
    fallback), the resulting category, and the confidence score. This audit
    trail supports debugging and model performance analysis.
    """

    __tablename__ = "email_classification_audits"

    email_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("emails.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    classification_method: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    classification_result: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    confidence_score: Mapped[float | None] = mapped_column(
        Numeric(5, 4),
        nullable=True,
    )

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------

    email: Mapped[Email] = relationship(
        "Email",
        back_populates="classification_audits",
        lazy="select",
    )

    __table_args__ = (
        Index("ix_email_classification_audits_email_id", "email_id"),
    )

    def __repr__(self) -> str:
        """Return a debug representation of the EmailClassificationAudit instance."""
        return (
            f"<EmailClassificationAudit id={self.id} "
            f"email_id={self.email_id} "
            f"method={self.classification_method!r} "
            f"result={self.classification_result!r}>"
        )
