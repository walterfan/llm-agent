"""
Medical Paper models for the Paper Writing Assistant.

Stores paper writing tasks, their workflow state, and A2A audit trail messages.
"""

from datetime import datetime
from enum import Enum
from uuid import uuid4

from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import relationship

from app.db.base import Base


class PaperType(str, Enum):
    """Types of medical papers supported."""

    RCT = "rct"  # Randomized Controlled Trial
    META_ANALYSIS = "meta_analysis"  # Meta-Analysis / Systematic Review
    COHORT = "cohort"  # Cohort Study


class PaperTaskStatus(str, Enum):
    """Status of a medical paper writing task."""

    PENDING = "pending"
    RUNNING = "running"
    REVISION = "revision"
    COMPLETED = "completed"
    FAILED = "failed"


class MedicalPaperTask(Base):
    """
    Medical paper writing task.

    Tracks the full lifecycle of a paper writing request:
    literature search -> stats analysis -> IMRAD writing -> compliance check.
    """

    __tablename__ = "medical_paper_tasks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Task metadata
    title = Column(String(500), nullable=False)
    paper_type = Column(String(20), nullable=False)
    status = Column(String(20), nullable=False, index=True)

    # Input
    research_question = Column(Text, nullable=False)
    study_design = Column(JSON, nullable=True)
    raw_data = Column(JSON, nullable=True)

    # Output
    manuscript = Column(JSON, nullable=True)  # Final manuscript sections
    references = Column(JSON, nullable=True)  # Literature references
    stats_report = Column(JSON, nullable=True)  # Statistical analysis report
    compliance_report = Column(JSON, nullable=True)  # Compliance check report

    # Workflow tracking
    current_step = Column(String(50), nullable=True)
    revision_round = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="medical_paper_tasks")
    messages = relationship(
        "PaperTaskMessage", back_populates="task", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<MedicalPaperTask(id={self.id}, title={self.title!r}, status={self.status})>"

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "user_id": self.user_id,
            "title": self.title,
            "paper_type": self.paper_type,
            "status": self.status,
            "research_question": self.research_question,
            "study_design": self.study_design,
            "current_step": self.current_step,
            "revision_round": self.revision_round,
            "manuscript": self.manuscript,
            "references": self.references,
            "stats_report": self.stats_report,
            "compliance_report": self.compliance_report,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
        }


class PaperTaskMessage(Base):
    """
    A2A message audit trail for paper writing tasks.

    Every inter-agent message is persisted here for observability and debugging.
    """

    __tablename__ = "paper_task_messages"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    task_id = Column(
        String(36), ForeignKey("medical_paper_tasks.id"), nullable=False, index=True
    )

    # A2A message fields
    sender = Column(String(50), nullable=False)
    receiver = Column(String(50), nullable=False)
    intent = Column(String(50), nullable=False)
    status = Column(String(20), nullable=False)
    input_payload = Column(JSON, nullable=True)
    output_payload = Column(JSON, nullable=True)
    error = Column(JSON, nullable=True)

    # Metrics
    latency_ms = Column(Integer, nullable=True)
    tokens_in = Column(Integer, nullable=True)
    tokens_out = Column(Integer, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    task = relationship("MedicalPaperTask", back_populates="messages")

    def __repr__(self) -> str:
        return f"<PaperTaskMessage(id={self.id}, sender={self.sender}, intent={self.intent})>"

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "task_id": str(self.task_id),
            "sender": self.sender,
            "receiver": self.receiver,
            "intent": self.intent,
            "status": self.status,
            "input_payload": self.input_payload,
            "output_payload": self.output_payload,
            "error": self.error,
            "latency_ms": self.latency_ms,
            "tokens_in": self.tokens_in,
            "tokens_out": self.tokens_out,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
