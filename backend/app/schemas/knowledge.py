"""
Pydantic schemas for Knowledge Base API.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


# --- Request schemas ---


class DocumentUpload(BaseModel):
    """Upload a text document to the knowledge base."""

    title: str = Field(..., min_length=1, max_length=500, description="Document title")
    content: str = Field(..., min_length=1, description="Document text content")
    tags: list[str] = Field(default_factory=list, description="Tags for categorization")


class KnowledgeQuery(BaseModel):
    """Query the knowledge base using semantic search."""

    query: str = Field(..., min_length=1, description="Search query text")
    top_k: int = Field(
        default=3, ge=1, le=10, description="Number of results to return"
    )


# --- Response schemas ---


class DocumentResponse(BaseModel):
    """Response for a single document."""

    id: UUID
    title: str
    content: str
    tags: list[str]
    source: Optional[str] = None
    word_count: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class FileUploadResponse(BaseModel):
    """Response after uploading a file. Includes full document so clients can update the list without refetching."""

    document: DocumentResponse
    message: str


class KnowledgeQueryResult(BaseModel):
    """A single result from a knowledge base query."""

    doc_id: Optional[str] = None
    title: Optional[str] = None
    content: str
    score: float
    metadata: dict = Field(default_factory=dict)


class KnowledgeQueryResponse(BaseModel):
    """Response for a knowledge base query."""

    query: str
    results: list[KnowledgeQueryResult]
    total: int
    message: Optional[str] = None  # Optional notice when RAG is unavailable


class KnowledgeStats(BaseModel):
    """Knowledge base statistics."""

    total_documents: int
    total_chunks: int
    total_words: int
