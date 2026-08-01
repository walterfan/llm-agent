from datetime import datetime, date
from uuid import uuid4

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class Recommendation(Base):
    """Recommendation model for AI-generated AI Recommendations."""

    __tablename__ = "recommendations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()), index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    city = Column(String(100), nullable=False)
    weather_data = Column(
        JSON, nullable=False
    )  # Snapshot of weather at generation time
    prompt = Column(Text, nullable=False)  # Full prompt sent to LLM
    response = Column(JSON, nullable=False)  # Structured RecommendationOutput
    cost_estimate = Column(Float, nullable=True)  # Estimated API cost
    tokens_used = Column(Integer, nullable=True)  # Total tokens
    forecast_date = Column(
        Date, nullable=True, index=True
    )  # The date this recommendation is for (today, tomorrow, etc.)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationship to User
    # user = relationship("User", back_populates="recommendations")

    def __repr__(self) -> str:
        return (
            f"<Recommendation(id={self.id}, user_id={self.user_id}, city={self.city})>"
        )


class CostLog(Base):
    """Cost log for tracking LLM API usage."""

    __tablename__ = "cost_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    recommendation_id = Column(
        String(36), ForeignKey("recommendations.id", ondelete="SET NULL"), nullable=True
    )
    model = Column(String(100), nullable=False)
    prompt_tokens = Column(Integer, nullable=False)
    completion_tokens = Column(Integer, nullable=False)
    total_tokens = Column(Integer, nullable=False)
    estimated_cost = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    def __repr__(self) -> str:
        return f"<CostLog(id={self.id}, user_id={self.user_id}, cost={self.estimated_cost})>"
