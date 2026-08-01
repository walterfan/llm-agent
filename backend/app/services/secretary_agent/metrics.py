"""
Prometheus metrics for the Personal Secretary agent.

Implements the Metrics-Driven Development (MDD) approach with:
- RED metrics (Rate, Errors, Duration)
- Tool metrics
- Business metrics
- Resource metrics
"""

import time
from contextlib import contextmanager
from functools import wraps
from typing import Any, Callable, Optional

from prometheus_client import Counter, Histogram, Gauge, Info

# ============================================================================
# RED Metrics (Rate, Errors, Duration)
# ============================================================================

# Chat request metrics
CHAT_REQUESTS_TOTAL = Counter(
    "secretary_chat_requests_total",
    "Total number of chat requests",
    ["method", "status"],  # method: streaming/non-streaming, status: success/error
)

CHAT_REQUEST_DURATION = Histogram(
    "secretary_chat_request_duration_seconds",
    "Duration of chat requests in seconds",
    ["method"],
    buckets=[0.5, 1, 2, 5, 10, 20, 30, 60, 120],
)

CHAT_FIRST_TOKEN_LATENCY = Histogram(
    "secretary_chat_first_token_latency_seconds",
    "Time to first token in streaming responses",
    buckets=[0.1, 0.25, 0.5, 1, 2, 5, 10],
)

CHAT_ERRORS_TOTAL = Counter(
    "secretary_chat_errors_total",
    "Total number of chat errors",
    ["error_type"],  # llm_error, tool_error, timeout, validation, other
)

# ============================================================================
# LLM Metrics
# ============================================================================

LLM_CALLS_TOTAL = Counter(
    "secretary_llm_calls_total",
    "Total number of LLM API calls",
    ["model", "status"],
)

LLM_CALL_DURATION = Histogram(
    "secretary_llm_call_duration_seconds",
    "Duration of LLM API calls",
    ["model"],
    buckets=[0.5, 1, 2, 5, 10, 20, 30, 60],
)

LLM_TOKENS_TOTAL = Counter(
    "secretary_llm_tokens_total",
    "Total tokens used in LLM calls",
    ["model", "type"],  # type: prompt/completion
)

LLM_COST_TOTAL = Counter(
    "secretary_llm_cost_total",
    "Estimated cost of LLM calls in USD",
    ["model"],
)

# ============================================================================
# Tool Metrics
# ============================================================================

TOOL_CALLS_TOTAL = Counter(
    "secretary_tool_calls_total",
    "Total number of tool calls",
    ["tool_name", "status"],  # status: success/error
)

TOOL_CALL_DURATION = Histogram(
    "secretary_tool_call_duration_seconds",
    "Duration of tool calls",
    ["tool_name"],
    buckets=[0.01, 0.05, 0.1, 0.5, 1, 2, 5, 10],
)

TOOL_ERRORS_TOTAL = Counter(
    "secretary_tool_errors_total",
    "Total number of tool errors",
    ["tool_name", "error_type"],
)

# ============================================================================
# Business Metrics
# ============================================================================

LEARNING_RECORDS_TOTAL = Counter(
    "secretary_learning_records_total",
    "Total learning records created",
    ["type"],  # word, sentence, topic, article, question, idea
)

LEARNING_REVIEWS_TOTAL = Counter(
    "secretary_learning_reviews_total",
    "Total learning record reviews",
    ["type"],
)

SESSIONS_CREATED_TOTAL = Counter(
    "secretary_sessions_created_total",
    "Total chat sessions created",
)

MESSAGES_TOTAL = Counter(
    "secretary_messages_total",
    "Total messages in chat",
    ["role"],  # user, assistant, tool
)

# ============================================================================
# Resource Metrics
# ============================================================================

ACTIVE_SESSIONS = Gauge(
    "secretary_active_sessions",
    "Number of active chat sessions",
)

ACTIVE_STREAMS = Gauge(
    "secretary_active_streams",
    "Number of active streaming connections",
)

AGENT_INFO = Info(
    "secretary_agent",
    "Information about the Secretary agent",
)

# Initialize agent info
AGENT_INFO.info(
    {
        "version": "1.0.0",
        "framework": "langchain",
    }
)


# ============================================================================
# Metric Helper Functions
# ============================================================================


def record_chat_request(method: str, status: str, duration: float):
    """Record metrics for a chat request."""
    CHAT_REQUESTS_TOTAL.labels(method=method, status=status).inc()
    CHAT_REQUEST_DURATION.labels(method=method).observe(duration)


