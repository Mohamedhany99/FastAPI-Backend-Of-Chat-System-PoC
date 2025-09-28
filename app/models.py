from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class User(Base):
    """User model with unique username and email."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    last_active: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    sent_messages: Mapped[list["Message"]] = relationship(
        back_populates="sender",
        primaryjoin="User.id==Message.sender_id",
        cascade="all,delete-orphan",
        lazy="raise",
    )
    received_messages: Mapped[list["Message"]] = relationship(
        back_populates="recipient",
        primaryjoin="User.id==Message.recipient_id",
        cascade="all,delete-orphan",
        lazy="raise",
    )


class Message(Base):
    """Direct 1:1 message."""

    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    sender_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    recipient_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    content: Mapped[str] = mapped_column(String(2000))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    sender: Mapped["User"] = relationship(foreign_keys=[sender_id], back_populates="sent_messages")
    recipient: Mapped["User"] = relationship(
        foreign_keys=[recipient_id], back_populates="received_messages"
    )


Index(
    "ix_messages_pair_created_at",
    Message.sender_id,
    Message.recipient_id,
    Message.created_at.desc(),
)
