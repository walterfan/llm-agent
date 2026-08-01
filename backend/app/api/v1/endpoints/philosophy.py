"""
API endpoints for Philosophy Master agent.

Provides endpoints for:
- Non-streaming chat
- Streaming chat (SSE)
"""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.api.deps import get_current_active_user
from app.models.user import User
from app.schemas.philosophy import PhilosophyChatRequest, PhilosophyChatResponse
from app.services.philosophy_master_agent import PhilosophyMasterService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/chat", response_model=PhilosophyChatResponse)
async def chat(
    request: PhilosophyChatRequest,
    current_user: User = Depends(get_current_active_user),
):
    if not request.message or not request.message.strip():
        raise HTTPException(
            status_code=400, detail="message must be a non-empty string"
        )
    try:
        service = PhilosophyMasterService()
        return await service.chat(request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.exception("Philosophy chat failed: %s", e)
        raise HTTPException(
            status_code=500, detail="Philosophy Master failed. Please try again."
        ) from e


@router.post("/chat/stream")
async def chat_stream(
    request: PhilosophyChatRequest,
    current_user: User = Depends(get_current_active_user),
):
    if not request.message or not request.message.strip():
        raise HTTPException(
            status_code=400, detail="message must be a non-empty string"
        )

    async def event_generator():
        try:
            service = PhilosophyMasterService()
            async for ev in service.chat_stream(request):
                yield f"data: {json.dumps(ev, ensure_ascii=False)}\n\n"
        except ValueError as e:
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)}, ensure_ascii=False)}\n\n"
        except Exception as e:
            logger.exception("Philosophy stream failed: %s", e)
            yield f"data: {json.dumps({'type': 'error', 'content': 'Philosophy Master failed. Please try again.'}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )
