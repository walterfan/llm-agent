"""Compiler (翻译机) — one sentence → five blueprints.

Turns a plain-language one-liner into an AgentSpec draft via five steps:

    ① extract intent & role      (mostly automatic)
    ② recognize tools from verbs  (mostly automatic; uncertain → enabled=False)
    ③ draft decision policies     (⚠ auto-filled, MUST be human-reviewed)
    ④ freeze into prompts         (System + User template)
    ⑤ attach acceptance cases

The LLM does the linguistic extraction (via instructor structured output); the
deterministic parts — binding verbs to the registry, disabling uncertain/high-risk
tools, writing compiler_notes, forcing status=draft — happen here in Python so they
are testable without an LLM and cannot be "hallucinated" away.
"""

from __future__ import annotations

import logging
from typing import Optional

from pydantic import BaseModel, Field

from app.core.config import settings
from app.services.agent_factory import registry
from app.services.agent_factory.spec import (
    AcceptanceCase,
    AgentSpec,
    BrainSpec,
    MemorySpec,
    PromptSpec,
    RoleSpec,
    ToolBinding,
)
from app.services.llm.provider_factory import LLMProviderFactory

logger = logging.getLogger("agent_factory.compiler")


# --- structured output the LLM must return (steps ①②③⑤ linguistic parts) --------


class _CompiledDraft(BaseModel):
    """What the LLM extracts from the one-liner."""

    role_name: str = Field(description="子 Agent 的名字，例：日程安排专家")
    role_description: str = Field(description="一句话说明它负责什么")
    boundaries: list[str] = Field(
        default_factory=list, description="它明确不做的事，例：不写代码、不闲聊"
    )
    tool_verbs: list[str] = Field(
        default_factory=list,
        description="从需求动词里抽出的能力关键词，例：查天气、设提醒、排任务",
    )
    policies: list[str] = Field(
        default_factory=list,
        description="决策规矩：把需求里的常识和潜台词写成明确规则",
    )
    acceptance: list[str] = Field(
        default_factory=list,
        description="2-4 条可检验场景，每条写成 '当X时，应当Y' 的一句话",
    )


_COMPILE_PROMPT = """你是一台"AI Agent 孵化器"的编译器。用户会给你一句关于他想要的 AI 助手的大白话，\
你要把它编译成一份子 Agent 的图纸。请从这句话里抽取：
1) 角色名与描述、以及它明确"不做什么"（边界）；
2) 需要用到的能力关键词（从动词来，例：查天气→"查天气"，设提醒→"设提醒"）；
3) 决策规矩（把话里没明说但显然需要的常识写成规则，例：下雨改户外、深夜别打扰）；
4) 2-4 条可检验的验收场景。

用户的一句话需求：
{one_liner}
"""


def _bind_tools(verbs: list[str]) -> tuple[list[ToolBinding], list[str]]:
    """Map extracted verbs to registry capabilities (deterministic).

    Returns (bindings, notes). Uncertain matches and high-risk tools are included
    with enabled=False and noted for human confirmation.
    """
    bindings: dict[str, ToolBinding] = {}
    notes: list[str] = []
    for verb in verbs:
        caps = registry.find_by_verb(verb)
        if not caps:
            notes.append(f"动词『{verb}』未匹配到已注册工具，需人工确认")
            continue
        for cap in caps:
            if cap.name in bindings:
                continue
            enabled = registry.default_enabled(cap.name)
            bindings[cap.name] = ToolBinding(name=cap.name, enabled=enabled)
            if not enabled:
                notes.append(
                    f"工具『{cap.name}』为高危(risk=high)，已默认关闭，需显式开启并人工审批"
                )
    return list(bindings.values()), notes


def _build_system_prompt(
    role: RoleSpec, tools: list[ToolBinding], policies: list[str]
) -> str:
    tool_names = "、".join(t.name for t in tools if t.enabled) or "（无）"
    boundaries = "；".join(role.boundaries) or "（无特别限制）"
    policy_text = "\n".join(f"- {p}" for p in policies) or "- （待补充）"
    return (
        f"你是一名「{role.name}」。{role.description}\n"
        f"你的边界：{boundaries}。\n"
        f"你可以使用这些工具：{tool_names}。\n"
        f"请遵守以下决策规矩：\n{policy_text}\n"
        f"办不到的事如实说明，不要编造。"
    )


class AgentCompiler:
    """Compiles a one-liner into an AgentSpec draft."""

    def __init__(self, llm_provider=None):
        self._llm = llm_provider

    def _get_llm(self):
        if self._llm is not None:
            return self._llm
        return LLMProviderFactory.get_provider(
            provider_type=settings.LLM_PROVIDER,
            base_url=settings.LLM_BASE_URL,
            api_key=settings.LLM_API_KEY,
            model=settings.LLM_MODEL,
            verify_ssl=settings.LLM_VERIFY_SSL,
            timeout=int(settings.LLM_TIMEOUT),
        )

    async def compile(
        self, one_liner: str, created_by: Optional[int] = None
    ) -> AgentSpec:
        """Run the five-step compile and return a draft AgentSpec."""
        llm = self._get_llm()
        draft: _CompiledDraft = await llm.generate_completion(
            prompt=_COMPILE_PROMPT.format(one_liner=one_liner),
            response_model=_CompiledDraft,
            max_retries=3,
            temperature=0.3,
        )
        return self.assemble_spec(one_liner, draft, created_by)

    def assemble_spec(
        self, one_liner: str, draft: _CompiledDraft, created_by: Optional[int] = None
    ) -> AgentSpec:
        """Deterministic step: turn the LLM draft into a validated AgentSpec draft.

        Separated from the LLM call so it is unit-testable without a network.
        """
        role = RoleSpec(
            name=draft.role_name.strip(),
            description=draft.role_description.strip(),
            boundaries=[b.strip() for b in draft.boundaries if b.strip()],
        )
        tools, tool_notes = _bind_tools(draft.tool_verbs)
        policies = [p.strip() for p in draft.policies if p.strip()]
        acceptance = [
            AcceptanceCase(given="", when=a.strip(), then="")
            for a in draft.acceptance
            if a.strip()
        ]

        notes = ["决策规矩(policies)由编译器自动补全，请人工逐条审查后再批准。"]
        notes.extend(tool_notes)

        spec = AgentSpec(
            one_liner=one_liner,
            role=role,
            brain=BrainSpec(model=settings.LLM_MODEL),
            memory=MemorySpec(),
            tools=tools,
            policies=policies,
            prompts=PromptSpec(
                system=_build_system_prompt(role, tools, policies),
                user_template="{input}",
            ),
            acceptance=acceptance,
            compiler_notes="\n".join(notes),
            created_by=created_by,
            status="draft",
        )
        return spec
