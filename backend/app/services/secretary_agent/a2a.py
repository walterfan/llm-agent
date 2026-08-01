"""
A2A (Agent-to-Agent) message contract for the Personal Secretary agent system.

Defines structured communication schemas between the Supervisor and SubAgents.
Based on the principle: "Don't rely on natural-language guessing, use contracts."

Key fields that MUST be present:
- id / correlation_id: for tracing
- status: for error classification
- output: structured result
- error: typed error info for retry strategies

Reference: journal_20260206_ai-agent-workflow.md Section 2
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class A2AProtocol(str, Enum):
    """Protocol version for A2A messages."""

    V1 = "a2a.v1"


class A2AStatus(str, Enum):
    """Status of an A2A message/response."""

    OK = "ok"
    ERROR = "error"
    PARTIAL = "partial"  # partial result (e.g., streaming)
    TIMEOUT = "timeout"
    VALIDATION_ERROR = "validation_error"
    TOOL_ERROR = "tool_error"


class A2AErrorType(str, Enum):
    """Classification of errors for retry strategy decisions."""

    VALIDATION_ERROR = "VALIDATION_ERROR"  # bad input, don't retry
    TOOL_ERROR = "TOOL_ERROR"  # tool failed, may retry
    LLM_ERROR = "LLM_ERROR"  # LLM failed, may retry with backoff
    TIMEOUT = "TIMEOUT"  # timed out, retry with longer timeout
    UNKNOWN = "UNKNOWN"  # unknown error


class A2AError(BaseModel):
    """Structured error information for A2A messages."""

    type: A2AErrorType
    message: str
    retryable: bool = False
    details: Optional[dict[str, Any]] = None


class A2AArtifact(BaseModel):
    """Artifact produced by a SubAgent."""

    type: str  # e.g., "markdown", "json", "image"
    path: Optional[str] = None  # file path if saved
    content: Optional[str] = None  # inline content if small


class A2AMetrics(BaseModel):
    """Performance metrics for an A2A interaction."""

    latency_ms: float
    tokens_in: Optional[int] = None
    tokens_out: Optional[int] = None
    tool_calls: int = 0


class A2AMessage(BaseModel):
    """
    Structured A2A message for inter-agent communication.

    This is the canonical contract between Supervisor and SubAgents.
    Every inter-agent interaction should be logged using this schema
    for observability and auditability.

    Example:
        msg = A2AMessage(
            sender="supervisor",
            receiver="learning_agent",
            intent="learn_word",
            input={"word": "serendipity"},
        )
    """

    protocol: A2AProtocol = A2AProtocol.V1
    id: str = Field(default_factory=lambda: f"msg_{uuid4().hex[:12]}")
    correlation_id: Optional[str] = None  # trace_id from tracing module
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")

    # Routing
    sender: str  # e.g., "supervisor", "learning_agent"
    receiver: str  # e.g., "learning_agent", "supervisor"
    intent: str  # e.g., "learn_word", "get_weather", "route_request"

    # Payload
    input: Optional[dict[str, Any]] = None
    status: A2AStatus = A2AStatus.OK
    output: Optional[dict[str, Any]] = None

    # Error & artifacts
    error: Optional[A2AError] = None
    artifact: Optional[list[A2AArtifact]] = None

    # Observability
    metrics: Optional[A2AMetrics] = None


def create_a2a_request(
    sender: str,
    receiver: str,
    intent: str,
    input_data: Optional[dict[str, Any]] = None,
    correlation_id: Optional[str] = None,
) -> A2AMessage:
    """Factory to create an A2A request message."""
    return A2AMessage(
        sender=sender,
        receiver=receiver,
        intent=intent,
        input=input_data,
        correlation_id=correlation_id,
    )


def create_a2a_response(
    request: A2AMessage,
    status: A2AStatus = A2AStatus.OK,
    output: Optional[dict[str, Any]] = None,
    error: Optional[A2AError] = None,
    metrics: Optional[A2AMetrics] = None,
) -> A2AMessage:
    """Factory to create an A2A response from a request."""
    return A2AMessage(
        sender=request.receiver,
        receiver=request.sender,
        intent=f"{request.intent}_response",
        correlation_id=request.correlation_id,
        status=status,
        input=request.input,
        output=output,
        error=error,
        metrics=metrics,
    )
