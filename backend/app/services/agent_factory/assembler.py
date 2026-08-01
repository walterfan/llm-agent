"""Assembler + generic ReAct runtime.

Reads an approved/published AgentSpec, binds its enabled tools to the real tool
implementations (reusing the secretary_agent tools), and runs a ReAct loop using
langgraph's create_react_agent — the same execution engine the secretary uses, here
parameterized by the spec (system prompt, tools, max_iterations) instead of hardcoded.

The secretary's own agent code is NOT modified; this is an additive generic entry.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

import httpx
from langchain_core.tools import StructuredTool
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

from app.core.config import settings
from app.services.agent_factory.spec import AgentSpec

logger = logging.getLogger("agent_factory.assembler")


class ToolResolutionError(Exception):
    """Raised when a spec references a tool that cannot be bound."""


def _build_llm(model: str) -> ChatOpenAI:
    http_client = httpx.AsyncClient(
        verify=getattr(settings, "LLM_VERIFY_SSL", True),
        timeout=httpx.Timeout(getattr(settings, "LLM_TIMEOUT", 60.0)),
    )
    return ChatOpenAI(
        model=model or settings.LLM_MODEL,
        openai_api_key=settings.LLM_API_KEY,
        openai_api_base=settings.LLM_BASE_URL,
        temperature=0.3,
        http_async_client=http_client,
    )


def build_tools(
    spec: AgentSpec, db=None, user_id: Optional[int] = None, session_id=None
) -> list[StructuredTool]:
    """Bind the spec's *enabled* tool names to real StructuredTool callables.

    Disabled bindings (including high-risk tools not explicitly enabled) are skipped.
    Unknown names raise ToolResolutionError. bash is intentionally NOT bindable here
    even if enabled — it requires a dedicated, separately-reviewed executor.
    """
    from app.services.secretary_agent.tools.calculator_tool import (
        CalculatorInput,
        calculate,
    )
    from app.services.secretary_agent.tools.datetime_tool import (
        DateTimeInput,
        get_current_datetime,
    )
    from app.services.secretary_agent.tools.weather_tool import (
        WeatherInput,
        get_weather,
    )

    tools: list[StructuredTool] = []
    for binding in spec.tools:
        if not binding.enabled:
            continue
        name = binding.name
        if name == "weather":
            tools.append(
                StructuredTool.from_function(
                    coroutine=get_weather,
                    name="get_weather",
                    description="Get current weather for a city.",
                    args_schema=WeatherInput,
                )
            )
        elif name == "calculator":
            tools.append(
                StructuredTool.from_function(
                    func=calculate,
                    name="calculate",
                    description="Evaluate a mathematical expression.",
                    args_schema=CalculatorInput,
                )
            )
        elif name == "datetime":
            tools.append(
                StructuredTool.from_function(
                    func=get_current_datetime,
                    name="get_datetime",
                    description="Get the current date and time.",
                    args_schema=DateTimeInput,
                )
            )
        elif name in ("note", "task", "reminder", "rag_search"):
            # Stateful tools need db + user_id; bound only when context is provided.
            tool = _build_stateful_tool(
                name, db=db, user_id=user_id, session_id=session_id
            )
            if tool is not None:
                tools.append(tool)
        elif name == "bash":
            # High-risk: never auto-bound by the generic runtime.
            logger.warning("Refusing to bind high-risk tool 'bash' in generic runtime")
            continue
        else:
            raise ToolResolutionError(f"unknown tool in spec: {name}")
    return tools


def _build_stateful_tool(name: str, db=None, user_id=None, session_id=None):
    """Bind a db/user-scoped tool. Returns None if required context is missing."""
    if db is None or user_id is None:
        logger.info("Skipping stateful tool %s (no db/user_id context)", name)
        return None
    if name == "reminder":
        from app.services.secretary_agent.tools.reminder_tool import (
            CreateReminderInput,
            create_reminder,
        )

        def _create_reminder(**kwargs: Any):
            return create_reminder(
                db=db, user_id=user_id, session_id=session_id, **kwargs
            )

        return StructuredTool.from_function(
            func=_create_reminder,
            name="create_reminder",
            description="Create a reminder for the user.",
            args_schema=CreateReminderInput,
        )
    if name == "task":
        from app.services.secretary_agent.tools.task_tool import (
            CreateTaskInput,
            create_task,
        )

        def _create_task(**kwargs: Any):
            return create_task(db=db, user_id=user_id, **kwargs)

        return StructuredTool.from_function(
            func=_create_task,
            name="create_task",
            description="Create a task for the user.",
            args_schema=CreateTaskInput,
        )
    if name == "note":
        from app.services.secretary_agent.tools.note_tool import (
            SaveNoteInput,
            save_note,
        )

        def _save_note(**kwargs: Any):
            return save_note(db=db, user_id=user_id, **kwargs)

        return StructuredTool.from_function(
            func=_save_note,
            name="save_note",
            description="Save a note for the user.",
            args_schema=SaveNoteInput,
        )
    # rag_search binding is deferred (depends on rag engine availability)
    return None


def assemble(spec: AgentSpec, db=None, user_id: Optional[int] = None, session_id=None):
    """Assemble an approved spec into a runnable ReAct agent (CompiledStateGraph)."""
    llm = _build_llm(spec.brain.model)
    tools = build_tools(spec, db=db, user_id=user_id, session_id=session_id)
    agent = create_react_agent(
        model=llm,
        tools=tools,
        prompt=spec.prompts.system,
        name=spec.role.name or "child_agent",
    )
    logger.info(
        "Assembled child agent %s with %d tools: %s",
        spec.role.name,
        len(tools),
        [t.name for t in tools],
    )
    return agent, tools
