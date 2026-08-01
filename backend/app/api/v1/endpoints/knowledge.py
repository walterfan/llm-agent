"""
Knowledge Base API endpoints.

Provides document CRUD and RAG semantic query for the AI Coach knowledge base.
All endpoints require JWT authentication and scope data per user.
"""

import logging
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.db.base import get_db
from app.models.knowledge_document import KnowledgeDocument
from app.models.user import User
from app.schemas.knowledge import (
    DocumentResponse,
    DocumentUpload,
    FileUploadResponse,
    KnowledgeQuery,
    KnowledgeQueryResponse,
    KnowledgeQueryResult,
    KnowledgeStats,
)
from app.services.rag.engine import get_rag_engine

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/documents", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED
)
def upload_document(
    payload: DocumentUpload,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """Upload a text document to the knowledge base."""
    doc_id = uuid4()
    word_count = len(payload.content)

    # Save metadata to DB
    doc = KnowledgeDocument(
        id=doc_id,
        user_id=current_user.id,
        title=payload.title,
        content=payload.content,
        tags=payload.tags,
        source="upload",
        word_count=word_count,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    # Index in RAG engine
    rag = get_rag_engine()
    if rag and rag.is_available:
        rag.add_document(
            doc_id=str(doc_id),
            title=payload.title,
            content=payload.content,
            user_id=current_user.id,
        )
    else:
        logger.warning("RAG engine not available, document saved to DB only")

    logger.info(
        f"Document uploaded: {payload.title} (id={doc_id}, user={current_user.id})"
    )
    return doc


@router.post(
    "/documents/file",
    response_model=FileUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Upload a file (PDF/TXT/MD) to the knowledge base."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    # Validate file type
    allowed_extensions = {".txt", ".md", ".pdf"}
    ext = "." + file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {ext}. Allowed: {', '.join(allowed_extensions)}",
        )

    # Read file content
    raw_bytes = await file.read()
    if len(raw_bytes) > 10 * 1024 * 1024:  # 10MB limit
        raise HTTPException(status_code=400, detail="File too large (max 10MB)")

    # Extract text based on file type
    if ext == ".pdf":
        try:
            from pypdf import PdfReader
            import io

            reader = PdfReader(io.BytesIO(raw_bytes))
            content = "\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to parse PDF: {e}")
    else:
        # TXT / MD
        content = raw_bytes.decode("utf-8", errors="replace")

    if not content.strip():
        raise HTTPException(status_code=400, detail="File contains no extractable text")

    doc_id = uuid4()
    title = file.filename.rsplit(".", 1)[0] if "." in file.filename else file.filename
    word_count = len(content)

    # Save to DB
    doc = KnowledgeDocument(
        id=doc_id,
        user_id=current_user.id,
        title=title,
        content=content,
        tags=[],
        source=f"file:{file.filename}",
        word_count=word_count,
    )
    db.add(doc)
    db.commit()

    # Index in RAG
    rag = get_rag_engine()
    if rag and rag.is_available:
        rag.add_document(
            doc_id=str(doc_id),
            title=title,
            content=content,
            user_id=current_user.id,
        )

    db.refresh(doc)  # ensure created_at/updated_at are loaded
    logger.info(f"File uploaded: {file.filename} (id={doc_id}, {word_count} chars)")
    return FileUploadResponse(
        document=DocumentResponse.model_validate(doc),
        message=f"File '{file.filename}' uploaded and indexed successfully",
    )


@router.get("/documents", response_model=list[DocumentResponse])
def list_documents(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """List all documents for the current user."""
    docs = (
        db.query(KnowledgeDocument)
        .filter(KnowledgeDocument.user_id == current_user.id)
        .order_by(KnowledgeDocument.created_at.desc())
        .all()
    )
    return docs


@router.delete("/documents/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    doc_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """Delete a document from the knowledge base."""
    doc = (
        db.query(KnowledgeDocument)
        .filter(
            KnowledgeDocument.id == doc_id,
            KnowledgeDocument.user_id == current_user.id,
        )
        .first()
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Remove from RAG
    rag = get_rag_engine()
    if rag and rag.is_available:
        rag.delete_document(str(doc_id))

    # Remove from DB
    db.delete(doc)
    db.commit()

    logger.info(f"Document deleted: {doc_id}")


@router.post("/query", response_model=KnowledgeQueryResponse)
def query_knowledge(
    payload: KnowledgeQuery,
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """Query the knowledge base using semantic search. Returns empty results with a message when RAG is unavailable."""
    rag = get_rag_engine()
    if not rag or not rag.is_available:
        reason = (
            getattr(rag, "init_error", None) if rag else "RAG engine not initialized"
        )
        hint = (
            (
                "Ensure LLM_API_KEY (or EMBEDDING_API_KEY) is set and that the embedding "
                "base URL supports /embeddings (e.g. OpenAI). Many chat APIs (e.g. DeepSeek) do not. "
                "Set EMBEDDING_BASE_URL=https://api.openai.com/v1 and EMBEDDING_API_KEY for embeddings."
            )
            if reason and "404" in str(reason)
            else (
                "Ensure optional dependencies are installed: pip install llama-index chromadb. "
                "Check backend logs for the full error."
            )
        )
        return KnowledgeQueryResponse(
            query=payload.query,
            results=[],
            total=0,
            message=f"RAG engine is not available. Reason: {reason or 'Unknown.'} {hint}",
        )

    response = rag.query(
        query_text=payload.query,
        user_id=current_user.id,
        top_k=payload.top_k,
    )

    results = [
        KnowledgeQueryResult(
            doc_id=r.metadata.get("doc_id"),
            title=r.metadata.get("title"),
            content=r.content,
            score=r.score,
            metadata=r.metadata,
        )
        for r in response.results
    ]

    return KnowledgeQueryResponse(
        query=payload.query,
        results=results,
        total=response.total,
    )


@router.get("/stats", response_model=KnowledgeStats)
def get_stats(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """Get knowledge base statistics for the current user."""
    # Count documents from DB
    total_documents = (
        db.query(KnowledgeDocument)
        .filter(KnowledgeDocument.user_id == current_user.id)
        .count()
    )

    # Total words from DB
    from sqlalchemy import func

    total_words_result = (
        db.query(func.sum(KnowledgeDocument.word_count))
        .filter(KnowledgeDocument.user_id == current_user.id)
        .scalar()
    )
    total_words = total_words_result or 0

    # Chunks from RAG engine
    rag = get_rag_engine()
    total_chunks = 0
    if rag and rag.is_available:
        stats = rag.get_stats(user_id=current_user.id)
        total_chunks = stats.get("user_chunks", 0)

    return KnowledgeStats(
        total_documents=total_documents,
        total_chunks=total_chunks,
        total_words=total_words,
    )
