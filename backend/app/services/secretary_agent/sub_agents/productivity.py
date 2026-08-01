"""
Productivity Sub-Agent (SRP: notes, tasks, reminders).

This sub-agent handles ALL personal organization requests:
- Notes: save, search, list
- Tasks: create, list, complete
- Reminders: create, list

ISP: Only gets productivity-related tools — no learning, weather, etc.

Reference: journal_20260206_ai-agent-workflow.md Section 1 (SRP)
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
from app.services.secretary_agent.tools.note_tool import (
    ListNotesInput,
    SaveNoteInput,
    SearchNotesInput,
    list_notes,
    save_note,
    search_notes,
)
from app.services.secretary_agent.tools.reminder_tool import (
    CreateReminderInput,
    ListRemindersInput,
    create_reminder,
    list_reminders,
)
from app.services.secretary_agent.tools.task_tool import (
    CompleteTaskInput,
    CreateTaskInput,
    ListTasksInput,
    complete_task,
    create_task,
    list_tasks,
)

logger = logging.getLogger("secretary_agent.productivity")


def create_productivity_tools(
    db: Optional[Session] = None,
    user_id: Optional[int] = None,
    session_id: Optional[UUID] = None,
) -> list[StructuredTool]:
    """
    Create productivity-domain tools.

    ISP: Only tools relevant to personal organization are included.

    Args:
        db: Database session for persistence
        user_id: Current user ID
        session_id: Current chat session ID

    Returns:
        List of StructuredTool instances for productivity
    """
    tools: list[StructuredTool] = []

    # ---- Note Tools ----
    tools.append(
        StructuredTool.from_function(
            func=partial(save_note, db=db, user_id=user_id, session_id=session_id),
            name="save_note",
            description=(
                "Save a note or memo for the user. "
                "Use when user wants to remember or record something."
            ),
            args_schema=SaveNoteInput,
        )
    )

    tools.append(
        StructuredTool.from_function(
            func=partial(search_notes, db=db, user_id=user_id),
            name="search_notes",
            description="Search through user's saved notes by content or title.",
            args_schema=SearchNotesInput,
        )
    )

    tools.append(
        StructuredTool.from_function(
            func=partial(list_notes, db=db, user_id=user_id),
            name="list_notes",
            description="List all user's notes.",
            args_schema=ListNotesInput,
        )
    )

    # ---- Task Tools ----
    tools.append(
        StructuredTool.from_function(
            func=partial(create_task, db=db, user_id=user_id, session_id=session_id),
            name="create_task",
            description=(
                "Create a to-do task for the user. "
                "Can set priority (low/medium/high/urgent) and due date."
            ),
            args_schema=CreateTaskInput,
        )
    )

    tools.append(
        StructuredTool.from_function(
            func=partial(list_tasks, db=db, user_id=user_id),
            name="list_tasks",
            description=(
                "List user's tasks/to-do items. "
                "Can filter by priority or include completed tasks."
            ),
            args_schema=ListTasksInput,
        )
    )

    tools.append(
        StructuredTool.from_function(
            func=partial(complete_task, db=db, user_id=user_id),
            name="complete_task",
            description="Mark a task as completed.",
            args_schema=CompleteTaskInput,
        )
    )

    # ---- Reminder Tools ----
    tools.append(
        StructuredTool.from_function(
            func=partial(
                create_reminder, db=db, user_id=user_id, session_id=session_id
            ),
            name="create_reminder",
            description=(
                "Create a reminder for a specific time. "
                "Time format: 'YYYY-MM-DD HH:MM' or relative like '30分钟后'. "
                "Can set repeat: none/daily/weekly/monthly/yearly."
            ),
            args_schema=CreateReminderInput,
        )
    )

    tools.append(
        StructuredTool.from_function(
            func=partial(list_reminders, db=db, user_id=user_id),
            name="list_reminders",
            description="List user's reminders.",
            args_schema=ListRemindersInput,
        )
    )

    return tools


def create_productivity_agent(
    llm: BaseChatModel,
    db: Optional[Session] = None,
    user_id: Optional[int] = None,
    session_id: Optional[UUID] = None,
):
    """
    Create the Productivity sub-agent with its tools.

    Args:
        llm: The language model instance
        db: Database session
        user_id: Current user ID
        session_id: Current chat session ID

    Returns:
        A compiled LangGraph agent (CompiledStateGraph)
    """
    tools = create_productivity_tools(db=db, user_id=user_id, session_id=session_id)

    prompt = get_prompt(
        "sub_agents.yaml",
        "productivity_agent",
        current_date=datetime.now().strftime("%Y-%m-%d"),
    )

    agent = create_react_agent(
        model=llm,
        tools=tools,
        prompt=prompt,
        name="productivity_agent",
    )

    logger.info(
        f"Created ProductivityAgent with {len(tools)} tools: "
        f"{[t.name for t in tools]}"
    )

    return agent
