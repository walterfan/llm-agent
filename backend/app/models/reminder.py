"""
Reminder model for Personal Secretary agent.

Reminders allow users to set time-based notifications.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
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


class ReminderStatus(str, Enum):
    """Reminder status options."""

    pending = "pending"  # Not yet triggered
    triggered = "triggered"  # Has been triggered/shown
    snoozed = "snoozed"  # User snoozed it
    dismissed = "dismissed"  # User dismissed it
    cancelled = "cancelled"  # User cancelled it


class ReminderRepeat(str, Enum):
    """Reminder repeat options."""

    none = "none"
    daily = "daily"
    weekly = "weekly"
    monthly = "monthly"
    yearly = "yearly"


class Reminder(Base):
    """
    Reminder model for time-based notifications.

    Attributes:
        id: Unique identifier (UUID)
        user_id: Owner of the reminder
        title: Reminder title (required)
        description: Additional details (optional)
        remind_at: When to trigger the reminder
        status: Current reminder status
        repeat: Repeat frequency
        snoozed_until: If snoozed, when to remind again
        tags: List of tags for categorization
        session_id: Chat session where reminder was created (optional)
        created_at: Creation timestamp
        updated_at: Last update timestamp
        deleted_at: Soft delete timestamp
    """

    __tablename__ = "reminders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Reminder content
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Scheduling
    remind_at = Column(DateTime, nullable=False, index=True)
    status = Column(
        String(20), default=ReminderStatus.pending.value, nullable=False, index=True
    )
    repeat = Column(String(20), default=ReminderRepeat.none.value, nullable=False)
    snoozed_until = Column(DateTime, nullable=True)

    # Organization
    tags = Column(JSON, default=list)

    # Context
    session_id = Column(UUID(as_uuid=True), nullable=True, index=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="reminders")

    def __repr__(self) -> str:
        return f"<Reminder(id={self.id}, title={self.title!r}, remind_at={self.remind_at})>"

    @property
    def is_deleted(self) -> bool:
        """Check if reminder is soft deleted."""
        return self.deleted_at is not None

    @property
    def is_due(self) -> bool:
        """Check if reminder is due to trigger."""
        if self.status != ReminderStatus.pending.value:
            return False
        if self.snoozed_until and datetime.utcnow() < self.snoozed_until:
            return False
        return datetime.utcnow() >= self.remind_at

    def trigger(self) -> None:
        """Mark reminder as triggered."""
        self.status = ReminderStatus.triggered.value

    def snooze(self, until: datetime) -> None:
        """Snooze reminder until specified time."""
        self.status = ReminderStatus.snoozed.value
        self.snoozed_until = until

    def dismiss(self) -> None:
        """Dismiss the reminder."""
        self.status = ReminderStatus.dismissed.value

    def soft_delete(self) -> None:
        """Mark reminder as deleted."""
        self.deleted_at = datetime.utcnow()

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "user_id": self.user_id,
            "title": self.title,
            "description": self.description,
            "remind_at": self.remind_at.isoformat() if self.remind_at else None,
            "status": self.status,
            "repeat": self.repeat,
            "snoozed_until": (
                self.snoozed_until.isoformat() if self.snoozed_until else None
            ),
            "is_due": self.is_due,
            "tags": self.tags or [],
            "session_id": str(self.session_id) if self.session_id else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
