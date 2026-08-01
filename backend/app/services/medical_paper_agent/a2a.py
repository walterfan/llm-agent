"""
A2A (Agent-to-Agent) communication utilities for the Medical Paper Agent.

Provides message creation, error classification, and retry logic
for inter-agent communication within the paper writing workflow.
"""

import time
from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class MedicalA2AStatus(str, Enum):
    """Status of a medical A2A message."""

    PENDING = "pending"
    OK = "ok"
    ERROR = "error"


class MedicalA2AErrorCode(str, Enum):
    """Error codes with associated retry strategies."""

    VALIDATION_ERROR = "VALIDATION_ERROR"  # Bad input, don't retry
    TOOL_ERROR = "TOOL_ERROR"  # Tool failed, retry up to 3x
    TIMEOUT = "TIMEOUT"  # Timed out, retry 2x with longer timeout
    RATE_LIMIT = "RATE_LIMIT"  # Rate limited, wait and retry
    LLM_ERROR = "LLM_ERROR"  # LLM returned error, retry 2x


# Retry configuration per error code
RETRY_CONFIG: dict[str, dict[str, Any]] = {
    MedicalA2AErrorCode.VALIDATION_ERROR: {"max_retries": 0, "backoff": 0},
    MedicalA2AErrorCode.TOOL_ERROR: {"max_retries": 3, "backoff": 2.0},
    MedicalA2AErrorCode.TIMEOUT: {"max_retries": 2, "backoff": 5.0},
    MedicalA2AErrorCode.RATE_LIMIT: {"max_retries": 3, "backoff": 10.0},
    MedicalA2AErrorCode.LLM_ERROR: {"max_retries": 2, "backoff": 3.0},
}


class MedicalA2AError(BaseModel):
    """Structured error for medical A2A messages."""

    code: MedicalA2AErrorCode
    message: str
    recoverable: bool = False
    retry_after: Optional[int] = None


class MedicalA2AMetrics(BaseModel):
    """Performance metrics for an A2A interaction."""

    latency_ms: float = 0
    tokens_in: int = 0
    tokens_out: int = 0
    tool_calls: int = 0


class MedicalA2AMessage(BaseModel):
    """
    Structured A2A message for medical paper inter-agent communication.

    Every message between supervisor and sub-agents uses this contract
    for traceability and structured error handling.
    """

    protocol: str = "a2a.medical.v1"
    id: str = Field(default_factory=lambda: f"med_{uuid4().hex[:12]}")
    correlation_id: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")

    sender: str
    receiver: str
    intent: str

    input: Optional[dict[str, Any]] = None
    status: MedicalA2AStatus = MedicalA2AStatus.PENDING
    output: Optional[dict[str, Any]] = None

    error: Optional[MedicalA2AError] = None
    metrics: Optional[MedicalA2AMetrics] = None


def create_medical_request(
    sender: str,
    receiver: str,
    intent: str,
    input_data: Optional[dict[str, Any]] = None,
    correlation_id: Optional[str] = None,
) -> MedicalA2AMessage:
    """Create an A2A request message for medical paper workflow."""
    return MedicalA2AMessage(
        sender=sender,
        receiver=receiver,
        intent=intent,
        input=input_data,
        correlation_id=correlation_id,
        status=MedicalA2AStatus.PENDING,
    )


def create_medical_response(
    request: MedicalA2AMessage,
    status: MedicalA2AStatus = MedicalA2AStatus.OK,
    output: Optional[dict[str, Any]] = None,
    error: Optional[MedicalA2AError] = None,
    metrics: Optional[MedicalA2AMetrics] = None,
) -> MedicalA2AMessage:
    """Create an A2A response from a request."""
    return MedicalA2AMessage(
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


def classify_error(error: Exception) -> MedicalA2AError:
    """
    Classify an exception into a structured A2A error.

    Maps common exception types to error codes with retry guidance.
    """
    error_msg = str(error)

    if "timeout" in error_msg.lower() or "timed out" in error_msg.lower():
        return MedicalA2AError(
            code=MedicalA2AErrorCode.TIMEOUT,
            message=error_msg,
            recoverable=True,
            retry_after=5,
        )
    elif "rate limit" in error_msg.lower() or "429" in error_msg:
        return MedicalA2AError(
            code=MedicalA2AErrorCode.RATE_LIMIT,
            message=error_msg,
            recoverable=True,
            retry_after=10,
        )
    elif "validation" in error_msg.lower() or isinstance(
        error, (ValueError, TypeError)
    ):
        return MedicalA2AError(
            code=MedicalA2AErrorCode.VALIDATION_ERROR,
            message=error_msg,
            recoverable=False,
        )
    else:
        return MedicalA2AError(
            code=MedicalA2AErrorCode.TOOL_ERROR,
            message=error_msg,
            recoverable=True,
        )


def should_retry(error: MedicalA2AError, attempt: int) -> bool:
    """Determine if an error should be retried based on error code and attempt count."""
    config = RETRY_CONFIG.get(error.code, {"max_retries": 0})
    return error.recoverable and attempt < config["max_retries"]


def get_backoff_seconds(error: MedicalA2AError, attempt: int) -> float:
    """Get exponential backoff duration for a retry attempt."""
    config = RETRY_CONFIG.get(error.code, {"backoff": 1.0})
    base = config["backoff"]
    return base * (2**attempt)
