"""
WebSocket Chat Server endpoint.

Provides real-time bidirectional chat with AI agents via WebSocket.

Protocol (JSON messages):
  Client → Server:
    { "type": "chat",       "message": "...", "session_id": "..." }
    { "type": "ping" }
    { "type": "new_session" }
    { "type": "list_sessions", "page": 1, "page_size": 20 }

  Server → Client:
    { "type": "token",       "content": "..." }
    { "type": "tool_call",   "tool": "...", "args": {...} }
    { "type": "tool_result", "tool": "...", "result": "..." }
    { "type": "agent_start", "agent": "..." }
    { "type": "agent_end",   "agent": "..." }
    { "type": "done",        "session_id": "...", "message_id": "..." }
    { "type": "error",       "content": "..." }
    { "type": "pong" }
    { "type": "session_created", "session_id": "...", "title": "..." }
    { "type": "sessions",   "sessions": [...], "total": N }
    { "type": "connected",  "user_id": N, "online_count": N }
"""

import json
import logging
import time
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.base import get_db
from app.models.chat_message import MessageRole
from app.models.user import User
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
from app.services.user_service import UserService

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# Connection Manager — tracks all active WebSocket connections
# ============================================================================


class ConnectionManager:
    """
    Manages active WebSocket connections.

    Provides:
    - Connection tracking per user
    - Broadcast to all / specific users
    - Online user count
    """

    def __init__(self):
        # user_id → list of WebSocket connections (one user can have multiple tabs)
        self._connections: dict[int, list[WebSocket]] = {}

    @property
    def online_count(self) -> int:
        """Number of unique online users."""
        return len(self._connections)

    @property
    def total_connections(self) -> int:
        """Total number of active WebSocket connections."""
        return sum(len(conns) for conns in self._connections.values())

    def connect(self, user_id: int, ws: WebSocket):
        if user_id not in self._connections:
            self._connections[user_id] = []
        self._connections[user_id].append(ws)
        logger.info(
            f"WS connected: user={user_id} "
            f"(connections={self.total_connections}, online={self.online_count})"
        )

    def disconnect(self, user_id: int, ws: WebSocket):
        if user_id in self._connections:
            try:
                self._connections[user_id].remove(ws)
            except ValueError:
                pass
            if not self._connections[user_id]:
                del self._connections[user_id]
        logger.info(
            f"WS disconnected: user={user_id} "
            f"(connections={self.total_connections}, online={self.online_count})"
        )

    async def send_json(self, ws: WebSocket, data: dict):
        """Send JSON to a specific connection."""
        try:
            await ws.send_json(data)
        except Exception as e:
            logger.warning(f"Failed to send WS message: {e}")

    async def broadcast(self, data: dict, exclude_user: Optional[int] = None):
        """Broadcast to all connected users (optionally excluding one)."""
        for uid, connections in self._connections.items():
            if uid == exclude_user:
                continue
            for ws in connections:
                await self.send_json(ws, data)

    async def send_to_user(self, user_id: int, data: dict):
        """Send to all connections of a specific user."""
        for ws in self._connections.get(user_id, []):
            await self.send_json(ws, data)

    def get_online_users(self) -> list[int]:
        return list(self._connections.keys())


# Singleton connection manager
manager = ConnectionManager()


# ============================================================================
# WebSocket Authentication
# ============================================================================


def authenticate_ws_token(token: str, db: Session) -> Optional[User]:
    """
    Authenticate a WebSocket connection via JWT token.

    Args:
        token: JWT access token (passed as query parameter)
        db: Database session

    Returns:
        User if valid, None otherwise
    """
    payload = decode_access_token(token)
    if not payload:
        return None

    user_id = payload.get("sub")
    if not user_id:
        return None

    user = UserService.get_user_by_id(db, int(user_id))
    if not user or not user.is_active:
        return None

    return user


# ============================================================================
# WebSocket Chat Endpoint
# ============================================================================


