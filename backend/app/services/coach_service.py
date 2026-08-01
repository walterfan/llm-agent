"""
Coach Service — handles coach chat logic with RAG context injection.

Provides both non-streaming and streaming coach responses with:
- 3 coaching modes (coach/tutor/quiz)
- RAG knowledge base context injection
- Learning progress awareness
- Session continuity (load/save conversation history)
"""

import logging
from datetime import datetime
from typing import Any, AsyncIterator, Optional
from uuid import UUID, uuid4

import httpx
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.chat_message import MessageRole
from app.models.chat_session import ChatSession
from app.models.learning_goal import GoalStatus, LearningGoal
from app.models.study_session import StudySession
from app.schemas.coach import CoachMode
from app.services.chat_service import ChatService
from app.services.rag.engine import get_rag_engine

logger = logging.getLogger("coach_service")

# Maximum number of history messages to load for context
MAX_HISTORY_MESSAGES = 20


# System prompts for each coaching mode
COACH_PROMPTS = {
    CoachMode.COACH: """你是一位专业的学习教练（Learning Coach）。你的职责是：
- 激励用户坚持学习，保持积极心态
- 根据用户的学习进度给出个性化建议
- 帮助用户制定和调整学习计划
- 在用户遇到困难时提供鼓励和方法指导

{rag_context}
{progress_context}

请用温暖、鼓励的语气回复。如果有知识库内容可以参考，请基于这些内容回答。
回复使用中文。""",
    CoachMode.TUTOR: """你是一位耐心的学习导师（Tutor）。你的职责是：
- 深入讲解用户提问的知识点
- 用通俗易懂的方式解释复杂概念
- 提供相关的例子和类比
- 引导用户思考，而不是直接给出所有答案

{rag_context}

如果有知识库中的相关内容，请优先基于这些内容进行讲解，并标注来源。
如果知识库中没有相关内容，请基于你的知识回答，但要说明这不是来自用户的知识库。
回复使用中文。""",
    CoachMode.QUIZ: """你是一位学习测验官（Quiz Master）。你的职责是：
- 根据用户的学习内容出题测验
- 题目类型包括：选择题、填空题、简答题、判断题
- 每次出 1-3 道题
- 用户回答后给出详细的评分和解析
- 根据答题情况调整难度

{rag_context}

如果有知识库内容，请基于这些内容出题。
如果用户没有指定主题，请询问要测验的主题。
回复使用中文。""",
}


def _build_rag_context(user_id: int, message: str) -> str:
    """Build RAG context by querying the knowledge base."""
    rag = get_rag_engine()
    if not rag or not rag.is_available:
        return ""

    response = rag.query(query_text=message, user_id=user_id, top_k=3)
    if not response.results:
        return ""

    context_parts = ["📚 相关知识库内容:"]
    for i, r in enumerate(response.results, 1):
        title = r.metadata.get("title", "未知文档")
        context_parts.append(f"\n[{i}] 来源: {title} (相关度: {r.score:.2f})")
        context_parts.append(r.content[:500])

    return "\n".join(context_parts)


def _build_progress_context(user_id: int, goal_id: Optional[str], db: Session) -> str:
    """Build learning progress context."""
    if not db:
        return ""

    try:
        # Get active goals
        goals_query = db.query(LearningGoal).filter(
            LearningGoal.user_id == user_id,
            LearningGoal.status == GoalStatus.ACTIVE,
        )

        if goal_id:
            goals_query = goals_query.filter(LearningGoal.id == goal_id)

        goals = goals_query.all()
        if not goals:
            return ""

        parts = ["📊 当前学习进度:"]
        for goal in goals[:3]:  # Limit to 3 goals
            sessions = (
                db.query(StudySession).filter(StudySession.goal_id == goal.id).all()
            )
            total_minutes = sum(s.duration_minutes for s in sessions)
            total_sessions = len(sessions)

            parts.append(
                f"\n- 目标: {goal.subject}"
                f"\n  已学习 {total_sessions} 次，共 {total_minutes} 分钟"
                f"\n  每日目标: {goal.daily_target_minutes} 分钟"
            )
            if goal.deadline:
                remaining = (goal.deadline - datetime.utcnow()).days
                parts.append(f"  剩余 {max(0, remaining)} 天")

        return "\n".join(parts)

    except Exception as e:
        logger.warning(f"Failed to build progress context: {e}")
        return ""


def _build_system_prompt(
    mode: CoachMode,
    user_id: int,
    message: str,
    goal_id: Optional[str],
    db: Session,
) -> str:
    """Build the full system prompt with RAG and progress context."""
    template = COACH_PROMPTS.get(mode, COACH_PROMPTS[CoachMode.COACH])

    rag_context = _build_rag_context(user_id, message)
    progress_context = ""
    if mode == CoachMode.COACH:
        progress_context = _build_progress_context(user_id, goal_id, db)

    return template.format(
        rag_context=rag_context,
        progress_context=progress_context,
    )


def _create_llm(streaming: bool = False) -> ChatOpenAI:
    """Create LLM instance."""
    http_client = httpx.AsyncClient(
        verify=getattr(settings, "LLM_VERIFY_SSL", True),
        timeout=httpx.Timeout(timeout=getattr(settings, "LLM_TIMEOUT", 60.0)),
    )
    return ChatOpenAI(
        model=settings.LLM_MODEL,
        openai_api_key=settings.LLM_API_KEY,
        openai_api_base=settings.LLM_BASE_URL,
        temperature=0.7,
        streaming=streaming,
        http_async_client=http_client,
    )


