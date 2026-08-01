"""
Tracing and logging module for the Personal Secretary agent.

Provides structured logging for all LLM calls and tool invocations,
enabling debugging, auditing, and performance analysis.
"""

import contextvars
import functools
import json
import logging
import time
from datetime import datetime
from typing import Any, Callable, Optional, TypeVar
from uuid import uuid4

from pydantic import BaseModel

logger = logging.getLogger("secretary_agent")

# Type variable for generic decorator
F = TypeVar("F", bound=Callable[..., Any])


# ============================================================================
# Log Models
# ============================================================================


class LLMCallLog(BaseModel):
    """Structured log for LLM calls."""

    trace_id: str
    call_id: str
    timestamp: str
    call_type: str = "llm"

    # LLM specific
    model: Optional[str] = None
    prompt_template: Optional[str] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None

    # Timing
    duration_ms: float

    # Status
    status: str  # "success" | "error"
    error_message: Optional[str] = None

    # Context
    user_id: Optional[int] = None
    session_id: Optional[str] = None


class ToolCallLog(BaseModel):
    """Structured log for tool calls."""

    trace_id: str
    call_id: str
    timestamp: str
    call_type: str = "tool"

    # Tool specific
    tool_name: str
    tool_args: dict
    tool_result: Optional[str] = None  # Truncated to max 1000 chars

    # Timing
    duration_ms: float

    # Status
    status: str  # "success" | "error"
    error_message: Optional[str] = None

    # Context
    user_id: Optional[int] = None
    session_id: Optional[str] = None


# ============================================================================
# Trace Context (Thread-local)
# ============================================================================

_trace_context: contextvars.ContextVar[dict] = contextvars.ContextVar(
    "trace_context", default={}
)


def new_trace(user_id: Optional[int] = None, session_id: Optional[str] = None) -> str:
    """
    Start a new trace for a chat request.

    Args:
        user_id: ID of the current user
        session_id: ID of the current chat session

    Returns:
        The new trace ID
    """
    trace_id = str(uuid4())
    _trace_context.set(
        {
            "trace_id": trace_id,
            "user_id": user_id,
            "session_id": session_id,
            "calls": [],
        }
    )
    logger.debug(f"Started new trace: {trace_id}")
    return trace_id


def get_trace_id() -> Optional[str]:
    """Get the current trace ID."""
    ctx = _trace_context.get()
    return ctx.get("trace_id")


def get_trace_context() -> dict:
    """Get the full trace context."""
    return _trace_context.get()


def clear_trace() -> None:
    """Clear the current trace context."""
    _trace_context.set({})


# ============================================================================
# Helper Functions
# ============================================================================


def truncate(value: Any, max_len: int = 500) -> str:
    """Truncate a value to a maximum length for logging."""
    s = str(value)
    return s[:max_len] + "..." if len(s) > max_len else s


def safe_serialize(obj: Any) -> Any:
    """Safely serialize an object for logging."""
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    elif hasattr(obj, "__dict__"):
        return {k: truncate(v) for k, v in obj.__dict__.items()}
    else:
        return truncate(str(obj))


# ============================================================================
# JSON Log Formatter
# ============================================================================


class StructuredFormatter(logging.Formatter):
    """JSON formatter for structured logs."""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
        }

        # Add extra fields (llm_call, tool_call)
        if hasattr(record, "llm_call"):
            log_data["llm_call"] = record.llm_call
        if hasattr(record, "tool_call"):
            log_data["tool_call"] = record.tool_call
        if hasattr(record, "trace_id"):
            log_data["trace_id"] = record.trace_id

        return json.dumps(log_data, default=str, ensure_ascii=False)


# ============================================================================
# Decorators
# ============================================================================


