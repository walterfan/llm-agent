"""
Chat service for managing chat sessions and messages.

This service handles CRUD operations for the Personal Secretary agent's
conversation management, including session creation, message storage,
and history retrieval.
"""

import logging
from typing import Optional
from uuid import UUID

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.models.chat_message import ChatMessage, MessageRole
from app.models.chat_session import ChatSession

logger = logging.getLogger(__name__)


class ChatService:
    """
    Service for chat session and message management.

    Provides CRUD operations for:
    - Chat sessions (conversations)
    - Chat messages (individual messages within sessions)

    All operations include user ownership validation to ensure users
    can only access their own data.
    """

    @staticmethod
    def create_session(
        db: Session, user_id: int, title: Optional[str] = None
    ) -> ChatSession:
        """
        Create a new chat session for a user.

        Args:
            db: Database session
            user_id: ID of the user creating the session
            title: Optional title (auto-generated from first message if None)

        Returns:
            The created ChatSession
        """
        session = ChatSession(
            user_id=user_id,
            title=title,
        )
        db.add(session)
        db.commit()
        db.refresh(session)

        logger.info(f"Created chat session {session.id} for user {user_id}")
        return session

    @staticmethod
    def get_session(
        db: Session, session_id: UUID, user_id: int
    ) -> Optional[ChatSession]:
        """
        Get a chat session by ID with ownership validation.

        Args:
            db: Database session
            session_id: UUID of the session to retrieve
            user_id: ID of the user (for ownership check)

        Returns:
            ChatSession if found and owned by user, None otherwise
        """
        return (
            db.query(ChatSession)
            .filter(
                ChatSession.id == session_id,
                ChatSession.user_id == user_id,
                ChatSession.is_active == True,  # noqa: E712
            )
            .first()
        )

    @staticmethod
    def list_sessions(
        db: Session, user_id: int, limit: int = 20, offset: int = 0
    ) -> tuple[list[ChatSession], int]:
        """
        List chat sessions for a user with pagination.

        Args:
            db: Database session
            user_id: ID of the user
            limit: Maximum number of sessions to return
            offset: Number of sessions to skip

        Returns:
            Tuple of (list of sessions, total count)
        """
        query = db.query(ChatSession).filter(
            ChatSession.user_id == user_id,
            ChatSession.is_active == True,  # noqa: E712
        )

        total = query.count()

        sessions = (
            query.order_by(desc(ChatSession.updated_at))
            .offset(offset)
            .limit(limit)
            .all()
        )

        return sessions, total

    @staticmethod
    def delete_session(db: Session, session_id: UUID, user_id: int) -> bool:
        """
        Soft delete a chat session (set is_active=False).

        Args:
            db: Database session
            session_id: UUID of the session to delete
            user_id: ID of the user (for ownership check)

        Returns:
            True if deleted, False if not found or not owned
        """
        session = ChatService.get_session(db, session_id, user_id)
        if not session:
            return False

        session.is_active = False
        db.commit()

        logger.info(f"Soft deleted chat session {session_id} for user {user_id}")
        return True

    @staticmethod
    def update_session_title(
        db: Session, session_id: UUID, user_id: int, title: str
    ) -> Optional[ChatSession]:
        """
        Update the title of a chat session.

        Args:
            db: Database session
            session_id: UUID of the session
            user_id: ID of the user (for ownership check)
            title: New title for the session

        Returns:
            Updated ChatSession, or None if not found
        """
        session = ChatService.get_session(db, session_id, user_id)
        if not session:
            return None

        session.title = title
        db.commit()
        db.refresh(session)
        return session

    @staticmethod
    def add_message(
        db: Session,
        session_id: UUID,
        role: MessageRole,
        content: Optional[str],
        tool_calls: Optional[list[dict]] = None,
        tool_name: Optional[str] = None,
        tool_call_id: Optional[str] = None,
    ) -> ChatMessage:
        """
        Add a message to a chat session.

        Args:
            db: Database session
            session_id: UUID of the session
            role: Role of the message sender (user/assistant/tool/system)
            content: Text content of the message
            tool_calls: List of tool calls (for assistant messages)
            tool_name: Name of tool (for tool result messages)
            tool_call_id: ID linking to the tool call (for tool results)

        Returns:
            The created ChatMessage
        """
        message = ChatMessage(
            session_id=session_id,
            role=role,
            content=content,
            tool_calls=tool_calls,
            tool_name=tool_name,
            tool_call_id=tool_call_id,
        )
        db.add(message)

        # Update session's updated_at timestamp
        session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
        if session:
            from datetime import datetime

            session.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(message)

        logger.debug(f"Added {role.value} message to session {session_id}")
        return message

    @staticmethod
    def get_messages(
        db: Session,
        session_id: UUID,
        limit: Optional[int] = None,
        before_id: Optional[UUID] = None,
    ) -> list[ChatMessage]:
        """
        Get messages from a chat session.

        Args:
            db: Database session
            session_id: UUID of the session
            limit: Maximum number of messages (None for all)
            before_id: Get messages created before this message ID

        Returns:
            List of messages ordered by creation time (oldest first)
        """
        query = db.query(ChatMessage).filter(ChatMessage.session_id == session_id)

        if before_id:
            # Get the timestamp of the reference message
            ref_message = (
                db.query(ChatMessage).filter(ChatMessage.id == before_id).first()
            )
            if ref_message:
                query = query.filter(ChatMessage.created_at < ref_message.created_at)

        # Order by creation time (oldest first for conversation flow)
        query = query.order_by(ChatMessage.created_at)

        if limit:
            # If limiting, we want the most recent N messages
            # So we order desc, limit, then reverse
            query = (
                db.query(ChatMessage)
                .filter(ChatMessage.session_id == session_id)
                .order_by(desc(ChatMessage.created_at))
                .limit(limit)
            )

            messages = query.all()
            messages.reverse()  # Restore chronological order
            return messages

        return query.all()

    @staticmethod
    def get_message_count(db: Session, session_id: UUID) -> int:
        """
        Get the number of messages in a session.

        Args:
            db: Database session
            session_id: UUID of the session

        Returns:
            Count of messages
        """
        return (
            db.query(ChatMessage).filter(ChatMessage.session_id == session_id).count()
        )

    @staticmethod
    def generate_session_title(content: str, max_length: int = 50) -> str:
        """
        Generate a session title from the first message content.

        Args:
            content: The message content
            max_length: Maximum length of the title

        Returns:
            A truncated title suitable for display
        """
        # Remove newlines and extra whitespace
        title = " ".join(content.split())

        if len(title) <= max_length:
            return title

        # Truncate at word boundary
        truncated = title[:max_length].rsplit(" ", 1)[0]
        return truncated + "..."