@router.websocket("/chat")
async def websocket_chat(
    websocket: WebSocket,
    token: str = Query(..., description="JWT access token"),
):
    """
    WebSocket endpoint for real-time AI chat.

    Connect: ws://host/api/v1/ws/chat?token=<jwt_token>

    Protocol:
      1. Client connects with JWT token as query parameter
      2. Server sends { type: "connected", user_id, online_count }
      3. Client sends JSON messages, server streams responses
      4. Heartbeat: client sends { type: "ping" }, server replies { type: "pong" }
    """
    # --- Authenticate ---
    # We need a DB session for auth; use a manual approach since
    # WebSocket endpoints don't support Depends(get_db) the same way.
    from app.db.session import SessionLocal

    db = SessionLocal()
    try:
        user = authenticate_ws_token(token, db)
        if not user:
            await websocket.close(code=4001, reason="Invalid or expired token")
            return
    except Exception as e:
        logger.error(f"WS auth error: {e}")
        await websocket.close(code=4001, reason="Authentication failed")
        return

    # --- Accept connection ---
    await websocket.accept()
    manager.connect(user.id, websocket)

    # Send welcome message
    await manager.send_json(
        websocket,
        {
            "type": "connected",
            "user_id": user.id,
            "user_name": user.full_name or user.email,
            "online_count": manager.online_count,
            "timestamp": datetime.now().isoformat(),
        },
    )

    try:
        # --- Message loop ---
        while True:
            raw = await websocket.receive_text()

            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                await manager.send_json(
                    websocket,
                    {
                        "type": "error",
                        "content": "Invalid JSON",
                    },
                )
                continue

            msg_type = data.get("type", "")

            if msg_type == "ping":
                await manager.send_json(websocket, {"type": "pong"})

            elif msg_type == "chat":
                await _handle_chat(websocket, data, user, db)

            elif msg_type == "new_session":
                await _handle_new_session(websocket, user, db)

            elif msg_type == "list_sessions":
                await _handle_list_sessions(websocket, data, user, db)

            elif msg_type == "get_session":
                await _handle_get_session(websocket, data, user, db)

            elif msg_type == "delete_session":
                await _handle_delete_session(websocket, data, user, db)

            else:
                await manager.send_json(
                    websocket,
                    {
                        "type": "error",
                        "content": f"Unknown message type: {msg_type}",
                    },
                )

    except WebSocketDisconnect:
        logger.info(f"WS client disconnected: user={user.id}")
    except Exception as e:
        logger.error(f"WS error for user={user.id}: {e}", exc_info=True)
        try:
            await manager.send_json(
                websocket,
                {
                    "type": "error",
                    "content": f"Server error: {str(e)}",
                },
            )
        except Exception:
            pass
    finally:
        manager.disconnect(user.id, websocket)
        db.close()


# ============================================================================
# Message Handlers
# ============================================================================


async def _handle_chat(
    ws: WebSocket,
    data: dict,
    user: User,
    db: Session,
):
    """
    Handle a chat message — stream AI response tokens back via WebSocket.
    """
    message = data.get("message", "").strip()
    if not message:
        await manager.send_json(
            ws,
            {
                "type": "error",
                "content": "Message cannot be empty",
            },
        )
        return

    session_id_str = data.get("session_id")
    start_time = time.time()

    try:
        # Get or create session
        if session_id_str:
            session_id = UUID(session_id_str)
            session = ChatService.get_session(db, session_id, user.id)
            if not session:
                await manager.send_json(
                    ws,
                    {
                        "type": "error",
                        "content": "Session not found",
                    },
                )
                return
        else:
            title = ChatService.generate_session_title(message)
            session = ChatService.create_session(db, user.id, title)
            record_session_created()
            # Notify client of new session
            await manager.send_json(
                ws,
                {
                    "type": "session_created",
                    "session_id": str(session.id),
                    "title": session.title,
                },
            )

        # Save user message
        ChatService.add_message(
            db=db,
            session_id=session.id,
            role=MessageRole.USER,
            content=message,
        )
        record_message("user")

        # Load chat history
        messages = ChatService.get_messages(db, session.id, limit=20)
        history = [
            {"role": msg.role.value, "content": msg.content} for msg in messages[:-1]
        ]

        # Create agent and stream response
        agent = SecretaryAgent(
            user_id=user.id,
            session_id=session.id,
            db=db,
        )

        full_content = ""
        tool_calls = []
        first_token_time = None

        stream_started()

        async for event in agent.chat_stream(message, history):
            event_type = event.get("type")

            if event_type == "token":
                if first_token_time is None:
                    first_token_time = time.time()
                    record_first_token_latency(first_token_time - start_time)

                full_content += event.get("content", "")
                await manager.send_json(ws, event)

            elif event_type == "tool_call":
                tool_calls.append(
                    {
                        "tool": event.get("tool"),
                        "args": event.get("args"),
                    }
                )
                await manager.send_json(ws, event)

            elif event_type == "tool_result":
                for tc in tool_calls:
                    if tc["tool"] == event.get("tool"):
                        tc["result"] = event.get("result")
                await manager.send_json(ws, event)

            elif event_type in ("agent_start", "agent_end"):
                await manager.send_json(ws, event)

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

                duration = time.time() - start_time
                record_chat_request("websocket", "success", duration)

                await manager.send_json(
                    ws,
                    {
                        "type": "done",
                        "session_id": str(session.id),
                        "message_id": str(assistant_msg.id),
                    },
                )

            elif event_type == "error":
                record_chat_error("ws_streaming_error")
                await manager.send_json(ws, event)

        stream_ended()

    except Exception as e:
        duration = time.time() - start_time
        record_chat_request("websocket", "error", duration)
        record_chat_error(type(e).__name__)
        logger.error(f"WS chat error: {e}", exc_info=True)
        await manager.send_json(
            ws,
            {
                "type": "error",
                "content": f"Chat error: {str(e)}",
            },
        )
        stream_ended()


