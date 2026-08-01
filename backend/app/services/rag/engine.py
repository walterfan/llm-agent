"""
RAG Engine — pluggable vector store + LlamaIndex embeddings.

Supports two vector store backends:
- pgvector  : PostgreSQL with pgvector extension (production, recommended)
- chromadb  : ChromaDB embedded on-disk (development / standalone)

When DATABASE_URL points to SQLite, RAG is automatically disabled because
SQLite cannot host pgvector.  Set VECTOR_STORE=chromadb to force ChromaDB
on SQLite if desired.

This module is used by:
- Knowledge Base API endpoints (document management + semantic search)
- Coach sub-agent tools (RAG-augmented coaching)
- Future agents that need knowledge retrieval
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger("rag_engine")


@dataclass
class RAGResult:
    """Result from a RAG query."""

    content: str
    score: float
    metadata: dict = field(default_factory=dict)


@dataclass
class RAGQueryResponse:
    """Full response from a RAG query."""

    results: list[RAGResult]
    query: str
    total: int


class RAGEngine:
    """
    RAG Engine with pluggable vector store backend.

    Provides document indexing and semantic retrieval with per-user isolation.
    Designed for graceful degradation — if dependencies are unavailable,
    operations return empty results with warnings.
    """

    def __init__(
        self,
        *,
        vector_store_type: str = "auto",
        database_url: str = "",
        persist_dir: str = "data/chroma",
        chunk_size: int = 512,
        chunk_overlap: int = 50,
        similarity_top_k: int = 3,
        embedding_model: str = "text-embedding-3-small",
        llm_api_key: str = "",
        llm_base_url: str = "https://api.openai.com/v1",
        embedding_api_key: str = "",
        embedding_base_url: str = "",
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.similarity_top_k = similarity_top_k
        self.embedding_model = embedding_model

        self._embed_api_key = embedding_api_key or llm_api_key
        self._embed_base_url = embedding_base_url or llm_base_url

        self._available = False
        self._init_error: Optional[str] = None
        self._embed_model = None
        self._store = None
        self._backend_name = "none"

        resolved_type = self._resolve_store_type(vector_store_type, database_url)
        self._initialize(resolved_type, database_url, persist_dir)

    @staticmethod
    def _resolve_store_type(vector_store_type: str, database_url: str) -> str:
        """Determine which vector store backend to use.

        auto  → pgvector if DATABASE_URL is PostgreSQL, disabled if SQLite
        pgvector / chromadb / disabled → use as-is
        """
        if vector_store_type != "auto":
            return vector_store_type

        if not database_url:
            return "disabled"

        db_lower = database_url.lower()
        if "postgresql" in db_lower or "postgres" in db_lower:
            return "pgvector"
        if "sqlite" in db_lower:
            logger.info(
                "SQLite detected — RAG (vector search) is disabled. Use PostgreSQL to enable pgvector."
            )
            return "disabled"

        return "disabled"

    @property
    def init_error(self) -> Optional[str]:
        return self._init_error

    @property
    def is_available(self) -> bool:
        return self._available

    @property
    def backend_name(self) -> str:
        return self._backend_name

    def _initialize(self, store_type: str, database_url: str, persist_dir: str) -> None:
        if store_type == "disabled":
            self._init_error = "RAG disabled (SQLite does not support vector search. Use PostgreSQL with pgvector.)"
            self._backend_name = "disabled"
            logger.info(self._init_error)
            return

        try:
            from llama_index.embeddings.openai import OpenAIEmbedding

            self._embed_model = OpenAIEmbedding(
                model=self.embedding_model,
                api_key=self._embed_api_key,
                api_base=self._embed_base_url,
            )

            if store_type == "pgvector":
                from app.services.rag.vector_store import PgVectorStore

                self._store = PgVectorStore(database_url=database_url)
            elif store_type == "chromadb":
                from app.services.rag.vector_store import ChromaVectorStore

                self._store = ChromaVectorStore(persist_dir=persist_dir)
            else:
                self._init_error = f"Unknown vector store type: {store_type}"
                return

            self._store.initialize()
            self._backend_name = self._store.backend_name
            self._available = True
            logger.info(
                f"RAG engine initialized: backend={self._backend_name}, "
                f"embedding={self.embedding_model}, embed_base={self._embed_base_url}"
            )

        except ImportError as e:
            self._init_error = f"Missing dependency: {e}"
            logger.warning(f"RAG engine unavailable — {self._init_error}")
        except Exception as e:
            self._init_error = f"{type(e).__name__}: {e}"
            logger.error(f"RAG engine initialization failed: {e}", exc_info=True)

    # ------------------------------------------------------------------
    # Public API (unchanged interface)
    # ------------------------------------------------------------------

    def add_document(
        self,
        doc_id: str,
        title: str,
        content: str,
        user_id: int,
        metadata: Optional[dict] = None,
    ) -> bool:
        if not self._available:
            logger.warning("RAG engine not available, skipping add_document")
            return False

        try:
            chunks = self._chunk_text(content)
            if not chunks:
                logger.warning(f"No chunks generated for document {doc_id}")
                return False

            embeddings = self._embed_model.get_text_embedding_batch(chunks)

            ids = [f"{doc_id}_chunk_{i}" for i in range(len(chunks))]
            metadatas = [
                {
                    "doc_id": doc_id,
                    "title": title,
                    "user_id": str(user_id),
                    "chunk_index": i,
                    **(metadata or {}),
                }
                for i in range(len(chunks))
            ]

            self._store.upsert_chunks(
                ids=ids, texts=chunks, embeddings=embeddings, metadatas=metadatas
            )

            logger.info(
                f"Added document '{title}' (id={doc_id}): "
                f"{len(chunks)} chunks indexed for user {user_id}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to add document {doc_id}: {e}", exc_info=True)
            return False

    def delete_document(self, doc_id: str) -> bool:
        if not self._available:
            logger.warning("RAG engine not available, skipping delete_document")
            return False

        try:
            self._store.delete_by_metadata("doc_id", doc_id)
            logger.info(f"Deleted document chunks for doc_id={doc_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete document {doc_id}: {e}", exc_info=True)
            return False

    def query(
        self,
        query_text: str,
        user_id: int,
        top_k: Optional[int] = None,
    ) -> RAGQueryResponse:
        if not self._available:
            logger.warning("RAG engine not available, returning empty results")
            return RAGQueryResponse(results=[], query=query_text, total=0)

        k = top_k or self.similarity_top_k

        try:
            query_embedding = self._embed_model.get_text_embedding(query_text)

            vs_results = self._store.search(
                query_embedding=query_embedding,
                top_k=k,
                filter_metadata={"user_id": user_id},
            )

            rag_results = [
                RAGResult(content=r.content, score=r.score, metadata=r.metadata)
                for r in vs_results
            ]

            logger.info(
                f"RAG query for user {user_id}: '{query_text[:50]}...' "
                f"→ {len(rag_results)} results"
            )
            return RAGQueryResponse(
                results=rag_results, query=query_text, total=len(rag_results)
            )

        except Exception as e:
            logger.error(f"RAG query failed: {e}", exc_info=True)
            return RAGQueryResponse(results=[], query=query_text, total=0)

    def get_stats(self, user_id: Optional[int] = None) -> dict[str, Any]:
        if not self._available:
            return {
                "available": False,
                "total_chunks": 0,
                "backend": self._backend_name,
            }

        try:
            total_chunks = self._store.count()
            stats: dict[str, Any] = {
                "available": True,
                "total_chunks": total_chunks,
                "backend": self._backend_name,
            }

            if user_id is not None:
                user_filter = {"user_id": user_id}
                user_chunks = self._store.count(filter_metadata=user_filter)
                user_metas = self._store.get_metadatas(filter_metadata=user_filter)
                doc_ids = {m["doc_id"] for m in user_metas if "doc_id" in m}

                stats["user_chunks"] = user_chunks
                stats["user_documents"] = len(doc_ids)

            return stats

        except Exception as e:
            logger.error(f"Failed to get RAG stats: {e}", exc_info=True)
            return {"available": False, "total_chunks": 0, "error": str(e)}

    def _chunk_text(self, text: str) -> list[str]:
        if not text or not text.strip():
            return []

        text = text.strip()
        if len(text) <= self.chunk_size:
            return [text]

        chunks: list[str] = []
        start = 0

        while start < len(text):
            end = start + self.chunk_size

            if end < len(text):
                for sep in ["\n\n", "\n", "。", ".", "！", "!", "？", "?", "；", ";"]:
                    last_sep = text.rfind(sep, start + self.chunk_size // 2, end)
                    if last_sep != -1:
                        end = last_sep + len(sep)
                        break

            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)

            new_start = end - self.chunk_overlap
            if new_start <= start:
                new_start = end
            start = new_start

        return chunks


# ---------------------------------------------------------------------------
# Global singleton
# ---------------------------------------------------------------------------

_rag_engine: Optional[RAGEngine] = None


def get_rag_engine() -> Optional[RAGEngine]:
    """Get the global RAG engine instance."""
    return _rag_engine


def init_rag_engine(
    *,
    vector_store_type: str = "auto",
    database_url: str = "",
    persist_dir: str = "data/chroma",
    chunk_size: int = 512,
    chunk_overlap: int = 50,
    similarity_top_k: int = 3,
    embedding_model: str = "text-embedding-3-small",
    llm_api_key: str = "",
    llm_base_url: str = "https://api.openai.com/v1",
    embedding_api_key: str = "",
    embedding_base_url: str = "",
) -> RAGEngine:
    """Initialize the global RAG engine instance."""
    global _rag_engine
    _rag_engine = RAGEngine(
        vector_store_type=vector_store_type,
        database_url=database_url,
        persist_dir=persist_dir,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        similarity_top_k=similarity_top_k,
        embedding_model=embedding_model,
        llm_api_key=llm_api_key,
        llm_base_url=llm_base_url,
        embedding_api_key=embedding_api_key,
        embedding_base_url=embedding_base_url,
    )
    return _rag_engine
