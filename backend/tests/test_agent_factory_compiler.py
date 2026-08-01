"""Unit tests for the AgentCompiler's deterministic assembly step.

The LLM call (compile()) is not exercised here — only assemble_spec(), which is the
pure, testable part: verb→registry binding, high-risk disabling, compiler_notes,
and forced draft status.
"""

from app.services.agent_factory.compiler import AgentCompiler, _CompiledDraft


def _draft() -> _CompiledDraft:
    return _CompiledDraft(
        role_name="日程安排专家",
        role_description="只排日程和设提醒",
        boundaries=["不写代码", "不闲聊"],
        tool_verbs=["查天气", "设提醒", "排任务"],
        policies=["下雨改户外", "深夜不打扰家人"],
        acceptance=["当下雨且有户外拍摄时，应当提示改期", "当两件事撞车时，按紧急取舍"],
    )


def test_assemble_produces_draft_with_five_blueprints():
    spec = AgentCompiler().assemble_spec("做一个日程安排专家", _draft(), created_by=7)
    assert spec.status == "draft"
    assert spec.created_by == 7
    # role + boundaries
    assert spec.role.name == "日程安排专家"
    assert "不写代码" in spec.role.boundaries
    # tools mapped from verbs
    tool_names = {t.name for t in spec.tools}
    assert "weather" in tool_names
    assert "reminder" in tool_names
    assert "task" in tool_names
    # policies + acceptance + prompts
    assert spec.policies == ["下雨改户外", "深夜不打扰家人"]
    assert len(spec.acceptance) == 2
    assert spec.prompts.system
    assert spec.prompts.user_template == "{input}"


def test_policies_auto_fill_is_flagged_in_notes():
    spec = AgentCompiler().assemble_spec("x", _draft())
    assert "policies" in spec.compiler_notes
    assert "人工" in spec.compiler_notes  # tells the reviewer to check


def test_unknown_verb_is_noted_not_bound():
    draft = _draft()
    draft.tool_verbs = ["召唤神龙"]  # matches nothing
    spec = AgentCompiler().assemble_spec("x", draft)
    assert spec.tools == []
    assert "召唤神龙" in spec.compiler_notes


def test_high_risk_tool_bound_disabled():
    draft = _draft()
    draft.tool_verbs = ["执行 shell 命令"]  # matches bash (risk=high)
    spec = AgentCompiler().assemble_spec("x", draft)
    bash = next((t for t in spec.tools if t.name == "bash"), None)
    assert bash is not None
    assert bash.enabled is False
    assert "bash" in spec.compiler_notes


def test_assembled_draft_is_not_yet_complete_without_review():
    # A compiled draft has policies+acceptance from the LLM, so it *can* be complete;
    # but with empty policies it must fail validate_complete.
    draft = _draft()
    draft.policies = []
    spec = AgentCompiler().assemble_spec("x", draft)
    assert any("policies" in e for e in spec.validate_complete())
