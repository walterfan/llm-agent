"""
Prometheus metrics for the Medical Paper Writing Assistant.

Implements Metrics-Driven Development (MDD) with:
- RED metrics (Rate, Errors, Duration)
- Pipeline step metrics
- Agent-level metrics
- Business metrics (compliance, revisions)
"""

import time
from contextlib import contextmanager
from functools import wraps
from typing import Callable

from prometheus_client import Counter, Gauge, Histogram, Info

# ============================================================================
# RED Metrics — Task-level
# ============================================================================

TASK_TOTAL = Counter(
    "medical_paper_task_total",
    "Total number of medical paper tasks",
    ["paper_type", "status"],  # status: created/completed/failed
)

TASK_DURATION = Histogram(
    "medical_paper_task_duration_seconds",
    "End-to-end duration of paper tasks",
    ["paper_type"],
    buckets=[10, 30, 60, 120, 300, 600, 1200, 1800, 3600],
)

TASK_ERRORS_TOTAL = Counter(
    "medical_paper_task_errors_total",
    "Total task-level errors",
    ["paper_type", "error_type"],
)

# ============================================================================
# Pipeline Step Metrics
# ============================================================================

STEP_DURATION = Histogram(
    "medical_paper_step_duration_seconds",
    "Duration of each pipeline step",
    ["step"],  # literature, stats, writer, compliance
    buckets=[1, 5, 10, 30, 60, 120, 300],
)

STEP_TOTAL = Counter(
    "medical_paper_step_total",
    "Total pipeline step executions",
    ["step", "status"],
)

# ============================================================================
# Agent Metrics
# ============================================================================

AGENT_CALLS_TOTAL = Counter(
    "medical_paper_agent_calls_total",
    "Total sub-agent invocations",
    ["agent", "status"],  # agent: literature/stats/writer/compliance
)

AGENT_LATENCY = Histogram(
    "medical_paper_agent_latency_seconds",
    "Sub-agent execution latency",
    ["agent"],
    buckets=[0.5, 1, 2, 5, 10, 20, 30, 60, 120],
)

AGENT_TOOL_CALLS = Counter(
    "medical_paper_agent_tool_calls_total",
    "Total tool calls by sub-agents",
    ["agent", "tool_name", "status"],
)

# ============================================================================
# Business Metrics
# ============================================================================

COMPLIANCE_SCORE = Gauge(
    "medical_paper_compliance_score",
    "Latest compliance score for a task",
    ["paper_type", "checklist_type"],
)

REVISION_ROUNDS = Histogram(
    "medical_paper_revision_rounds",
    "Number of revision rounds per task",
    ["paper_type"],
    buckets=[0, 1, 2, 3, 4, 5],
)

REFERENCES_COUNT = Histogram(
    "medical_paper_references_count",
    "Number of references collected per task",
    ["paper_type"],
    buckets=[5, 10, 15, 20, 25, 30, 50],
)

MANUSCRIPT_WORD_COUNT = Histogram(
    "medical_paper_manuscript_word_count",
    "Total word count of generated manuscripts",
    ["paper_type"],
    buckets=[500, 1000, 2000, 3000, 5000, 8000, 10000],
)

# ============================================================================
# Resource Metrics
# ============================================================================

ACTIVE_TASKS = Gauge(
    "medical_paper_active_tasks",
    "Number of currently running tasks",
)

ACTIVE_STREAMS = Gauge(
    "medical_paper_active_streams",
    "Number of active streaming connections",
)

AGENT_INFO = Info(
    "medical_paper_agent",
    "Information about the Medical Paper agent",
)

AGENT_INFO.info(
    {
        "version": "1.0.0",
        "framework": "langgraph",
        "supported_types": "rct,cohort,meta_analysis",
    }
)


# ============================================================================
# Helper Functions
# ============================================================================


def record_task_created(paper_type: str):
    """Record a new task creation."""
    TASK_TOTAL.labels(paper_type=paper_type, status="created").inc()
    ACTIVE_TASKS.inc()


def record_task_completed(paper_type: str, duration: float):
    """Record successful task completion."""
    TASK_TOTAL.labels(paper_type=paper_type, status="completed").inc()
    TASK_DURATION.labels(paper_type=paper_type).observe(duration)
    ACTIVE_TASKS.dec()


def record_task_failed(paper_type: str, error_type: str):
    """Record task failure."""
    TASK_TOTAL.labels(paper_type=paper_type, status="failed").inc()
    TASK_ERRORS_TOTAL.labels(paper_type=paper_type, error_type=error_type).inc()
    ACTIVE_TASKS.dec()


def record_step(step: str, status: str, duration: float):
    """Record a pipeline step execution."""
    STEP_TOTAL.labels(step=step, status=status).inc()
    STEP_DURATION.labels(step=step).observe(duration)


def record_agent_call(agent: str, status: str, duration: float):
    """Record a sub-agent invocation."""
    AGENT_CALLS_TOTAL.labels(agent=agent, status=status).inc()
    AGENT_LATENCY.labels(agent=agent).observe(duration)


def record_agent_tool_call(agent: str, tool_name: str, status: str):
    """Record a tool call by a sub-agent."""
    AGENT_TOOL_CALLS.labels(agent=agent, tool_name=tool_name, status=status).inc()


def record_compliance_score(paper_type: str, checklist_type: str, score: float):
    """Record a compliance score."""
    COMPLIANCE_SCORE.labels(paper_type=paper_type, checklist_type=checklist_type).set(
        score
    )


def record_revision_rounds(paper_type: str, rounds: int):
    """Record the number of revision rounds."""
    REVISION_ROUNDS.labels(paper_type=paper_type).observe(rounds)


def record_references_count(paper_type: str, count: int):
    """Record the number of references collected."""
    REFERENCES_COUNT.labels(paper_type=paper_type).observe(count)


def record_manuscript_word_count(paper_type: str, word_count: int):
    """Record the manuscript word count."""
    MANUSCRIPT_WORD_COUNT.labels(paper_type=paper_type).observe(word_count)


def stream_started():
    """Record a streaming connection started."""
    ACTIVE_STREAMS.inc()


def stream_ended():
    """Record a streaming connection ended."""
    ACTIVE_STREAMS.dec()


# ============================================================================
# Context Managers
# ============================================================================


@contextmanager
def track_step(step: str):
    """Context manager to track pipeline step metrics."""
    start_time = time.time()
    status = "success"
    try:
        yield
    except Exception:
        status = "error"
        raise
    finally:
        duration = time.time() - start_time
        record_step(step, status, duration)


@contextmanager
def track_agent(agent: str):
    """Context manager to track sub-agent metrics."""
    start_time = time.time()
    status = "success"
    try:
        yield
    except Exception:
        status = "error"
        raise
    finally:
        duration = time.time() - start_time
        record_agent_call(agent, status, duration)


@contextmanager
def track_streaming():
    """Context manager to track streaming connections."""
    stream_started()
    try:
        yield
    finally:
        stream_ended()
