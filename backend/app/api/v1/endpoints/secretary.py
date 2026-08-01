"""
API endpoints for the Personal Secretary agent.

Provides endpoints for:
- Chat with streaming support (SSE)
- Session management
- Tool discovery
"""

import json
import logging
import time
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, get_db
from app.models.chat_message import MessageRole
from app.models.user import User
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    MessageResponse,
    SessionDetailResponse,
    SessionListResponse,
    SessionResponse,
    ToolInfo,
    ToolListResponse,
)
from app.services.chat_service import ChatService
from app.services.secretary_agent.agent import SecretaryAgent
from app.services.secretary_agent.metrics import (
    record_chat_request,
    record_chat_error,
    record_first_token_latency,
    record_session_created,
    record_message,
    stream_started,
    stream_ended,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# ============================================================================
# Chat Endpoints
# ============================================================================


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Send a message to the Personal Secretary agent.

    If session_id is not provided, creates a new session.
    Returns the complete response (non-streaming).
    """
    start_time = time.time()
    is_new_session = False

    try:
        # Get or create session
        if request.session_id:
            session = ChatService.get_session(db, request.session_id, current_user.id)
            if not session:
                raise HTTPException(status_code=404, detail="Session not found")
        else:
            # Auto-generate title from first message
            title = ChatService.generate_session_title(request.message)
            session = ChatService.create_session(db, current_user.id, title)
            is_new_session = True
            record_session_created()

        # Save user message
        user_msg = ChatService.add_message(
            db=db,
            session_id=session.id,
            role=MessageRole.USER,
            content=request.message,
        )
        record_message("user")

        # Load chat history
        messages = ChatService.get_messages(db, session.id, limit=20)
        history = [
            {"role": msg.role.value, "content": msg.content}
            for msg in messages[:-1]  # Exclude the message we just added
        ]

        # Create agent and get response
        agent = SecretaryAgent(
            user_id=current_user.id,
            session_id=session.id,
            db=db,
        )

        result = await agent.chat(request.message, history)

        # Save assistant response
        assistant_msg = ChatService.add_message(
            db=db,
            session_id=session.id,
            role=MessageRole.ASSISTANT,
            content=result["content"],
            tool_calls=result.get("tool_calls"),
        )
        record_message("assistant")

        # Record success metrics
        duration = time.time() - start_time
        record_chat_request("non-streaming", "success", duration)

        return ChatResponse(
            session_id=session.id,
            message_id=assistant_msg.id,
            content=result["content"],
            tool_calls=result.get("tool_calls", []),
            created_at=assistant_msg.created_at,
        )
    except Exception as e:
        # Record error metrics
        duration = time.time() - start_time
        record_chat_request("non-streaming", "error", duration)
        record_chat_error(type(e).__name__)
        raise


@router.post("/chat/stream")
async def chat_stream(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Send a message to the Personal Secretary agent with streaming response.

    Returns Server-Sent Events (SSE) with:
    - type: "token" - streaming token
    - type: "tool_call" - tool being called
    - type: "tool_result" - tool execution result
    - type: "done" - completion with session_id
    - type: "error" - error occurred
    """
    is_new_session = False

    # Get or create session
    if request.session_id:
        session = ChatService.get_session(db, request.session_id, current_user.id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
    else:
        title = ChatService.generate_session_title(request.message)
        session = ChatService.create_session(db, current_user.id, title)
        is_new_session = True
        record_session_created()

    # Save user message
    ChatService.add_message(
        db=db,
        session_id=session.id,
        role=MessageRole.USER,
        content=request.message,
    )
    record_message("user")

    # Load chat history
    messages = ChatService.get_messages(db, session.id, limit=20)
    history = [
        {"role": msg.role.value, "content": msg.content} for msg in messages[:-1]
    ]

    # Create agent
    agent = SecretaryAgent(
        user_id=current_user.id,
        session_id=session.id,
        db=db,
    )

    async def event_generator():
        """Generate SSE events from agent stream."""
        start_time = time.time()
        first_token_time = None
        full_content = ""
        tool_calls = []

        stream_started()

        try:
            async for event in agent.chat_stream(request.message, history):
                event_type = event.get("type")

                if event_type == "token":
                    # Record first token latency
                    if first_token_time is None:
                        first_token_time = time.time()
                        record_first_token_latency(first_token_time - start_time)

                    full_content += event.get("content", "")
                    yield f"data: {json.dumps(event)}\n\n"

                elif event_type == "tool_call":
                    tool_calls.append(
                        {
                            "tool": event.get("tool"),
                            "args": event.get("args"),
                        }
                    )
                    yield f"data: {json.dumps(event)}\n\n"

                elif event_type == "tool_result":
                    # Update tool call with result
                    for tc in tool_calls:
                        if tc["tool"] == event.get("tool"):
                            tc["result"] = event.get("result")
                    yield f"data: {json.dumps(event)}\n\n"

                elif event_type == "done":
                    # Save assistant response
                    assistant_msg = ChatService.add_message(
                        db=db,
                        session_id=session.id,
                        role=MessageRole.ASSISTANT,
                        content=full_content,
                        tool_calls=tool_calls if tool_calls else None,
                    )
                    record_message("assistant")

                    # Record success metrics
                    duration = time.time() - start_time
                    record_chat_request("streaming", "success", duration)

                    yield f"data: {json.dumps({'type': 'done', 'session_id': str(session.id), 'message_id': str(assistant_msg.id)})}\n\n"

                elif event_type == "error":
                    record_chat_error("streaming_error")
                    yield f"data: {json.dumps(event)}\n\n"

        except Exception as e:
            logger.error(f"Streaming error: {e}", exc_info=True)
            duration = time.time() - start_time
            record_chat_request("streaming", "error", duration)
            record_chat_error(type(e).__name__)
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"

        finally:
            stream_ended()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


# ============================================================================
# Session Endpoints
# ============================================================================


@router.get("/sessions", response_model=SessionListResponse)
async def list_sessions(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List user's chat sessions."""
    offset = (page - 1) * page_size
    sessions, total = ChatService.list_sessions(
        db=db,
        user_id=current_user.id,
        limit=page_size,
        offset=offset,
    )

    return SessionListResponse(
        sessions=[
            SessionResponse(
                id=s.id,
                title=s.title,
                message_count=ChatService.get_message_count(db, s.id),
                created_at=s.created_at,
                updated_at=s.updated_at,
            )
            for s in sessions
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/sessions/{session_id}", response_model=SessionDetailResponse)
async def get_session(
    session_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get a chat session with its messages."""
    session = ChatService.get_session(db, session_id, current_user.id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    messages = ChatService.get_messages(db, session_id)

    return SessionDetailResponse(
        id=session.id,
        title=session.title,
        messages=[
            MessageResponse(
                id=m.id,
                role=m.role.value,
                content=m.content,
                tool_calls=m.tool_calls,
                tool_name=m.tool_name,
                created_at=m.created_at,
            )
            for m in messages
        ],
        created_at=session.created_at,
        updated_at=session.updated_at,
    )


@router.delete("/sessions/{session_id}", status_code=204)
async def delete_session(
    session_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Delete a chat session."""
    success = ChatService.delete_session(db, session_id, current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return None


# ============================================================================
# Tool Discovery
# ============================================================================


@router.get("/tools", response_model=ToolListResponse)
async def list_tools(
    current_user: User = Depends(get_current_active_user),
):
    """List available tools for the Personal Secretary agent."""
    tools = [
        # Learning tools
        ToolInfo(
            name="learn_word",
            description="Learn an English word with Chinese explanation, pronunciation, and examples",
            category="learning",
        ),
        ToolInfo(
            name="learn_sentence",
            description="Learn an English sentence with translation, grammar notes, and context",
            category="learning",
        ),
        ToolInfo(
            name="learn_topic",
            description="Get a structured learning plan for a tech topic",
            category="learning",
        ),
        ToolInfo(
            name="learn_article",
            description="Learn from a web article: fetch, translate, and generate mindmap",
            category="learning",
        ),
        ToolInfo(
            name="save_learning",
            description="Save a learning record to your learning history",
            category="learning",
        ),
        ToolInfo(
            name="list_learning",
            description="View your saved learning records",
            category="learning",
        ),
        # Note tools
        ToolInfo(
            name="save_note",
            description="Save a note or memo",
            category="notes",
        ),
        ToolInfo(
            name="search_notes",
            description="Search through your saved notes",
            category="notes",
        ),
        ToolInfo(
            name="list_notes",
            description="List all your notes",
            category="notes",
        ),
        # Task tools
        ToolInfo(
            name="create_task",
            description="Create a to-do task with priority and due date",
            category="tasks",
        ),
        ToolInfo(
            name="list_tasks",
            description="List your to-do tasks",
            category="tasks",
        ),
        ToolInfo(
            name="complete_task",
            description="Mark a task as completed",
            category="tasks",
        ),
        # Reminder tools
        ToolInfo(
            name="create_reminder",
            description="Set a reminder for a specific time",
            category="reminders",
        ),
        ToolInfo(
            name="list_reminders",
            description="List your reminders",
            category="reminders",
        ),
        # Utility tools
        ToolInfo(
            name="calculate",
            description="Evaluate mathematical expressions",
            category="utility",
        ),
        ToolInfo(
            name="get_datetime",
            description="Get current date and time",
            category="utility",
        ),
        ToolInfo(
            name="get_weather",
            description="Get current weather for a city",
            category="utility",
        ),
    ]

    return ToolListResponse(tools=tools)
