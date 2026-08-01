"""
Utility Sub-Agent (SRP: weather, calculator, datetime).

This sub-agent handles ALL quick-info utility requests:
- Weather queries (city weather + clothing suggestions)
- Math calculations
- Date and time queries

ISP: Only gets utility-related tools — no learning, notes, tasks, etc.

Reference: journal_20260206_ai-agent-workflow.md Section 1 (SRP)
"""

import logging
from datetime import datetime

from langchain_core.language_models import BaseChatModel
from langchain_core.tools import StructuredTool
from langgraph.prebuilt import create_react_agent

from app.services.secretary_agent.prompts import get_prompt
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

logger = logging.getLogger("secretary_agent.utility")


def create_utility_tools() -> list[StructuredTool]:
    """
    Create utility-domain tools.

    ISP: Only tools for quick information retrieval are included.
    These tools are stateless — they don't need db, user_id, or session_id.

    Returns:
        List of StructuredTool instances for utilities
    """
    tools: list[StructuredTool] = []

    # Calculator
    tools.append(
        StructuredTool.from_function(
            func=calculate,
            name="calculate",
            description=(
                "Evaluate mathematical expressions. Supports basic arithmetic, "
                "functions (sqrt, sin, cos, log, etc.), and constants (pi, e)."
            ),
            args_schema=CalculatorInput,
        )
    )

    # DateTime
    tools.append(
        StructuredTool.from_function(
            func=get_current_datetime,
            name="get_datetime",
            description="Get the current date and time. Can specify timezone.",
            args_schema=DateTimeInput,
        )
    )

    # Weather (async)
    tools.append(
        StructuredTool.from_function(
            coroutine=get_weather,
            name="get_weather",
            description=(
                "Get current weather for a city. "
                "Provide city name (e.g., 'Beijing', '北京') or AD code. "
                "Returns temperature, weather condition, wind, humidity, "
                "and suggestions."
            ),
            args_schema=WeatherInput,
        )
    )

    return tools


def create_utility_agent(llm: BaseChatModel):
    """
    Create the Utility sub-agent with its tools.

    Utility tools are stateless — no db or user context needed.

    Args:
        llm: The language model instance

    Returns:
        A compiled LangGraph agent (CompiledStateGraph)
    """
    tools = create_utility_tools()

    prompt = get_prompt(
        "sub_agents.yaml",
        "utility_agent",
        current_date=datetime.now().strftime("%Y-%m-%d"),
    )

    agent = create_react_agent(
        model=llm,
        tools=tools,
        prompt=prompt,
        name="utility_agent",
    )

    logger.info(
        f"Created UtilityAgent with {len(tools)} tools: " f"{[t.name for t in tools]}"
    )

    return agent
