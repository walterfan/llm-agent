"""Pydantic request/response schemas for the AI Agent Factory API."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from app.services.agent_factory.spec import AgentSpec


class CompileRequest(BaseModel):
    """POST /factory/compile — one plain-language sentence."""

    one_liner: str = Field(..., min_length=1, description="一句话需求")


class SpecSummary(BaseModel):
    """Row in the spec list."""

    id: str
    name: str
    version: int
    status: str
    one_liner: str


class SpecResponse(BaseModel):
    """A full spec (the five blueprints) plus its DB status/version."""

    id: str
    name: str
    version: int
    status: str
    spec: AgentSpec


class UpdateSpecRequest(BaseModel):
    """PATCH /factory/specs/{id} — human edits to a draft (esp. policies/tools)."""

    spec: AgentSpec


class RunRequest(BaseModel):
    """POST /factory/agents/{id}/run — a task for the assembled child agent."""

    input: str = Field(..., min_length=1, description="给子 Agent 的一句话任务")


class RunStep(BaseModel):
    """One ReAct step in the returned trace."""

    thought: Optional[str] = None
    action: Optional[str] = None
    observation: Optional[str] = None


class RunResponse(BaseModel):
    """Result of running an assembled child agent."""

    spec_id: str
    final: str
    trace: list[RunStep] = Field(default_factory=list)
