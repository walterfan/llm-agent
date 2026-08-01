from datetime import datetime, time
from enum import Enum

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum as SQLEnum,
    Integer,
    JSON,
    String,
    Text,
    Time,
)
from sqlalchemy.orm import relationship

from app.db.base import Base


class UserRole(str, Enum):
    """User role enumeration for role-based access control."""

    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    USER = "user"
    GUEST = "guest"


class User(Base):
    """User model for authentication and profile management."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    role = Column(
        SQLEnum(UserRole, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        default=UserRole.USER,
        index=True,
    )
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Profile fields for Lazy Rabbit AI Agents
    gender = Column(String(10), nullable=True)  # "男", "女", "其他"
    age = Column(Integer, nullable=True)
    identity = Column(String(50), nullable=True)  # "大学生", "上班族", "退休人员"
    style = Column(
        String(50), nullable=True
    )  # "舒适优先", "时尚优先", "运动风", "商务风"
    temperature_sensitivity = Column(
        String(20), nullable=True
    )  # "怕冷", "正常", "怕热", "非常怕冷"
    activity_context = Column(
        String(50), nullable=True
    )  # "工作日", "周末", "假期", "出游", "居家"
    other_preferences = Column(Text, nullable=True)  # Free-form text

    # Email notification preferences
    email_notifications_enabled = Column(Boolean, default=False, nullable=False)
    email_send_time = Column(Time, nullable=True)  # Preferred send time (e.g., 08:00)
    email_additional_recipients = Column(
        JSON, nullable=True
    )  # List of additional email addresses
    email_preferred_city = Column(
        String(20), nullable=True
    )  # AD code for recommendation city

    # Relationships for Personal Secretary agent
    notes = relationship("Note", back_populates="user", lazy="dynamic")
    tasks = relationship("Task", back_populates="user", lazy="dynamic")
    reminders = relationship("Reminder", back_populates="user", lazy="dynamic")
    chat_sessions = relationship("ChatSession", back_populates="user", lazy="dynamic")
    learning_records = relationship(
        "LearningRecord", back_populates="user", lazy="dynamic"
    )
    medical_paper_tasks = relationship(
        "MedicalPaperTask", back_populates="user", lazy="dynamic"
    )
    knowledge_documents = relationship(
        "KnowledgeDocument", back_populates="user", lazy="dynamic"
    )
    learning_goals = relationship("LearningGoal", back_populates="user", lazy="dynamic")
    study_sessions = relationship("StudySession", back_populates="user", lazy="dynamic")

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, role={self.role.value})>"