async def _handle_new_session(ws: WebSocket, user: User, db: Session):
    """Create a new empty session."""
    session = ChatService.create_session(db, user.id, title=None)
    record_session_created()
    await manager.send_json(
        ws,
        {
            "type": "session_created",
            "session_id": str(session.id),
            "title": session.title,
        },
    )


async def _handle_list_sessions(
    ws: WebSocket,
    data: dict,
    user: User,
    db: Session,
):
    """List user's chat sessions."""
    page = data.get("page", 1)
    page_size = data.get("page_size", 20)
    offset = (page - 1) * page_size

    sessions, total = ChatService.list_sessions(
        db=db,
        user_id=user.id,
        limit=page_size,
        offset=offset,
    )

    await manager.send_json(
        ws,
        {
            "type": "sessions",
            "sessions": [
                {
                    "id": str(s.id),
                    "title": s.title,
                    "message_count": ChatService.get_message_count(db, s.id),
                    "created_at": s.created_at.isoformat(),
                    "updated_at": s.updated_at.isoformat(),
                }
                for s in sessions
            ],
            "total": total,
            "page": page,
            "page_size": page_size,
        },
    )


async def _handle_get_session(
    ws: WebSocket,
    data: dict,
    user: User,
    db: Session,
):
    """Get a session with its messages."""
    session_id_str = data.get("session_id")
    if not session_id_str:
        await manager.send_json(
            ws,
            {
                "type": "error",
                "content": "session_id is required",
            },
        )
        return

    session_id = UUID(session_id_str)
    session = ChatService.get_session(db, session_id, user.id)
    if not session:
        await manager.send_json(
            ws,
            {
                "type": "error",
                "content": "Session not found",
            },
        )
        return

    messages = ChatService.get_messages(db, session_id)

    await manager.send_json(
        ws,
        {
            "type": "session_detail",
            "session": {
                "id": str(session.id),
                "title": session.title,
                "messages": [
                    {
                        "id": str(m.id),
                        "role": m.role.value,
                        "content": m.content,
                        "tool_calls": m.tool_calls,
                        "tool_name": m.tool_name,
                        "created_at": m.created_at.isoformat(),
                    }
                    for m in messages
                ],
                "created_at": session.created_at.isoformat(),
                "updated_at": session.updated_at.isoformat(),
            },
        },
    )


async def _handle_delete_session(
    ws: WebSocket,
    data: dict,
    user: User,
    db: Session,
):
    """Delete a chat session."""
    session_id_str = data.get("session_id")
    if not session_id_str:
        await manager.send_json(
            ws,
            {
                "type": "error",
                "content": "session_id is required",
            },
        )
        return

    session_id = UUID(session_id_str)
    success = ChatService.delete_session(db, session_id, user.id)

    if success:
        await manager.send_json(
            ws,
            {
                "type": "session_deleted",
                "session_id": session_id_str,
            },
        )
    else:
        await manager.send_json(
            ws,
            {
                "type": "error",
                "content": "Session not found",
            },
        )


# ============================================================================
# REST endpoints for connection info (admin)
# ============================================================================


@router.get("/status")
async def ws_status():
    """Get WebSocket server status."""
    return {
        "online_users": manager.online_count,
        "total_connections": manager.total_connections,
        "online_user_ids": manager.get_online_users(),
        "timestamp": datetime.now().isoformat(),
    }
