"""Learning record model for storing user's learning content."""

from datetime import datetime
from enum import Enum
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class LearningRecordType(str, Enum):
    """
    Type of learning content.

    - word: English word learning
    - sentence: English sentence learning
    - topic: Tech topic learning plan
    - article: Web article with translation and mindmap
    - question: Q&A content
    - idea: Idea converted to action plan
    """

    WORD = "word"
    SENTENCE = "sentence"
    TOPIC = "topic"
    ARTICLE = "article"
    QUESTION = "question"
    IDEA = "idea"


class LearningRecord(Base):
    """
    Learning record model for persisting user's learning content.

    Stores various types of learning content (words, sentences, topics, etc.)
    along with the structured response from the AI and user metadata.

    Attributes:
        id: Unique UUID identifier
        user_id: Foreign key to the user who owns this record
        input_type: Type of learning content (word, sentence, topic, etc.)
        user_input: The original user input (word, sentence, URL, etc.)
        response_payload: JSON containing the structured response
        session_id: Optional link to the chat session where this was created
        tags: JSON array of tags for categorization
        is_favorite: Whether user marked this as favorite
        review_count: Number of times user has reviewed this
        last_reviewed_at: When the user last reviewed this
        created_at: When the record was created
        updated_at: When the record was last updated
        is_deleted: Soft delete flag
    """

    __tablename__ = "learning_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    input_type = Column(
        SQLEnum(LearningRecordType, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        index=True,
    )
    user_input = Column(Text, nullable=False)

    # Structured response from AI (JSON)
    # Contains the full response schema (WordResponse, TopicResponse, etc.)
    response_payload = Column(JSON, nullable=False)

    # Optional link to chat session
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("chat_sessions.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Categorization
    tags = Column(JSON, nullable=True)  # ["english", "vocabulary", etc.]

    # User engagement
    is_favorite = Column(Boolean, default=False, nullable=False)
    review_count = Column(Integer, default=0, nullable=False)
    last_reviewed_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Soft delete
    is_deleted = Column(Boolean, default=False, nullable=False)

    # Relationships
    user = relationship("User", back_populates="learning_records")
    session = relationship("ChatSession")

    def __repr__(self) -> str:
        input_preview = (
            self.user_input[:30] + "..."
            if len(self.user_input) > 30
            else self.user_input
        )
        return (
            f"<LearningRecord(id={self.id}, type={self.input_type.value}, "
            f"input={input_preview})>"
        )
