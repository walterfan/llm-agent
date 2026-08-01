"""AgentSpec persistence model — stores compiled child-agent blueprints.

The full AgentSpec (Pydantic) is serialized into ``spec_json``; a few fields are
lifted into columns for querying (name / version / status / one_liner / owner).
"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String, Text

from app.db.base import Base


class AgentSpecRecord(Base):
    """A stored child-agent blueprint (draft / approved / published)."""

    __tablename__ = "agent_specs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()), index=True)
    name = Column(String(200), nullable=False, default="")
    version = Column(Integer, nullable=False, default=1)
    status = Column(String(20), nullable=False, default="draft", index=True)
    one_liner = Column(Text, nullable=False, default="")
    spec_json = Column(JSON, nullable=False)  # full serialized AgentSpec
    created_by = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    def __repr__(self) -> str:
        return (
            f"<AgentSpecRecord(id={self.id}, name={self.name!r}, "
            f"version={self.version}, status={self.status})>"
        )
