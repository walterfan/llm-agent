"""
Pydantic schemas for chat API endpoints.
"""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ============================================================================
# Request Schemas
# ============================================================================


class ChatRequest(BaseModel):
    """Request schema for sending a chat message."""

    message: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="The message to send to the agent",
    )
    session_id: Optional[UUID] = Field(
        default=None, description="ID of existing session (creates new if not provided)"
    )


# ============================================================================
# Response Schemas
# ============================================================================


class ToolCallInfo(BaseModel):
    """Information about a tool call made during response."""

    tool: str = Field(description="Name of the tool")
    args: dict[str, Any] = Field(
        default_factory=dict,
        description="Arguments passed to the tool (empty when only name/result is stored)",
    )
    result: Optional[str] = Field(default=None, description="Tool execution result")


class ChatResponse(BaseModel):
    """Response schema for non-streaming chat."""

    session_id: UUID = Field(description="ID of the chat session")
    message_id: UUID = Field(description="ID of the response message")
    content: str = Field(description="Response content")
    tool_calls: list[ToolCallInfo] = Field(
        default_factory=list, description="Tool calls made during response"
    )
    created_at: datetime = Field(description="When the response was created")

    class Config:
        from_attributes = True


class MessageResponse(BaseModel):
    """Schema for a single chat message."""

    id: UUID = Field(description="Message ID")
    role: str = Field(description="Message role: user, assistant, tool, system")
    content: Optional[str] = Field(description="Message content")
    tool_calls: Optional[list[dict[str, Any]]] = Field(
        default=None, description="Tool calls (for assistant messages)"
    )
    tool_name: Optional[str] = Field(
        default=None, description="Tool name (for tool messages)"
    )
    created_at: datetime = Field(description="When the message was created")

    class Config:
        from_attributes = True


class SessionResponse(BaseModel):
    """Schema for a chat session."""

    id: UUID = Field(description="Session ID")
    title: Optional[str] = Field(description="Session title")
    message_count: int = Field(description="Number of messages in session")
    created_at: datetime = Field(description="When the session was created")
    updated_at: datetime = Field(description="When the session was last active")

    class Config:
        from_attributes = True


class SessionDetailResponse(BaseModel):
    """Schema for a session with messages."""

    id: UUID = Field(description="Session ID")
    title: Optional[str] = Field(description="Session title")
    messages: list[MessageResponse] = Field(description="Messages in the session")
    created_at: datetime = Field(description="When the session was created")
    updated_at: datetime = Field(description="When the session was last active")

    class Config:
        from_attributes = True


class SessionListResponse(BaseModel):
    """Schema for paginated session list."""

    sessions: list[SessionResponse] = Field(description="List of sessions")
    total: int = Field(description="Total number of sessions")
    page: int = Field(description="Current page")
    page_size: int = Field(description="Items per page")


class ToolInfo(BaseModel):
    """Information about an available tool."""

    name: str = Field(description="Tool name")
    description: str = Field(description="What the tool does")
    category: str = Field(description="Tool category: learning, utility, etc.")


class ToolListResponse(BaseModel):
    """Schema for list of available tools."""

    tools: list[ToolInfo] = Field(description="Available tools")
