"""
DateTime tool for the Personal Secretary agent.

Provides current date and time information.
"""

from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

from pydantic import BaseModel, Field

from app.services.secretary_agent.tracing import trace_tool_call


class DateTimeInput(BaseModel):
    """Input schema for datetime tool."""

    timezone: Optional[str] = Field(
        default="Asia/Shanghai",
        description="Timezone name (e.g., 'Asia/Shanghai', 'UTC', 'America/New_York')",
    )
    format: Optional[str] = Field(
        default=None, description="Custom format string (e.g., '%Y-%m-%d %H:%M:%S')"
    )


class DateTimeResponse(BaseModel):
    """Response schema for datetime tool."""

    datetime: str = Field(description="Formatted datetime string")
    date: str = Field(description="Date in YYYY-MM-DD format")
    time: str = Field(description="Time in HH:MM:SS format")
    weekday: str = Field(description="Day of the week")
    weekday_chinese: str = Field(description="Day of the week in Chinese")
    timezone: str = Field(description="Timezone used")
    unix_timestamp: int = Field(description="Unix timestamp")


WEEKDAY_CHINESE = {
    0: "星期一",
    1: "星期二",
    2: "星期三",
    3: "星期四",
    4: "星期五",
    5: "星期六",
    6: "星期日",
}


@trace_tool_call
def get_current_datetime(
    timezone: str = "Asia/Shanghai", format: Optional[str] = None
) -> DateTimeResponse:
    """
    Get the current date and time.

    Args:
        timezone: Timezone name (default: Asia/Shanghai)
        format: Optional custom format string

    Returns:
        DateTimeResponse with current date/time information
    """
    try:
        tz = ZoneInfo(timezone)
    except Exception:
        # Fallback to UTC if timezone is invalid
        tz = ZoneInfo("UTC")
        timezone = "UTC"

    now = datetime.now(tz)

    # Format datetime
    if format:
        try:
            formatted = now.strftime(format)
        except Exception:
            formatted = now.isoformat()
    else:
        formatted = now.strftime("%Y-%m-%d %H:%M:%S %Z")

    return DateTimeResponse(
        datetime=formatted,
        date=now.strftime("%Y-%m-%d"),
        time=now.strftime("%H:%M:%S"),
        weekday=now.strftime("%A"),
        weekday_chinese=WEEKDAY_CHINESE[now.weekday()],
        timezone=timezone,
        unix_timestamp=int(now.timestamp()),
    )
