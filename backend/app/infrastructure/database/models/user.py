"""SQLAlchemy ORM model for the User entity."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from infrastructure.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from infrastructure.database.models.email import Email
    from infrastructure.database.models.email_sync_state import EmailSyncState
    from infrastructure.database.models.oauth_token import OAuthToken


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Represents an authenticated user of the platform.

    Each user authenticates via Google OAuth and owns a set of emails,
    OAuth tokens, and sync state records.
    """

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(
        String(320),
        unique=True,
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    google_id: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------

    oauth_tokens: Mapped[list[OAuthToken]] = relationship(
        "OAuthToken",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="select",
    )
    emails: Mapped[list[Email]] = relationship(
        "Email",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="select",
    )
    email_sync_states: Mapped[list[EmailSyncState]] = relationship(
        "EmailSyncState",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="select",
    )

    __table_args__ = (
        Index("ix_users_email", "email"),
        Index("ix_users_google_id", "google_id"),
    )

    def __repr__(self) -> str:
        """Return a debug representation of the User instance."""
        return f"<User id={self.id} email={self.email!r}>"
