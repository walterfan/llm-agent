"""Memory API endpoints for agents created by factory."""

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.api.deps import get_current_active_user
from app.models.user import User
from app.services.memory import FileMemoryBackend, Memory

router = APIRouter()
memory_backend = FileMemoryBackend()


class AddMemoryRequest(BaseModel):
    """Request to add a memory."""

    content: str
    metadata: Optional[dict] = None


class SearchMemoryRequest(BaseModel):
    """Request to search memories."""

    query: str
    limit: int = 5


class MemoryResponse(BaseModel):
    """Response containing memories."""

    memories: list[Memory]
    total: int


@router.post("/agents/{agent_id}/memories", response_model=Memory)
def add_memory(
    agent_id: str,
    request: AddMemoryRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """Add a memory for an agent.

    Only accessible by authenticated users.
    """
    memory = memory_backend.add_memory(
        agent_id=agent_id,
        content=request.content,
        metadata={
            **(request.metadata or {}),
            "user_id": current_user.id,
            "user_email": current_user.email,
        },
    )
    return memory


@router.get("/agents/{agent_id}/memories", response_model=MemoryResponse)
def list_memories(
    agent_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    limit: int = Query(10, ge=1, le=100),
):
    """Get recent memories for an agent."""
    memories = memory_backend.get_recent_memories(agent_id, limit=limit)
    total = memory_backend.count_memories(agent_id)
    return MemoryResponse(memories=memories, total=total)


@router.post("/agents/{agent_id}/memories/search", response_model=MemoryResponse)
def search_memories(
    agent_id: str,
    request: SearchMemoryRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """Search memories for an agent using ripgrep/grep."""
    memories = memory_backend.search_memories(
        agent_id=agent_id, query=request.query, limit=request.limit
    )
    total = memory_backend.count_memories(agent_id)
    return MemoryResponse(memories=memories, total=total)


@router.get("/agents/{agent_id}/memories/count")
def count_memories(
    agent_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """Get total memory count for an agent."""
    count = memory_backend.count_memories(agent_id)
    return {"agent_id": agent_id, "count": count}


@router.delete("/agents/{agent_id}/memories", status_code=204)
def clear_memories(
    agent_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """Clear all memories for an agent.

    Warning: This operation cannot be undone!
    """
    memory_backend.clear_memories(agent_id)
    return None
