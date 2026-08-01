"""File-based long-term memory for agents.

Simple, lightweight alternative to vector databases. Stores memories as JSON files
and uses keyword-based retrieval.

Storage structure:
    data/agent_memory/<agent_id>/
        memories.jsonl    - One memory per line (append-only)
        index.json        - Quick lookup index (timestamps, keywords)
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel


class Memory(BaseModel):
    """A single memory entry."""

    id: str
    timestamp: str
    content: str
    metadata: dict = {}
    keywords: List[str] = []


class FileMemoryBackend:
    """File-based memory storage for agents."""

    def __init__(self, base_dir: str = "data/agent_memory"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _agent_dir(self, agent_id: str) -> Path:
        """Get storage directory for an agent."""
        agent_dir = self.base_dir / f"agent_{agent_id}"
        agent_dir.mkdir(parents=True, exist_ok=True)
        return agent_dir

    def _memories_file(self, agent_id: str) -> Path:
        """Get path to memories.jsonl file."""
        return self._agent_dir(agent_id) / "memories.jsonl"

    def add_memory(
        self,
        agent_id: str,
        content: str,
        metadata: Optional[dict] = None,
        keywords: Optional[List[str]] = None,
    ) -> Memory:
        """Store a new memory for an agent.

        Args:
            agent_id: The agent's ID
            content: The memory content (user message, agent response, observation)
            metadata: Optional metadata (user_id, session_id, etc.)
            keywords: Optional keywords for quick retrieval

        Returns:
            The created Memory object
        """
        memory = Memory(
            id=f"{agent_id}_{datetime.utcnow().timestamp()}",
            timestamp=datetime.utcnow().isoformat(),
            content=content,
            metadata=metadata or {},
            keywords=keywords or self._extract_keywords(content),
        )

        # Append to JSONL file
        memories_file = self._memories_file(agent_id)
        with open(memories_file, "a", encoding="utf-8") as f:
            f.write(memory.model_dump_json() + "\n")

        return memory

    def search_memories(
        self, agent_id: str, query: str, limit: int = 5
    ) -> List[Memory]:
        """Search memories for an agent using ripgrep (fast) or fallback to grep.

        Args:
            agent_id: The agent's ID
            query: Search query
            limit: Maximum number of results

        Returns:
            List of matching memories, sorted by relevance
        """
        import subprocess
        import shutil

        memories_file = self._memories_file(agent_id)
        if not memories_file.exists():
            return []

        # Try using ripgrep (rg) first, fall back to grep
        grep_cmd = None
        if shutil.which("rg"):
            # ripgrep: faster, case-insensitive, show context
            grep_cmd = ["rg", "-i", "-N", query, str(memories_file)]
        elif shutil.which("grep"):
            # standard grep fallback
            grep_cmd = ["grep", "-i", query, str(memories_file)]

        matches = []

        if grep_cmd:
            try:
                result = subprocess.run(
                    grep_cmd, capture_output=True, text=True, timeout=5
                )
                # Parse matching lines
                for line in result.stdout.splitlines():
                    if line.strip():
                        try:
                            memory = Memory.model_validate_json(line)
                            # Simple scoring: exact match in content
                            score = 1
                            if query.lower() in memory.content.lower():
                                score = 10
                            matches.append((score, memory))
                        except Exception:
                            continue
            except (subprocess.TimeoutExpired, Exception):
                pass  # Fall back to Python implementation below

        # Fallback: Python-based search if grep fails or no results
        if not matches:
            query_lower = query.lower()
            with open(memories_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip() and query_lower in line.lower():
                        try:
                            memory = Memory.model_validate_json(line)
                            score = 10 if query_lower in memory.content.lower() else 1
                            matches.append((score, memory))
                        except Exception:
                            continue

        # Sort by score and return top results
        matches.sort(key=lambda x: (x[0], x[1].timestamp), reverse=True)
        return [m for _, m in matches[:limit]]

    def get_recent_memories(self, agent_id: str, limit: int = 10) -> List[Memory]:
        """Get the most recent memories for an agent.

        Args:
            agent_id: The agent's ID
            limit: Maximum number of memories to return

        Returns:
            List of recent memories, newest first
        """
        memories_file = self._memories_file(agent_id)
        if not memories_file.exists():
            return []

        memories = []
        with open(memories_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    memories.append(Memory.model_validate_json(line))

        # Return most recent
        return memories[-limit:][::-1]

    def clear_memories(self, agent_id: str) -> None:
        """Delete all memories for an agent.

        Args:
            agent_id: The agent's ID
        """
        memories_file = self._memories_file(agent_id)
        if memories_file.exists():
            memories_file.unlink()

    def count_memories(self, agent_id: str) -> int:
        """Count total memories for an agent.

        Args:
            agent_id: The agent's ID

        Returns:
            Number of stored memories
        """
        memories_file = self._memories_file(agent_id)
        if not memories_file.exists():
            return 0

        with open(memories_file, "r", encoding="utf-8") as f:
            return sum(1 for line in f if line.strip())

    @staticmethod
    def _extract_keywords(text: str) -> List[str]:
        """Extract keywords from text for indexing.

        Simple implementation: lowercase, remove common words, split on spaces.
        Could be enhanced with proper NLP/stemming.

        Args:
            text: Input text

        Returns:
            List of keywords
        """
        # Common stop words to filter out
        stop_words = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "is",
            "was",
            "are",
            "were",
            "been",
            "be",
            "have",
            "has",
            "had",
            "do",
            "does",
            "did",
            "will",
            "would",
            "could",
            "should",
            "may",
            "might",
            "can",
            "this",
            "that",
            "these",
            "those",
            "i",
            "you",
            "he",
            "she",
            "it",
            "we",
            "they",
            "what",
            "which",
            "who",
            "when",
            "where",
            "why",
            "how",
            "的",
            "是",
            "在",
            "了",
            "和",
            "有",
            "我",
            "你",
            "他",
        }

        # Simple tokenization
        words = text.lower().split()
        keywords = [
            w.strip(".,!?;:\"'()[]{}")
            for w in words
            if len(w) > 2 and w.lower() not in stop_words
        ]

        # Remove duplicates while preserving order
        seen = set()
        unique_keywords = []
        for k in keywords:
            if k not in seen:
                seen.add(k)
                unique_keywords.append(k)

        return unique_keywords[:20]  # Limit to 20 keywords
