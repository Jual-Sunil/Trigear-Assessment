"""SQLAlchemy ORM model for the OAuthToken entity."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from infrastructure.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from infrastructure.database.models.user import User


class OAuthToken(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Stores encrypted OAuth2 tokens for a user's Google account.

    Access and refresh tokens are encrypted at rest using the application
    encryption key before being persisted. The ``expires_at`` timestamp
    is used to determine when a token refresh is required.
    """

    __tablename__ = "oauth_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    encrypted_access_token: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    encrypted_refresh_token: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        nullable=False,
    )

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------

    user: Mapped[User] = relationship(
        "User",
        back_populates="oauth_tokens",
        lazy="select",
    )

    __table_args__ = (Index("ix_oauth_tokens_user_id", "user_id"),)

    def __repr__(self) -> str:
        """Return a debug representation of the OAuthToken instance."""
        return f"<OAuthToken id={self.id} user_id={self.user_id}>"
