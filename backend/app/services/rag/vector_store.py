"""Abstract vector store interface and implementations.

Provides a pluggable backend for the RAG engine:
- PgVectorStore: PostgreSQL with pgvector extension (production)
- ChromaVectorStore: ChromaDB embedded (development / standalone)
- Both share the same interface so the RAG engine is backend-agnostic.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger("rag.vector_store")


@dataclass
class VectorSearchResult:
    """A single vector search result."""

    chunk_id: str
    content: str
    score: float
    metadata: dict = field(default_factory=dict)


class BaseVectorStore(ABC):
    """Abstract interface for vector storage backends."""

    @abstractmethod
    def initialize(self) -> None:
        """Initialize the store. Raises on failure."""

    @property
    @abstractmethod
    def is_available(self) -> bool: ...

    @property
    @abstractmethod
    def backend_name(self) -> str: ...

    @abstractmethod
    def upsert_chunks(
        self,
        ids: list[str],
        texts: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict],
    ) -> None: ...

    @abstractmethod
    def delete_by_metadata(self, key: str, value: str) -> None: ...

    @abstractmethod
    def search(
        self,
        query_embedding: list[float],
        top_k: int,
        filter_metadata: Optional[dict] = None,
    ) -> list[VectorSearchResult]: ...

    @abstractmethod
    def count(self, filter_metadata: Optional[dict] = None) -> int: ...

    @abstractmethod
    def get_metadatas(self, filter_metadata: Optional[dict] = None) -> list[dict]:
        """Return metadata dicts for all matching chunks (for stats)."""
        ...


# ---------------------------------------------------------------------------
# ChromaDB backend
# ---------------------------------------------------------------------------


class ChromaVectorStore(BaseVectorStore):
    """ChromaDB-based vector store (embedded, on-disk)."""

    def __init__(self, persist_dir: str = "data/chroma"):
        self._persist_dir = persist_dir
        self._client = None
        self._collection = None
        self._ready = False

    def initialize(self) -> None:
        import chromadb
        from pathlib import Path

        Path(self._persist_dir).mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(path=self._persist_dir)
        self._collection = self._client.get_or_create_collection(
            name="knowledge_base",
            metadata={"hnsw:space": "cosine"},
        )
        self._ready = True
        logger.info(
            f"ChromaDB initialized: {self._persist_dir}, chunks={self._collection.count()}"
        )

    @property
    def is_available(self) -> bool:
        return self._ready

    @property
    def backend_name(self) -> str:
        return "chromadb"

    def upsert_chunks(self, ids, texts, embeddings, metadatas):
        self._collection.upsert(
            ids=ids, embeddings=embeddings, documents=texts, metadatas=metadatas
        )

    def delete_by_metadata(self, key: str, value: str) -> None:
        self._collection.delete(where={key: value})

    def search(self, query_embedding, top_k, filter_metadata=None):
        kwargs: dict[str, Any] = {
            "query_embeddings": [query_embedding],
            "n_results": top_k,
            "include": ["documents", "metadatas", "distances"],
        }
        if filter_metadata:
            kwargs["where"] = {k: str(v) for k, v in filter_metadata.items()}

        results = self._collection.query(**kwargs)

        out: list[VectorSearchResult] = []
        if results and results["documents"] and results["documents"][0]:
            for i, doc in enumerate(results["documents"][0]):
                meta = results["metadatas"][0][i] if results["metadatas"] else {}
                distance = results["distances"][0][i] if results["distances"] else 1.0
                out.append(
                    VectorSearchResult(
                        chunk_id=results["ids"][0][i] if results["ids"] else "",
                        content=doc,
                        score=1.0 - distance,
                        metadata=meta,
                    )
                )
        return out

    def count(self, filter_metadata=None):
        if filter_metadata:
            where = {k: str(v) for k, v in filter_metadata.items()}
            res = self._collection.get(where=where, include=[])
            return len(res["ids"]) if res["ids"] else 0
        return self._collection.count()

    def get_metadatas(self, filter_metadata=None):
        where = (
            {k: str(v) for k, v in filter_metadata.items()} if filter_metadata else None
        )
        kwargs: dict[str, Any] = {"include": ["metadatas"]}
        if where:
            kwargs["where"] = where
        res = self._collection.get(**kwargs)
        return res["metadatas"] if res["metadatas"] else []


# ---------------------------------------------------------------------------
# pgvector backend
# ---------------------------------------------------------------------------


class PgVectorStore(BaseVectorStore):
    """PostgreSQL + pgvector based vector store.

    Uses a dedicated ``document_chunks`` table with a ``vector`` column.
    Requires the pgvector extension (``CREATE EXTENSION IF NOT EXISTS vector``).
    """

    def __init__(self, database_url: str):
        self._database_url = database_url
        self._ready = False
        self._engine = None

    def initialize(self) -> None:
        from sqlalchemy import create_engine, text

        self._engine = create_engine(self._database_url)

        with self._engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.execute(
                text(
                    """
                CREATE TABLE IF NOT EXISTS document_chunks (
                    id TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    embedding vector,
                    doc_id TEXT NOT NULL,
                    title TEXT,
                    user_id TEXT NOT NULL,
                    chunk_index INTEGER NOT NULL DEFAULT 0
                )
            """
                )
            )
            conn.execute(
                text(
                    """
                CREATE INDEX IF NOT EXISTS idx_chunks_user_id ON document_chunks (user_id)
            """
                )
            )
            conn.execute(
                text(
                    """
                CREATE INDEX IF NOT EXISTS idx_chunks_doc_id ON document_chunks (doc_id)
            """
                )
            )
            conn.commit()

        self._ready = True
        logger.info("pgvector store initialized")

    @property
    def is_available(self) -> bool:
        return self._ready

    @property
    def backend_name(self) -> str:
        return "pgvector"

    def upsert_chunks(self, ids, texts, embeddings, metadatas):
        from sqlalchemy import text

        with self._engine.connect() as conn:
            for chunk_id, content, emb, meta in zip(ids, texts, embeddings, metadatas):
                emb_str = "[" + ",".join(str(x) for x in emb) + "]"
                conn.execute(
                    text(
                        """
                        INSERT INTO document_chunks (id, content, embedding, doc_id, title, user_id, chunk_index)
                        VALUES (:id, :content, :embedding::vector, :doc_id, :title, :user_id, :chunk_index)
                        ON CONFLICT (id) DO UPDATE SET
                            content = EXCLUDED.content,
                            embedding = EXCLUDED.embedding,
                            title = EXCLUDED.title
                    """
                    ),
                    {
                        "id": chunk_id,
                        "content": content,
                        "embedding": emb_str,
                        "doc_id": meta.get("doc_id", ""),
                        "title": meta.get("title", ""),
                        "user_id": str(meta.get("user_id", "")),
                        "chunk_index": meta.get("chunk_index", 0),
                    },
                )
            conn.commit()

    def delete_by_metadata(self, key: str, value: str) -> None:
        from sqlalchemy import text

        col_map = {"doc_id": "doc_id", "user_id": "user_id"}
        col = col_map.get(key, key)
        with self._engine.connect() as conn:
            conn.execute(
                text(f"DELETE FROM document_chunks WHERE {col} = :val"), {"val": value}
            )
            conn.commit()

    def search(self, query_embedding, top_k, filter_metadata=None):
        from sqlalchemy import text

        emb_str = "[" + ",".join(str(x) for x in query_embedding) + "]"
        where_clauses = []
        params: dict[str, Any] = {"emb": emb_str, "k": top_k}

        if filter_metadata:
            for fk, fv in filter_metadata.items():
                col = fk if fk in ("doc_id", "user_id", "title") else fk
                where_clauses.append(f"{col} = :{fk}")
                params[fk] = str(fv)

        where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

        sql = f"""
            SELECT id, content, doc_id, title, user_id, chunk_index,
                   1 - (embedding <=> :emb::vector) AS score
            FROM document_chunks
            {where_sql}
            ORDER BY embedding <=> :emb::vector
            LIMIT :k
        """

        with self._engine.connect() as conn:
            rows = conn.execute(text(sql), params).fetchall()

        return [
            VectorSearchResult(
                chunk_id=row[0],
                content=row[1],
                score=float(row[6]),
                metadata={
                    "doc_id": row[2],
                    "title": row[3],
                    "user_id": row[4],
                    "chunk_index": row[5],
                },
            )
            for row in rows
        ]

    def count(self, filter_metadata=None):
        from sqlalchemy import text

        params: dict[str, Any] = {}
        where_parts = []
        if filter_metadata:
            for fk, fv in filter_metadata.items():
                where_parts.append(f"{fk} = :{fk}")
                params[fk] = str(fv)
        where_sql = ("WHERE " + " AND ".join(where_parts)) if where_parts else ""
        sql = f"SELECT COUNT(*) FROM document_chunks {where_sql}"

        with self._engine.connect() as conn:
            return conn.execute(text(sql), params).scalar() or 0

    def get_metadatas(self, filter_metadata=None):
        from sqlalchemy import text

        params: dict[str, Any] = {}
        where_parts = []
        if filter_metadata:
            for fk, fv in filter_metadata.items():
                where_parts.append(f"{fk} = :{fk}")
                params[fk] = str(fv)
        where_sql = ("WHERE " + " AND ".join(where_parts)) if where_parts else ""
        sql = f"SELECT doc_id, title, user_id, chunk_index FROM document_chunks {where_sql}"

        with self._engine.connect() as conn:
            rows = conn.execute(text(sql), params).fetchall()

        return [
            {"doc_id": r[0], "title": r[1], "user_id": r[2], "chunk_index": r[3]}
            for r in rows
        ]
