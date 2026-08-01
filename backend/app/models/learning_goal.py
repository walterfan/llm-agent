"""
Learning Goal model for AI Coach learning plan tracking.

Tracks user learning goals with deadlines, daily targets, and completion status.
"""

from datetime import datetime
from enum import Enum
from uuid import uuid4

from sqlalchemy import (
    Column,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class GoalStatus(str, Enum):
    """Learning goal status."""

    ACTIVE = "active"
    COMPLETED = "completed"
    PAUSED = "paused"
    ABANDONED = "abandoned"


class LearningGoal(Base):
    """
    Learning goal for tracking study progress.

    Attributes:
        id: Unique identifier (UUID)
        user_id: Owner of the goal
        subject: Subject/topic of the goal
        description: Detailed description
        status: Current status (active/completed/paused/abandoned)
        daily_target_minutes: Daily study target in minutes
        deadline: Optional deadline
        created_at: Creation timestamp
        completed_at: Completion timestamp
    """

    __tablename__ = "learning_goals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Goal details
    subject = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(
        SQLEnum(GoalStatus),
        nullable=False,
        default=GoalStatus.ACTIVE,
        index=True,
    )
    daily_target_minutes = Column(Integer, nullable=True, default=30)

    # Timestamps
    deadline = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="learning_goals")
    study_sessions = relationship(
        "StudySession",
        back_populates="goal",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    def __repr__(self) -> str:
        return f"<LearningGoal(id={self.id}, subject={self.subject!r}, status={self.status})>"

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "user_id": self.user_id,
            "subject": self.subject,
            "description": self.description,
            "status": self.status.value if self.status else None,
            "daily_target_minutes": self.daily_target_minutes,
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
        }
