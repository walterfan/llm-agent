"""
Task model for Personal Secretary agent.

Tasks allow users to manage their to-do items with priorities and due dates.
"""

from datetime import datetime
from enum import Enum
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


class TaskPriority(str, Enum):
    """Task priority levels."""

    low = "low"
    medium = "medium"
    high = "high"
    urgent = "urgent"


class TaskStatus(str, Enum):
    """Task status options."""

    pending = "pending"
    in_progress = "in_progress"
    completed = "completed"
    cancelled = "cancelled"


class Task(Base):
    """
    Task model for managing user to-do items.

    Attributes:
        id: Unique identifier (UUID)
        user_id: Owner of the task
        title: Task title (required)
        description: Detailed description (optional)
        priority: Task priority level
        status: Current task status
        due_date: When the task is due (optional)
        completed_at: When the task was completed
        tags: List of tags for categorization
        session_id: Chat session where task was created (optional)
        created_at: Creation timestamp
        updated_at: Last update timestamp
        deleted_at: Soft delete timestamp
    """

    __tablename__ = "tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Task content
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Status and priority
    priority = Column(String(20), default=TaskPriority.medium.value, nullable=False)
    status = Column(
        String(20), default=TaskStatus.pending.value, nullable=False, index=True
    )

    # Scheduling
    due_date = Column(DateTime, nullable=True, index=True)
    completed_at = Column(DateTime, nullable=True)

    # Organization
    tags = Column(JSON, default=list)

    # Context
    session_id = Column(UUID(as_uuid=True), nullable=True, index=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="tasks")

    def __repr__(self) -> str:
        return f"<Task(id={self.id}, title={self.title!r}, status={self.status})>"

    @property
    def is_deleted(self) -> bool:
        """Check if task is soft deleted."""
        return self.deleted_at is not None

    @property
    def is_overdue(self) -> bool:
        """Check if task is overdue."""
        if not self.due_date:
            return False
        if self.status == TaskStatus.completed.value:
            return False
        return datetime.utcnow() > self.due_date

    def complete(self) -> None:
        """Mark task as completed."""
        self.status = TaskStatus.completed.value
        self.completed_at = datetime.utcnow()

    def soft_delete(self) -> None:
        """Mark task as deleted."""
        self.deleted_at = datetime.utcnow()

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "user_id": self.user_id,
            "title": self.title,
            "description": self.description,
            "priority": self.priority,
            "status": self.status,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
            "is_overdue": self.is_overdue,
            "tags": self.tags or [],
            "session_id": str(self.session_id) if self.session_id else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