def trace_llm_call(prompt_template: Optional[str] = None):
    """
    Decorator to trace LLM calls.

    Usage:
        @trace_llm_call(prompt_template="learning_tools.yaml:learn_word")
        async def call_llm(prompt: str, model: str) -> str:
            ...
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            call_id = str(uuid4())
            ctx = get_trace_context()
            start_time = time.perf_counter()

            log_entry = {
                "trace_id": ctx.get("trace_id"),
                "call_id": call_id,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "call_type": "llm",
                "prompt_template": prompt_template,
                "model": kwargs.get("model") or (args[1] if len(args) > 1 else None),
                "user_id": ctx.get("user_id"),
                "session_id": ctx.get("session_id"),
            }

            try:
                result = await func(*args, **kwargs)
                duration_ms = (time.perf_counter() - start_time) * 1000

                # Extract token usage if available
                if hasattr(result, "usage") and result.usage:
                    log_entry["prompt_tokens"] = getattr(
                        result.usage, "prompt_tokens", None
                    )
                    log_entry["completion_tokens"] = getattr(
                        result.usage, "completion_tokens", None
                    )
                    log_entry["total_tokens"] = getattr(
                        result.usage, "total_tokens", None
                    )

                log_entry["duration_ms"] = duration_ms
                log_entry["status"] = "success"

                logger.info(
                    f"LLM call completed ({duration_ms:.2f}ms)",
                    extra={"llm_call": log_entry, "trace_id": ctx.get("trace_id")},
                )

                return result

            except Exception as e:
                duration_ms = (time.perf_counter() - start_time) * 1000
                log_entry["duration_ms"] = duration_ms
                log_entry["status"] = "error"
                log_entry["error_message"] = str(e)

                logger.error(
                    f"LLM call failed: {e}",
                    extra={"llm_call": log_entry, "trace_id": ctx.get("trace_id")},
                    exc_info=True,
                )
                raise

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            call_id = str(uuid4())
            ctx = get_trace_context()
            start_time = time.perf_counter()

            log_entry = {
                "trace_id": ctx.get("trace_id"),
                "call_id": call_id,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "call_type": "llm",
                "prompt_template": prompt_template,
                "model": kwargs.get("model") or (args[1] if len(args) > 1 else None),
                "user_id": ctx.get("user_id"),
                "session_id": ctx.get("session_id"),
            }

            try:
                result = func(*args, **kwargs)
                duration_ms = (time.perf_counter() - start_time) * 1000

                log_entry["duration_ms"] = duration_ms
                log_entry["status"] = "success"

                logger.info(
                    f"LLM call completed ({duration_ms:.2f}ms)",
                    extra={"llm_call": log_entry, "trace_id": ctx.get("trace_id")},
                )

                return result

            except Exception as e:
                duration_ms = (time.perf_counter() - start_time) * 1000
                log_entry["duration_ms"] = duration_ms
                log_entry["status"] = "error"
                log_entry["error_message"] = str(e)

                logger.error(
                    f"LLM call failed: {e}",
                    extra={"llm_call": log_entry, "trace_id": ctx.get("trace_id")},
                    exc_info=True,
                )
                raise

        # Return appropriate wrapper based on function type
        import asyncio

        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        return sync_wrapper  # type: ignore

    return decorator


def trace_tool_call(func: F) -> F:
    """
    Decorator to trace tool calls.

    Usage:
        @tool("learn_word", args_schema=LearnWordInput)
        @trace_tool_call
        async def learn_word(word: str) -> WordResponse:
            ...
    """

    @functools.wraps(func)
    async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
        call_id = str(uuid4())
        ctx = get_trace_context()
        tool_name = func.__name__
        start_time = time.perf_counter()

        # Serialize args for logging
        tool_args = {k: truncate(v) for k, v in kwargs.items()}

        log_entry = {
            "trace_id": ctx.get("trace_id"),
            "call_id": call_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "call_type": "tool",
            "tool_name": tool_name,
            "tool_args": tool_args,
            "user_id": ctx.get("user_id"),
            "session_id": ctx.get("session_id"),
        }

        logger.info(
            f"Tool call started: {tool_name}",
            extra={"tool_call": log_entry, "trace_id": ctx.get("trace_id")},
        )

        try:
            result = await func(*args, **kwargs)
            duration_ms = (time.perf_counter() - start_time) * 1000

            # Truncate result for logging
            result_str = truncate(
                (
                    result.model_dump_json()
                    if hasattr(result, "model_dump_json")
                    else str(result)
                ),
                max_len=1000,
            )

            log_entry["tool_result"] = result_str
            log_entry["duration_ms"] = duration_ms
            log_entry["status"] = "success"

            logger.info(
                f"Tool call completed: {tool_name} ({duration_ms:.2f}ms)",
                extra={"tool_call": log_entry, "trace_id": ctx.get("trace_id")},
            )

            return result

        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            log_entry["duration_ms"] = duration_ms
            log_entry["status"] = "error"
            log_entry["error_message"] = str(e)

            logger.error(
                f"Tool call failed: {tool_name} - {e}",
                extra={"tool_call": log_entry, "trace_id": ctx.get("trace_id")},
                exc_info=True,
            )
            raise

    @functools.wraps(func)
    def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
        call_id = str(uuid4())
        ctx = get_trace_context()
        tool_name = func.__name__
        start_time = time.perf_counter()

        tool_args = {k: truncate(v) for k, v in kwargs.items()}

        log_entry = {
            "trace_id": ctx.get("trace_id"),
            "call_id": call_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "call_type": "tool",
            "tool_name": tool_name,
            "tool_args": tool_args,
            "user_id": ctx.get("user_id"),
            "session_id": ctx.get("session_id"),
        }

        logger.info(
            f"Tool call started: {tool_name}",
            extra={"tool_call": log_entry, "trace_id": ctx.get("trace_id")},
        )

        try:
            result = func(*args, **kwargs)
            duration_ms = (time.perf_counter() - start_time) * 1000

            result_str = truncate(
                (
                    result.model_dump_json()
                    if hasattr(result, "model_dump_json")
                    else str(result)
                ),
                max_len=1000,
            )

            log_entry["tool_result"] = result_str
            log_entry["duration_ms"] = duration_ms
            log_entry["status"] = "success"

            logger.info(
                f"Tool call completed: {tool_name} ({duration_ms:.2f}ms)",
                extra={"tool_call": log_entry, "trace_id": ctx.get("trace_id")},
            )

            return result

        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            log_entry["duration_ms"] = duration_ms
            log_entry["status"] = "error"
            log_entry["error_message"] = str(e)

            logger.error(
                f"Tool call failed: {tool_name} - {e}",
                extra={"tool_call": log_entry, "trace_id": ctx.get("trace_id")},
                exc_info=True,
            )
            raise

    # Return appropriate wrapper based on function type
    import asyncio

    if asyncio.iscoroutinefunction(func):
        return async_wrapper  # type: ignore
    return sync_wrapper  # type: ignore


# ============================================================================
# Logger Configuration
# ============================================================================


def configure_logger(level: str = "INFO", use_json: bool = True) -> None:
    """
    Configure the secretary_agent logger.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR)
        use_json: Whether to use JSON formatting
    """
    secretary_logger = logging.getLogger("secretary_agent")
    secretary_logger.setLevel(getattr(logging, level.upper()))

    # Remove existing handlers
    secretary_logger.handlers.clear()

    # Add new handler
    handler = logging.StreamHandler()
    if use_json:
        handler.setFormatter(StructuredFormatter())
    else:
        handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )

    secretary_logger.addHandler(handler)
