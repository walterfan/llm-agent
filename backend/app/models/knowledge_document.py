"""
Knowledge Document model for AI Coach RAG knowledge base.

Stores metadata about documents uploaded by users for RAG retrieval.
The actual vector embeddings are stored in ChromaDB.
"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class KnowledgeDocument(Base):
    """
    Knowledge document metadata.

    Attributes:
        id: Unique identifier (UUID)
        user_id: Owner of the document
        title: Document title
        content: Original text content
        tags: List of tags for categorization
        source: Source of the document (e.g., 'upload', 'file:xxx.pdf')
        word_count: Number of words/characters in the document
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """

    __tablename__ = "knowledge_documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Document content
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)

    # Metadata
    tags = Column(JSON, default=list)
    source = Column(String(255), nullable=True, default="upload")
    word_count = Column(Integer, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="knowledge_documents")

    def __repr__(self) -> str:
        return f"<KnowledgeDocument(id={self.id}, title={self.title!r})>"

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "user_id": self.user_id,
            "title": self.title,
            "content": (
                self.content[:200] + "..." if len(self.content) > 200 else self.content
            ),
            "tags": self.tags or [],
            "source": self.source,
            "word_count": self.word_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
