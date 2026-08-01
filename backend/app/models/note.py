"""
Note model for Personal Secretary agent.

Notes allow users to save memos, ideas, and snippets of information.
"""

from datetime import datetime
from typing import Optional, List
from uuid import uuid4

from sqlalchemy import (
    Column,
    String,
    Text,
    Integer,
    DateTime,
    Boolean,
    ForeignKey,
    JSON,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class Note(Base):
    """
    Note model for storing user notes and memos.

    Attributes:
        id: Unique identifier (UUID)
        user_id: Owner of the note
        title: Note title (optional)
        content: Note content (required)
        tags: List of tags for categorization
        is_pinned: Whether the note is pinned to top
        is_archived: Whether the note is archived
        session_id: Chat session where note was created (optional)
        created_at: Creation timestamp
        updated_at: Last update timestamp
        deleted_at: Soft delete timestamp
    """

    __tablename__ = "notes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Note content
    title = Column(String(255), nullable=True)
    content = Column(Text, nullable=False)

    # Organization
    tags = Column(JSON, default=list)
    is_pinned = Column(Boolean, default=False, nullable=False)
    is_archived = Column(Boolean, default=False, nullable=False)

    # Context
    session_id = Column(UUID(as_uuid=True), nullable=True, index=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="notes")

    def __repr__(self) -> str:
        return f"<Note(id={self.id}, title={self.title!r})>"

    @property
    def is_deleted(self) -> bool:
        """Check if note is soft deleted."""
        return self.deleted_at is not None

    def soft_delete(self) -> None:
        """Mark note as deleted."""
        self.deleted_at = datetime.utcnow()

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "user_id": self.user_id,
            "title": self.title,
            "content": self.content,
            "tags": self.tags or [],
            "is_pinned": self.is_pinned,
            "is_archived": self.is_archived,
            "session_id": str(self.session_id) if self.session_id else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