def record_chat_error(error_type: str):
    """Record a chat error."""
    CHAT_ERRORS_TOTAL.labels(error_type=error_type).inc()


def record_first_token_latency(latency: float):
    """Record time to first token."""
    CHAT_FIRST_TOKEN_LATENCY.observe(latency)


def record_llm_call(
    model: str,
    status: str,
    duration: float,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    cost: float = 0.0,
):
    """Record metrics for an LLM call."""
    LLM_CALLS_TOTAL.labels(model=model, status=status).inc()
    LLM_CALL_DURATION.labels(model=model).observe(duration)

    if prompt_tokens > 0:
        LLM_TOKENS_TOTAL.labels(model=model, type="prompt").inc(prompt_tokens)
    if completion_tokens > 0:
        LLM_TOKENS_TOTAL.labels(model=model, type="completion").inc(completion_tokens)
    if cost > 0:
        LLM_COST_TOTAL.labels(model=model).inc(cost)


def record_tool_call(tool_name: str, status: str, duration: float):
    """Record metrics for a tool call."""
    TOOL_CALLS_TOTAL.labels(tool_name=tool_name, status=status).inc()
    TOOL_CALL_DURATION.labels(tool_name=tool_name).observe(duration)


def record_tool_error(tool_name: str, error_type: str):
    """Record a tool error."""
    TOOL_ERRORS_TOTAL.labels(tool_name=tool_name, error_type=error_type).inc()


def record_learning_record(record_type: str):
    """Record a learning record creation."""
    LEARNING_RECORDS_TOTAL.labels(type=record_type).inc()


def record_learning_review(record_type: str):
    """Record a learning record review."""
    LEARNING_REVIEWS_TOTAL.labels(type=record_type).inc()


def record_session_created():
    """Record a new session creation."""
    SESSIONS_CREATED_TOTAL.inc()
    ACTIVE_SESSIONS.inc()


def record_session_deleted():
    """Record a session deletion."""
    ACTIVE_SESSIONS.dec()


def record_message(role: str):
    """Record a message."""
    MESSAGES_TOTAL.labels(role=role).inc()


def stream_started():
    """Record streaming started."""
    ACTIVE_STREAMS.inc()


def stream_ended():
    """Record streaming ended."""
    ACTIVE_STREAMS.dec()


# ============================================================================
# Decorators
# ============================================================================


@contextmanager
def track_chat_request(method: str = "non-streaming"):
    """Context manager to track chat request metrics."""
    start_time = time.time()
    status = "success"
    try:
        yield
    except Exception as e:
        status = "error"
        error_type = type(e).__name__
        record_chat_error(error_type)
        raise
    finally:
        duration = time.time() - start_time
        record_chat_request(method, status, duration)


@contextmanager
def track_streaming():
    """Context manager to track streaming connections."""
    stream_started()
    try:
        yield
    finally:
        stream_ended()


def track_tool(tool_name: str):
    """Decorator to track tool call metrics."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            status = "success"
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                status = "error"
                record_tool_error(tool_name, type(e).__name__)
                raise
            finally:
                duration = time.time() - start_time
                record_tool_call(tool_name, status, duration)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            status = "success"
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                status = "error"
                record_tool_error(tool_name, type(e).__name__)
                raise
            finally:
                duration = time.time() - start_time
                record_tool_call(tool_name, status, duration)

        import asyncio

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


def track_llm(model: str = "unknown"):
    """Decorator to track LLM call metrics."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            status = "success"
            try:
                result = await func(*args, **kwargs)
                # Try to extract token usage from result
                prompt_tokens = 0
                completion_tokens = 0
                if hasattr(result, "usage"):
                    prompt_tokens = getattr(result.usage, "prompt_tokens", 0)
                    completion_tokens = getattr(result.usage, "completion_tokens", 0)

                record_llm_call(
                    model=model,
                    status=status,
                    duration=time.time() - start_time,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                )
                return result
            except Exception as e:
                status = "error"
                record_llm_call(
                    model=model,
                    status=status,
                    duration=time.time() - start_time,
                )
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            status = "success"
            try:
                result = func(*args, **kwargs)
                record_llm_call(
                    model=model,
                    status=status,
                    duration=time.time() - start_time,
                )
                return result
            except Exception as e:
                status = "error"
                record_llm_call(
                    model=model,
                    status=status,
                    duration=time.time() - start_time,
                )
                raise

        import asyncio

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator
