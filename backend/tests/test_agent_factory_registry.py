"""Unit tests for the tool registry (read-only capability catalog)."""

from app.services.agent_factory.registry import (
    ToolCapability,
    default_enabled,
    find_by_verb,
    get_capability,
    list_capabilities,
)

LOW_RISK_TOOLS = {"weather", "rag_search", "note", "task", "reminder", "calculator", "datetime"}


def test_list_capabilities_contains_all_tools():
    names = {c.name for c in list_capabilities()}
    assert LOW_RISK_TOOLS.issubset(names)
    assert "bash" in names
    assert len(list_capabilities()) == len(LOW_RISK_TOOLS) + 1


def test_get_capability_by_name():
    cap = get_capability("weather")
    assert isinstance(cap, ToolCapability)
    assert cap.name == "weather"
    assert cap.risk == "low"
    assert get_capability("does_not_exist") is None


def test_find_by_verb_chinese():
    assert any(c.name == "weather" for c in find_by_verb("天气"))
    assert any(c.name == "task" for c in find_by_verb("安排"))


def test_find_by_verb_english():
    assert any(c.name == "reminder" for c in find_by_verb("remind"))
    assert any(c.name == "calculator" for c in find_by_verb("calculate"))


def test_find_by_verb_empty_returns_nothing():
    assert find_by_verb("") == []
    assert find_by_verb("   ") == []


def test_bash_is_high_risk_and_disabled_by_default():
    bash = get_capability("bash")
    assert bash is not None
    assert bash.risk == "high"
    assert default_enabled("bash") is False


def test_low_risk_tool_enabled_by_default():
    assert default_enabled("weather") is True
    assert default_enabled("reminder") is True


def test_default_enabled_unknown_tool_is_false():
    assert default_enabled("nope") is False
