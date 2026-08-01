"""Chat session model for Personal Secretary agent conversations."""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class ChatSession(Base):
    """
    Chat session model for storing conversation sessions.

    Each session represents a conversation thread between a user and
    the Personal Secretary agent.

    Attributes:
        id: Unique UUID identifier for the session
        user_id: Foreign key to the user who owns this session
        title: Auto-generated title from first message (optional)
        is_active: Whether the session is active (soft delete support)
        created_at: When the session was created
        updated_at: When the session was last active
    """

    __tablename__ = "chat_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    messages = relationship(
        "ChatMessage",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="ChatMessage.created_at",
    )
    user = relationship("User", back_populates="chat_sessions")

    def __repr__(self) -> str:
        return (
            f"<ChatSession(id={self.id}, user_id={self.user_id}, title={self.title})>"
        )