def _load_conversation_history(
    db: Session,
    session_id: UUID,
    user_id: int,
) -> list:
    """
    Load conversation history from a chat session.

    Returns a list of LangChain message objects (HumanMessage / AIMessage)
    for the most recent MAX_HISTORY_MESSAGES messages.
    """
    try:
        session = ChatService.get_session(db, session_id, user_id)
        if not session:
            return []

        messages = ChatService.get_messages(db, session_id, limit=MAX_HISTORY_MESSAGES)

        history = []
        for msg in messages:
            if msg.role == MessageRole.USER:
                history.append(HumanMessage(content=msg.content or ""))
            elif msg.role == MessageRole.ASSISTANT:
                history.append(AIMessage(content=msg.content or ""))
            # Skip tool and system messages for coach context

        return history

    except Exception as e:
        logger.warning(
            f"Failed to load conversation history for session {session_id}: {e}"
        )
        return []


def _get_or_create_session(
    db: Session,
    session_id: Optional[str],
    user_id: int,
    first_message: str,
) -> tuple[UUID, bool]:
    """
    Get an existing session or create a new one.

    Returns:
        (session_uuid, is_new) — the session UUID and whether it was newly created.
    """
    if session_id:
        try:
            sid = UUID(session_id)
            existing = ChatService.get_session(db, sid, user_id)
            if existing:
                return sid, False
        except (ValueError, AttributeError):
            logger.warning(f"Invalid session_id format: {session_id}")

    # Create new session
    title = ChatService.generate_session_title(first_message)
    new_session = ChatService.create_session(db, user_id, title=f"🎓 {title}")
    return new_session.id, True


def _save_user_message(db: Session, session_id: UUID, content: str) -> None:
    """Save a user message to the session."""
    try:
        ChatService.add_message(
            db=db,
            session_id=session_id,
            role=MessageRole.USER,
            content=content,
        )
    except Exception as e:
        logger.warning(f"Failed to save user message: {e}")


def _save_assistant_message(db: Session, session_id: UUID, content: str) -> None:
    """Save an assistant message to the session."""
    try:
        ChatService.add_message(
            db=db,
            session_id=session_id,
            role=MessageRole.ASSISTANT,
            content=content,
        )
    except Exception as e:
        logger.warning(f"Failed to save assistant message: {e}")


async def get_coach_response(
    message: str,
    mode: CoachMode,
    user_id: int,
    session_id: Optional[str] = None,
    goal_id: Optional[str] = None,
    db: Optional[Session] = None,
) -> dict[str, Any]:
    """
    Get a non-streaming coach response with session continuity.

    If session_id is provided, loads conversation history for context.
    Creates a new session if session_id is None or invalid.
    Saves both user message and assistant response to the session.

    Returns:
        Dict with 'content', 'sources', 'session_id'
    """
    # Get or create session
    sid = None
    if db:
        sid, is_new = _get_or_create_session(db, session_id, user_id, message)
        # Save user message
        _save_user_message(db, sid, message)

    system_prompt = _build_system_prompt(mode, user_id, message, goal_id, db)

    # Build messages with history
    messages = [SystemMessage(content=system_prompt)]

    # Load conversation history if we have a session
    if db and sid:
        history = _load_conversation_history(db, sid, user_id)
        # Exclude the last message (which is the one we just saved)
        if history and len(history) > 1:
            messages.extend(history[:-1])

    messages.append(HumanMessage(content=message))

    llm = _create_llm(streaming=False)
    response = await llm.ainvoke(messages)

    # Save assistant response
    if db and sid:
        _save_assistant_message(db, sid, response.content)

    # Extract RAG sources for response
    sources = []
    rag = get_rag_engine()
    if rag and rag.is_available:
        rag_response = rag.query(query_text=message, user_id=user_id, top_k=3)
        sources = [
            {
                "title": r.metadata.get("title", ""),
                "score": round(r.score, 3),
                "doc_id": r.metadata.get("doc_id", ""),
            }
            for r in rag_response.results
        ]

    return {
        "content": response.content,
        "sources": sources,
        "session_id": str(sid) if sid else str(uuid4()),
    }


async def get_coach_response_stream(
    message: str,
    mode: CoachMode,
    user_id: int,
    session_id: Optional[str] = None,
    goal_id: Optional[str] = None,
    db: Optional[Session] = None,
) -> AsyncIterator[dict[str, Any]]:
    """
    Get a streaming coach response with session continuity.

    If session_id is provided, loads conversation history for context.
    Creates a new session if session_id is None or invalid.
    Saves both user message and assistant response to the session.

    Yields:
        Dicts with 'type' and 'content'
    """
    # Get or create session
    sid = None
    if db:
        sid, is_new = _get_or_create_session(db, session_id, user_id, message)
        # Save user message
        _save_user_message(db, sid, message)

    system_prompt = _build_system_prompt(mode, user_id, message, goal_id, db)

    # Build messages with history
    messages = [SystemMessage(content=system_prompt)]

    # Load conversation history if we have a session
    if db and sid:
        history = _load_conversation_history(db, sid, user_id)
        # Exclude the last message (which is the one we just saved)
        if history and len(history) > 1:
            messages.extend(history[:-1])

    messages.append(HumanMessage(content=message))

    llm = _create_llm(streaming=True)

    # Collect full response for saving
    full_response = []

    async for chunk in llm.astream(messages):
        if chunk.content:
            full_response.append(chunk.content)
            yield {"type": "token", "content": chunk.content}

    # Save the complete assistant response
    if db and sid and full_response:
        _save_assistant_message(db, sid, "".join(full_response))

    # Yield session_id as metadata (consumed by the endpoint)
    yield {"type": "meta", "session_id": str(sid) if sid else str(uuid4())}
