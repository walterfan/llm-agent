"""Tests for the assembler's deterministic tool-binding logic.

We test build_tools() rather than a full LLM run: it's the part that enforces
'disabled tools are not bound' and 'high-risk tools are never auto-bound'.
"""

import pytest

from app.services.agent_factory.assembler import ToolResolutionError, build_tools
from app.services.agent_factory.spec import AgentSpec, ToolBinding


def test_enabled_stateless_tools_are_bound():
    spec = AgentSpec(
        tools=[
            ToolBinding(name="weather", enabled=True),
            ToolBinding(name="calculator", enabled=True),
            ToolBinding(name="datetime", enabled=True),
        ]
    )
    tools = build_tools(spec)
    names = {t.name for t in tools}
    assert names == {"get_weather", "calculate", "get_datetime"}


def test_disabled_tool_is_not_bound():
    spec = AgentSpec(
        tools=[
            ToolBinding(name="weather", enabled=True),
            ToolBinding(name="calculator", enabled=False),
        ]
    )
    names = {t.name for t in build_tools(spec)}
    assert "get_weather" in names
    assert "calculate" not in names


def test_high_risk_bash_never_bound_even_if_enabled():
    spec = AgentSpec(tools=[ToolBinding(name="bash", enabled=True)])
    assert build_tools(spec) == []


def test_stateful_tool_skipped_without_context():
    # reminder needs db+user_id; without them it's silently skipped, not an error
    spec = AgentSpec(tools=[ToolBinding(name="reminder", enabled=True)])
    assert build_tools(spec) == []


def test_unknown_tool_raises():
    spec = AgentSpec(tools=[ToolBinding(name="teleporter", enabled=True)])
    with pytest.raises(ToolResolutionError):
        build_tools(spec)
