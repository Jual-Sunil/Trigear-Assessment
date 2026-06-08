"""SQLAlchemy ORM model for the EmailSyncState entity."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from infrastructure.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from infrastructure.database.models.user import User


class EmailSyncState(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Tracks incremental Gmail synchronisation state per user.

    The ``history_id`` field stores the Gmail History API cursor returned
    from the most recent sync operation, enabling incremental fetches that
    avoid re-processing previously seen messages.
    """

    __tablename__ = "email_sync_states"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    history_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    last_synced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------

    user: Mapped[User] = relationship(
        "User",
        back_populates="email_sync_states",
        lazy="select",
    )

    __table_args__ = (Index("ix_email_sync_states_user_id", "user_id"),)

    def __repr__(self) -> str:
        """Return a debug representation of the EmailSyncState instance."""
        return (
            f"<EmailSyncState id={self.id} "
            f"user_id={self.user_id} "
            f"history_id={self.history_id!r}>"
        )
