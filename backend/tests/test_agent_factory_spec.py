"""Unit tests for the AgentSpec blueprint model."""

from app.services.agent_factory.spec import (
    AcceptanceCase,
    AgentSpec,
    BrainSpec,
    MemorySpec,
    PromptSpec,
    RoleSpec,
    ToolBinding,
)


def _complete_spec() -> AgentSpec:
    return AgentSpec(
        one_liner="帮我做一个日程安排专家",
        role=RoleSpec(
            name="日程安排专家",
            description="只排日程和设提醒",
            boundaries=["不写代码", "不闲聊"],
        ),
        brain=BrainSpec(model="gpt-4", max_iterations=8),
        memory=MemorySpec(long_term=True),
        tools=[ToolBinding(name="weather"), ToolBinding(name="reminder")],
        policies=["下雨改户外", "撞车按紧急取舍"],
        prompts=PromptSpec(system="你是日程安排专家", user_template="今天要干嘛：{input}"),
        acceptance=[AcceptanceCase(given="下雨", when="有户外拍摄", then="提示改期")],
    )


def test_defaults():
    spec = AgentSpec()
    assert spec.status == "draft"
    assert spec.version == 1
    assert spec.brain.strategy == "react"
    assert spec.brain.max_iterations == 10
    assert spec.memory.short_term is True
    assert spec.memory.long_term is False
    assert spec.id  # uuid assigned


def test_round_trip_serialize_deserialize():
    spec = _complete_spec()
    dumped = spec.model_dump()
    restored = AgentSpec.model_validate(dumped)
    assert restored.role.name == "日程安排专家"
    assert restored.policies == ["下雨改户外", "撞车按紧急取舍"]
    assert len(restored.tools) == 2
    assert restored.acceptance[0].then == "提示改期"
    assert restored == spec


def test_validate_complete_passes_for_complete_spec():
    assert _complete_spec().validate_complete() == []


def test_validate_complete_flags_empty_policies():
    spec = _complete_spec()
    spec.policies = []
    errors = spec.validate_complete()
    assert any("policies" in e for e in errors)


def test_validate_complete_flags_zero_acceptance():
    spec = _complete_spec()
    spec.acceptance = []
    errors = spec.validate_complete()
    assert any("acceptance" in e for e in errors)


def test_validate_complete_flags_empty_role_name():
    spec = _complete_spec()
    spec.role.name = "  "
    errors = spec.validate_complete()
    assert any("role.name" in e for e in errors)


def test_validate_complete_flags_empty_system_prompt():
    spec = _complete_spec()
    spec.prompts.system = ""
    errors = spec.validate_complete()
    assert any("prompts.system" in e for e in errors)


def test_default_rag_collection_format():
    spec = AgentSpec(id="abc123")
    assert spec.default_rag_collection() == "agent_abc123"


def test_resolved_rag_collection_when_long_term_off():
    spec = AgentSpec(id="x", memory=MemorySpec(long_term=False))
    assert spec.resolved_rag_collection() is None


def test_resolved_rag_collection_defaults_to_per_agent():
    spec = AgentSpec(id="x", memory=MemorySpec(long_term=True))
    assert spec.resolved_rag_collection() == "agent_x"


def test_resolved_rag_collection_respects_explicit_name():
    spec = AgentSpec(
        id="x", memory=MemorySpec(long_term=True, rag_collection="custom_coll")
    )
    assert spec.resolved_rag_collection() == "custom_coll"
