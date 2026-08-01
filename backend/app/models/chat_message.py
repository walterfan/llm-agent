"""Chat message model for Personal Secretary agent conversations."""

from datetime import datetime
from enum import Enum
from uuid import uuid4

from sqlalchemy import Column, DateTime, Enum as SQLEnum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class MessageRole(str, Enum):
    """
    Role of the message sender.

    - user: Message from the human user
    - assistant: Response from the AI agent
    - tool: Result from a tool execution
    - system: System message (e.g., context injection)
    """

    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"
    SYSTEM = "system"


class ChatMessage(Base):
    """
    Chat message model for storing individual messages in a session.

    Stores both user messages and assistant responses, including
    tool calls and their results.

    Attributes:
        id: Unique UUID identifier for the message
        session_id: Foreign key to the parent chat session
        role: Who sent the message (user/assistant/tool/system)
        content: The text content of the message
        tool_calls: JSON array of tool calls made by assistant
        tool_name: Name of the tool (for tool role messages)
        tool_call_id: ID linking tool result to its call
        created_at: When the message was created
    """

    __tablename__ = "chat_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, index=True)
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("chat_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role = Column(
        SQLEnum(MessageRole, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        index=True,
    )
    content = Column(Text, nullable=True)

    # Tool-related fields
    # For assistant messages: list of tool calls made
    # Format: [{"id": "call_xxx", "name": "tool_name", "arguments": {...}}]
    tool_calls = Column(JSON, nullable=True)

    # For tool role messages: which tool produced this result
    tool_name = Column(String(100), nullable=True)

    # For tool role messages: links back to the tool_call id
    tool_call_id = Column(String(100), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    session = relationship("ChatSession", back_populates="messages")

    def __repr__(self) -> str:
        content_preview = (
            self.content[:50] + "..."
            if self.content and len(self.content) > 50
            else self.content
        )
        return f"<ChatMessage(id={self.id}, role={self.role.value}, content={content_preview})>"
