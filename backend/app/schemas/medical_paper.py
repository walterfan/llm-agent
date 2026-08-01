"""
Schemas for the Medical Paper Writing Assistant.

Includes A2A message schemas, domain-specific output schemas,
and API request/response models.
"""

from datetime import datetime
from typing import Any, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ============================================================================
# A2A Domain Schemas — Agent output contracts
# ============================================================================


class Reference(BaseModel):
    """A single literature reference from PubMed."""

    pmid: str
    title: str
    authors: list[str]
    journal: str
    year: int
    abstract: str
    relevance_score: float = 0.0


class LiteratureOutput(BaseModel):
    """Output from the Literature Agent."""

    references: list[Reference] = []
    search_strategy: str = ""
    total_found: int = 0
    filtered_count: int = 0


class AnalysisResult(BaseModel):
    """A single statistical analysis result."""

    test_name: str
    statistic: float
    p_value: float
    confidence_interval: tuple[float, float] = (0.0, 0.0)
    effect_size: float = 0.0
    interpretation: str = ""


class StatsOutput(BaseModel):
    """Output from the Stats Agent."""

    primary_analysis: Optional[AnalysisResult] = None
    secondary_analyses: list[AnalysisResult] = []
    sensitivity_analyses: list[AnalysisResult] = []
    summary_statistics: dict[str, Any] = {}


class ComplianceItem(BaseModel):
    """A single compliance checklist item."""

    item_id: str
    description: str
    status: Literal["PASS", "WARN", "FAIL"]
    finding: str = ""
    suggestion: Optional[str] = None


class ComplianceOutput(BaseModel):
    """Output from the Compliance Agent."""

    checklist_type: str  # CONSORT, STROBE, PRISMA
    total_items: int = 0
    passed: int = 0
    warnings: int = 0
    failed: int = 0
    items: list[ComplianceItem] = []
    overall_score: float = 0.0


class ManuscriptSection(BaseModel):
    """A single section of the manuscript."""

    section_type: str  # introduction, methods, results, discussion, abstract
    title: str
    content: str
    word_count: int = 0
    citations: list[str] = []


class ManuscriptOutput(BaseModel):
    """Output from the Writer Agent."""

    sections: list[ManuscriptSection] = []
    total_word_count: int = 0


# ============================================================================
# A2A Error Schema (medical paper specific extensions)
# ============================================================================


class A2AErrorMedical(BaseModel):
    """Error info for medical paper A2A messages."""

    code: str  # VALIDATION_ERROR, TOOL_ERROR, TIMEOUT, RATE_LIMIT, LLM_ERROR
    message: str
    recoverable: bool = False
    retry_after: Optional[int] = None  # seconds


class A2AMetricsMedical(BaseModel):
    """Metrics for medical paper A2A messages."""

    latency_ms: int = 0
    tokens_in: int = 0
    tokens_out: int = 0
    tool_calls: int = 0


class A2AMessageMedical(BaseModel):
    """
    A2A message schema for medical paper agent communication.

    Extends the secretary agent A2A contract with medical-paper-specific
    output types while maintaining the same core structure.
    """

    protocol: str = "a2a.medical.v1"
    id: str = ""
    correlation_id: Optional[str] = None
    timestamp: Optional[str] = None

    sender: str
    receiver: str
    intent: str

    input: Optional[dict[str, Any]] = None
    status: str = "pending"  # pending, ok, error
    output: Optional[dict[str, Any]] = None

    error: Optional[A2AErrorMedical] = None
    metrics: Optional[A2AMetricsMedical] = None


# ============================================================================
# API Request/Response Schemas
# ============================================================================


class CreateTaskRequest(BaseModel):
    """Request to create a new medical paper writing task."""

    title: str = Field(
        ...,
        min_length=1,
        max_length=500,
        json_schema_extra={"examples": ["Effect of Drug X on Blood Pressure"]},
    )
    paper_type: str = Field(
        default="rct",
        description="Paper type: rct, meta_analysis, cohort",
        json_schema_extra={"examples": ["rct"]},
    )
    research_question: str = Field(
        ...,
        min_length=10,
        json_schema_extra={
            "examples": [
                "Does Drug X reduce systolic blood pressure compared to placebo in adults with stage 1 hypertension?"
            ]
        },
    )
    study_design: Optional[dict[str, Any]] = Field(
        default=None,
        description="Study design parameters (arms, blinding, duration, etc.)",
        json_schema_extra={
            "examples": [{"type": "double-blind", "arms": 2, "duration_weeks": 12}]
        },
    )
    raw_data: Optional[dict[str, Any]] = Field(
        default=None,
        description="Raw data for statistical analysis (optional)",
    )


class RevisionRequest(BaseModel):
    """Request to submit revision feedback for a completed task."""

    feedback: str = Field(
        ...,
        min_length=1,
        json_schema_extra={
            "examples": ["Add confidence intervals to the results section"]
        },
    )
    sections_to_revise: Optional[list[str]] = Field(
        default=None,
        description="Specific sections to revise, or None for all",
        json_schema_extra={"examples": [["results", "discussion"]]},
    )


class TaskResponse(BaseModel):
    """Response for a medical paper task with all artifacts."""

    id: str = Field(description="Unique task identifier (UUID)")
    user_id: int
    title: str
    paper_type: str = Field(description="Paper type: rct, cohort, meta_analysis")
    status: str = Field(
        description="Task status: pending, running, revision, completed, failed"
    )
    research_question: str
    study_design: Optional[dict[str, Any]] = None
    current_step: Optional[str] = Field(
        default=None,
        description="Current pipeline step: literature, stats, writer, compliance, done",
    )
    revision_round: int = 0
    manuscript: Optional[dict[str, Any]] = Field(
        default=None, description="Manuscript sections (IMRAD)"
    )
    references: Optional[list[dict[str, Any]]] = Field(
        default=None, description="Literature references from PubMed"
    )
    stats_report: Optional[dict[str, Any]] = Field(
        default=None, description="Statistical analysis report"
    )
    compliance_report: Optional[dict[str, Any]] = Field(
        default=None, description="CONSORT/STROBE/PRISMA compliance report"
    )
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    completed_at: Optional[str] = None


class TaskListResponse(BaseModel):
    """Response for listing medical paper tasks."""

    tasks: list[TaskResponse]
    total: int


class TemplateInfo(BaseModel):
    """Information about a paper template."""

    paper_type: str
    name: str
    description: str
    checklist: str  # CONSORT, STROBE, PRISMA


class TemplateListResponse(BaseModel):
    """Response for listing paper templates."""

    templates: list[TemplateInfo]
