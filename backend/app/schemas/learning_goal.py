"""
Pydantic schemas for Learning Goal and Study Session APIs.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


# --- Goal schemas ---


class GoalCreate(BaseModel):
    """Create a new learning goal."""

    subject: str = Field(..., min_length=1, max_length=255, description="Subject/topic")
    description: Optional[str] = Field(None, description="Detailed description")
    daily_target_minutes: int = Field(
        default=30, ge=1, le=480, description="Daily target in minutes"
    )
    deadline: Optional[datetime] = Field(None, description="Optional deadline")


class GoalUpdate(BaseModel):
    """Update an existing learning goal."""

    subject: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    status: Optional[str] = Field(None, pattern="^(active|completed|paused|abandoned)$")
    daily_target_minutes: Optional[int] = Field(None, ge=1, le=480)
    deadline: Optional[datetime] = None


class GoalResponse(BaseModel):
    """Response for a single learning goal."""

    id: UUID
    subject: str
    description: Optional[str] = None
    status: str
    daily_target_minutes: Optional[int] = None
    deadline: Optional[datetime] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# --- Session schemas ---


class SessionCreate(BaseModel):
    """Log a study session."""

    goal_id: Optional[UUID] = Field(None, description="Associated learning goal")
    duration_minutes: int = Field(..., ge=1, le=720, description="Duration in minutes")
    notes: Optional[str] = Field(None, description="Session notes")
    difficulty: Optional[str] = Field(
        None, pattern="^(easy|medium|hard)$", description="Difficulty rating"
    )


class SessionResponse(BaseModel):
    """Response for a single study session."""

    id: UUID
    goal_id: Optional[UUID] = None
    duration_minutes: int
    notes: Optional[str] = None
    difficulty: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Progress schemas ---


class ProgressReport(BaseModel):
    """Progress report for a learning goal."""

    goal: GoalResponse
    total_sessions: int
    total_minutes: int
    avg_minutes_per_session: float
    current_streak_days: int
    longest_streak_days: int
    completion_percentage: float
    days_remaining: Optional[int] = None
    ai_feedback: Optional[str] = None
