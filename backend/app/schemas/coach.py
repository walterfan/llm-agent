"""
Pydantic schemas for Coach Chat API.
"""

from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class CoachMode(str, Enum):
    """Coaching mode."""

    COACH = "coach"  # Motivational coaching with progress awareness
    TUTOR = "tutor"  # Deep tutoring with RAG knowledge
    QUIZ = "quiz"  # Quiz-based assessment


class CoachChatRequest(BaseModel):
    """Request for coach chat."""

    message: str = Field(..., min_length=1, description="User message")
    mode: CoachMode = Field(default=CoachMode.COACH, description="Coaching mode")
    session_id: Optional[str] = Field(
        None, description="Session ID for conversation continuity"
    )
    goal_id: Optional[UUID] = Field(
        None, description="Scope coaching to a specific goal"
    )


class CoachChatResponse(BaseModel):
    """Response for coach chat (non-streaming)."""

    content: str
    sources: list[dict] = Field(
        default_factory=list, description="RAG source references"
    )
    session_id: str
    mode: str
