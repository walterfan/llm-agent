"""Streaming response schemas for recommendations."""

from pydantic import BaseModel, Field


class StreamChunk(BaseModel):
    """Single chunk in a streaming response."""

    type: str = Field(
        ..., description="Type of chunk: 'token', 'data', 'error', 'done'"
    )
    content: str | None = Field(
        None, description="Chunk content (for 'token' and 'error' types)"
    )
    data: dict | None = Field(None, description="Structured data (for 'data' type)")


class StreamStartEvent(BaseModel):
    """Event sent at the start of streaming."""

    type: str = Field(default="start", description="Event type")
    message: str = Field(
        default="Starting recommendation generation...", description="Start message"
    )


class StreamTokenEvent(BaseModel):
    """Event sent for each token."""

    type: str = Field(default="token", description="Event type")
    content: str = Field(..., description="Token content")


class StreamDataEvent(BaseModel):
    """Event sent for structured data chunks."""

    type: str = Field(default="data", description="Event type")
    field: str = Field(
        ..., description="Field name (e.g., 'weather', 'clothing_items')"
    )
    value: str | dict | list = Field(..., description="Field value")


class StreamErrorEvent(BaseModel):
    """Event sent when an error occurs."""

    type: str = Field(default="error", description="Event type")
    message: str = Field(..., description="Error message")


class StreamDoneEvent(BaseModel):
    """Event sent when streaming is complete."""

    type: str = Field(default="done", description="Event type")
    message: str = Field(
        default="Recommendation generation complete", description="Completion message"
    )
    recommendation_id: str | None = Field(
        None, description="ID of the created recommendation"
    )
