"""AgentSpec — the standard blueprint (图纸) a child agent is assembled from.

Merges the blog's 0~7 eight-slot skeleton with Lilian Weng's
"LLM brain + Planning / Memory / Tool use" framework:

    0. one_liner   ← the user's plain-language request
    1. role        ← who it is, and especially what it does NOT do
    2. brain       ← model, planning strategy (ReAct), when to stop
    3. memory      ← short-term (context) / long-term (per-agent RAG collection)
    4. tools       ← bindings chosen from the tool registry
    5. policies    ← decision rules (the slot that most needs human review)
    6. prompts     ← System (job description) + User (work-order template)
    7. acceptance  ← checkable Given/When/Then scenarios

Design decisions (resolved with the project owner):
  - Long-term memory is isolated per agent: each child agent gets its own RAG
    collection (default ``agent_<id>``); memory never leaks between agents.
  - status flows draft → approved → published; ``published`` means the spec may be
    shared with and run by other users.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

SpecStatus = Literal["draft", "approved", "published"]


class RoleSpec(BaseModel):
    """Slot 1 — role and boundaries (是谁、尤其不做什么)."""

    name: str = ""
    description: str = ""
    boundaries: list[str] = Field(default_factory=list)


class BrainSpec(BaseModel):
    """Slot 2 — brain and planning (用哪个模型、ReAct、何时停)."""

    model: str = ""
    strategy: Literal["react"] = "react"
    max_iterations: int = 10


class MemorySpec(BaseModel):
    """Slot 3 — memory (短期上下文 / 长期向量库+RAG)."""

    short_term: bool = True
    long_term: bool = False
    # When long_term is True and this is unset, the factory assigns a dedicated
    # per-agent collection (agent_<id>) so agents' memories stay isolated.
    rag_collection: Optional[str] = None


class ToolBinding(BaseModel):
    """Slot 4 — one tool binding chosen from the registry."""

    name: str
    enabled: bool = True
    config: dict = Field(default_factory=dict)


class PromptSpec(BaseModel):
    """Slot 6 — prompts (System = 岗位说明书, User = 工单模板)."""

    system: str = ""
    user_template: str = ""


class AcceptanceCase(BaseModel):
    """Slot 7 — a single checkable Given/When/Then acceptance scenario."""

    given: str = ""
    when: str = ""
    then: str = ""


class WorkflowNode(BaseModel):
    """A single step in the agent's execution workflow."""

    id: str
    type: Literal["start", "think", "tool", "decision", "end"] = "think"
    label: str = ""
    tool_name: Optional[str] = None  # For tool nodes
    condition: Optional[str] = None  # For decision nodes


class WorkflowEdge(BaseModel):
    """Connection between workflow nodes."""

    from_node: str
    to_node: str
    condition: Optional[str] = None  # When to follow this edge
    label: str = ""


class WorkflowSpec(BaseModel):
    """Slot 8 — workflow definition (execution flow visualization)."""

    enabled: bool = False  # If False, uses default ReAct loop
    nodes: list[WorkflowNode] = Field(default_factory=list)
    edges: list[WorkflowEdge] = Field(default_factory=list)


class AgentSpec(BaseModel):
    """The complete blueprint compiled from one natural-language sentence."""

    model_config = ConfigDict(validate_assignment=False)

    id: str = Field(default_factory=lambda: str(uuid4()))
    version: int = 1
    status: SpecStatus = "draft"

    one_liner: str = ""  # slot 0

    role: RoleSpec = Field(default_factory=RoleSpec)  # slot 1
    brain: BrainSpec = Field(default_factory=BrainSpec)  # slot 2
    memory: MemorySpec = Field(default_factory=MemorySpec)  # slot 3
    tools: list[ToolBinding] = Field(default_factory=list)  # slot 4
    policies: list[str] = Field(default_factory=list)  # slot 5
    prompts: PromptSpec = Field(default_factory=PromptSpec)  # slot 6
    acceptance: list[AcceptanceCase] = Field(default_factory=list)  # slot 7
    workflow: WorkflowSpec = Field(default_factory=WorkflowSpec)  # slot 8 (optional)

    # Notes the compiler leaves about auto-filled content (esp. policies), so the
    # human reviewer knows what to scrutinize at the quality gate.
    compiler_notes: str = ""

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: Optional[int] = None

    def validate_complete(self) -> list[str]:
        """Return a list of missing-blueprint errors; empty means ready to approve.

        The approve gate blocks approval while this returns any errors. The
        decision-rules (policies) and acceptance slots are mandatory because they
        are exactly what the blog warns are most often left half-baked.
        """
        errors: list[str] = []
        if not self.role.name.strip():
            errors.append("role.name is empty")
        if not self.prompts.system.strip():
            errors.append("prompts.system is empty")
        if not self.policies:
            errors.append("policies (决策规矩) must not be empty")
        if not self.acceptance:
            errors.append("acceptance must have at least one case")
        return errors

    def default_rag_collection(self) -> str:
        """The dedicated long-term-memory collection name for this agent."""
        return f"agent_{self.id}"

    def resolved_rag_collection(self) -> Optional[str]:
        """The collection to use at runtime when long-term memory is enabled."""
        if not self.memory.long_term:
            return None
        return self.memory.rag_collection or self.default_rag_collection()
