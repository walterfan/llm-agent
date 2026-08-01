"""
Study Session model for AI Coach learning plan tracking.

Logs individual study sessions linked to learning goals.
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


class Difficulty(str, Enum):
    """Study session difficulty rating."""

    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class StudySession(Base):
    """
    Study session log entry.

    Attributes:
        id: Unique identifier (UUID)
        user_id: Owner of the session
        goal_id: Associated learning goal (optional)
        duration_minutes: Duration of the study session
        notes: Session notes
        difficulty: Self-rated difficulty
        created_at: When the session was logged
    """

    __tablename__ = "study_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    goal_id = Column(
        UUID(as_uuid=True),
        ForeignKey("learning_goals.id"),
        nullable=True,
        index=True,
    )

    # Session details
    duration_minutes = Column(Integer, nullable=False)
    notes = Column(Text, nullable=True)
    difficulty = Column(SQLEnum(Difficulty), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="study_sessions")
    goal = relationship("LearningGoal", back_populates="study_sessions")

    def __repr__(self) -> str:
        return f"<StudySession(id={self.id}, duration={self.duration_minutes}min)>"

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "user_id": self.user_id,
            "goal_id": str(self.goal_id) if self.goal_id else None,
            "duration_minutes": self.duration_minutes,
            "notes": self.notes,
            "difficulty": self.difficulty.value if self.difficulty else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
