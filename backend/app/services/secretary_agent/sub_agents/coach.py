"""
Coach Sub-Agent (SRP: RAG knowledge, learning goals, study sessions, coaching).

This sub-agent handles ALL coaching-related requests:
- Query knowledge base (RAG)
- Create and track learning goals
- Log study sessions
- Provide progress reports
- Coaching, tutoring, and quiz modes

ISP: Only gets coaching-related tools — no notes, tasks, weather, etc.
"""

import logging
from datetime import datetime
from functools import partial
from typing import Optional
from uuid import UUID

from langchain_core.language_models import BaseChatModel
from langchain_core.tools import StructuredTool
from langgraph.prebuilt import create_react_agent
from sqlalchemy.orm import Session

from app.services.secretary_agent.prompts import get_prompt
from app.services.secretary_agent.tools.coach_tools import (
    CreateGoalInput,
    GetProgressInput,
    LogStudySessionInput,
    QueryKnowledgeInput,
    create_goal,
    get_progress,
    log_study_session,
    query_knowledge,
)

logger = logging.getLogger("secretary_agent.coach")


def create_coach_tools(
    db: Optional[Session] = None,
    user_id: Optional[int] = None,
    session_id: Optional[UUID] = None,
) -> list[StructuredTool]:
    """
    Create coaching-domain tools.

    ISP: Only tools relevant to coaching are included.

    Args:
        db: Database session for persistence tools
        user_id: Current user ID for scoped queries
        session_id: Current chat session ID

    Returns:
        List of StructuredTool instances for coaching
    """
    tools: list[StructuredTool] = []

    # Query knowledge base
    tools.append(
        StructuredTool.from_function(
            func=partial(query_knowledge, user_id=user_id),
            name="query_knowledge",
            description=(
                "Search the user's knowledge base using semantic search. "
                "Use this when the user asks a question that might be answered "
                "by their uploaded study materials."
            ),
            args_schema=QueryKnowledgeInput,
        )
    )

    # Create learning goal
    tools.append(
        StructuredTool.from_function(
            func=partial(create_goal, db=db, user_id=user_id),
            name="create_goal",
            description=(
                "Create a new learning goal for the user. "
                "Use when the user wants to set a study target or learning plan."
            ),
            args_schema=CreateGoalInput,
        )
    )

    # Log study session
    tools.append(
        StructuredTool.from_function(
            func=partial(log_study_session, db=db, user_id=user_id),
            name="log_study_session",
            description=(
                "Log a study session for the user. "
                "Use when the user reports they have studied or wants to record study time."
            ),
            args_schema=LogStudySessionInput,
        )
    )

    # Get progress report
    tools.append(
        StructuredTool.from_function(
            func=partial(get_progress, db=db, user_id=user_id),
            name="get_progress",
            description=(
                "Get a progress report for a specific learning goal. "
                "Shows total sessions, study time, streaks, and completion status."
            ),
            args_schema=GetProgressInput,
        )
    )

    return tools


def create_coach_agent(
    llm: BaseChatModel,
    db: Optional[Session] = None,
    user_id: Optional[int] = None,
    session_id: Optional[UUID] = None,
):
    """
    Create the Coach sub-agent with its tools.

    Args:
        llm: The language model instance
        db: Database session
        user_id: Current user ID
        session_id: Current chat session ID

    Returns:
        A compiled LangGraph agent (CompiledStateGraph)
    """
    tools = create_coach_tools(db=db, user_id=user_id, session_id=session_id)

    prompt = get_prompt(
        "coach.yaml",
        "coach_agent",
        current_date=datetime.now().strftime("%Y-%m-%d"),
    )

    agent = create_react_agent(
        model=llm,
        tools=tools,
        prompt=prompt,
        name="coach_agent",
    )

    logger.info(
        f"Created CoachAgent with {len(tools)} tools: " f"{[t.name for t in tools]}"
    )

    return agent
