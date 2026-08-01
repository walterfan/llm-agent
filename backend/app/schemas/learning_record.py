"""
Pydantic schemas for learning record API endpoints.
"""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.learning_record import LearningRecordType


# ============================================================================
# Request Schemas
# ============================================================================


class LearningRecordCreate(BaseModel):
    """Request schema for creating a learning record (confirming save)."""

    input_type: LearningRecordType = Field(
        description="Type of learning content: word, sentence, topic, article, question, idea"
    )
    user_input: str = Field(
        ...,
        min_length=1,
        description="The original user input (word, sentence, URL, etc.)",
    )
    response_payload: dict[str, Any] = Field(
        description="The structured response from the AI"
    )
    session_id: Optional[UUID] = Field(
        default=None, description="Optional chat session ID where this was created"
    )
    tags: Optional[list[str]] = Field(
        default=None, description="Optional tags for categorization"
    )


class LearningRecordUpdate(BaseModel):
    """Request schema for updating a learning record."""

    tags: Optional[list[str]] = Field(
        default=None, description="New tags for the record"
    )
    is_favorite: Optional[bool] = Field(default=None, description="Favorite status")


# ============================================================================
# Response Schemas
# ============================================================================


class LearningRecordResponse(BaseModel):
    """Schema for a single learning record."""

    id: UUID = Field(description="Record ID")
    input_type: LearningRecordType = Field(description="Type of learning content")
    user_input: str = Field(description="Original user input")
    response_payload: dict[str, Any] = Field(description="AI response")
    session_id: Optional[UUID] = Field(description="Related chat session ID")
    tags: list[str] = Field(description="Tags")
    is_favorite: bool = Field(description="Whether marked as favorite")
    review_count: int = Field(description="Number of times reviewed")
    last_reviewed_at: Optional[datetime] = Field(description="Last review time")
    created_at: datetime = Field(description="When created")
    updated_at: datetime = Field(description="When last updated")

    class Config:
        from_attributes = True


class LearningRecordListResponse(BaseModel):
    """Schema for paginated learning record list."""

    records: list[LearningRecordResponse] = Field(description="List of records")
    total: int = Field(description="Total number of records")
    page: int = Field(description="Current page")
    page_size: int = Field(description="Items per page")


class LearningStatisticsResponse(BaseModel):
    """Schema for learning statistics."""

    total: int = Field(description="Total number of records")
    by_type: dict[str, int] = Field(description="Count by type")
    favorites: int = Field(description="Number of favorites")
    total_reviews: int = Field(description="Total review count")
