"""
Reminder tools for Personal Secretary agent.

Allows the agent to create and manage reminders for the user.
"""

from datetime import datetime, timedelta
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.reminder import ReminderRepeat, ReminderStatus
from app.services.secretary_agent.tracing import trace_tool_call


class CreateReminderInput(BaseModel):
    """Input schema for create_reminder tool."""

    title: str = Field(..., description="Reminder title")
    remind_at: str = Field(
        ..., description="When to remind in ISO format (YYYY-MM-DD HH:MM)"
    )
    description: Optional[str] = Field(None, description="Optional description")
    repeat: str = Field(
        "none", description="Repeat: none, daily, weekly, monthly, yearly"
    )
    tags: Optional[List[str]] = Field(None, description="Optional tags")


class CreateReminderResponse(BaseModel):
    """Response schema for create_reminder tool."""

    reminder_id: str
    title: str
    remind_at: str
    repeat: str
    message: str


class ListRemindersInput(BaseModel):
    """Input schema for list_reminders tool."""

    include_past: bool = Field(False, description="Include past/triggered reminders")
    limit: int = Field(20, description="Maximum number of reminders", ge=1, le=100)


class ListRemindersResponse(BaseModel):
    """Response schema for list_reminders tool."""

    reminders: List[dict]
    total: int
    due_count: int
    message: str


class SnoozeReminderInput(BaseModel):
    """Input schema for snooze_reminder tool."""

    reminder_id: str = Field(..., description="ID of the reminder to snooze")
    snooze_minutes: int = Field(15, description="Minutes to snooze", ge=1, le=1440)


class SnoozeReminderResponse(BaseModel):
    """Response schema for snooze_reminder tool."""

    reminder_id: str
    title: str
    snoozed_until: str
    message: str


def _parse_remind_at(remind_at_str: str) -> Optional[datetime]:
    """Parse remind_at string to datetime."""
    formats = [
        "%Y-%m-%d %H:%M",
        "%Y-%m-%dT%H:%M",
        "%Y/%m/%d %H:%M",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(remind_at_str, fmt)
        except ValueError:
            continue

    # Try relative time parsing
    remind_at_lower = remind_at_str.lower()
    now = datetime.utcnow()

    if "分钟后" in remind_at_str or "minutes" in remind_at_lower:
        try:
            minutes = int("".join(filter(str.isdigit, remind_at_str)))
            return now + timedelta(minutes=minutes)
        except ValueError:
            pass

    if "小时后" in remind_at_str or "hours" in remind_at_lower:
        try:
            hours = int("".join(filter(str.isdigit, remind_at_str)))
            return now + timedelta(hours=hours)
        except ValueError:
            pass

    if "天后" in remind_at_str or "days" in remind_at_lower:
        try:
            days = int("".join(filter(str.isdigit, remind_at_str)))
            return now + timedelta(days=days)
        except ValueError:
            pass

    return None


@trace_tool_call
def create_reminder(
    title: str,
    remind_at: str,
    description: Optional[str] = None,
    repeat: str = "none",
    tags: Optional[List[str]] = None,
    db=None,
    user_id: int = None,
    session_id: Optional[UUID] = None,
) -> CreateReminderResponse:
    """
    Create a new reminder for the user.

    Use this tool when the user wants to:
    - Set a reminder for a specific time
    - Be notified about something later
    - Schedule a recurring reminder

    Args:
        title: Reminder title
        remind_at: When to remind (YYYY-MM-DD HH:MM or relative like "30分钟后")
        description: Optional description
        repeat: Repeat frequency (none, daily, weekly, monthly, yearly)
        tags: Optional tags
        db: Database session (injected)
        user_id: User ID (injected)
        session_id: Chat session ID (injected)

    Returns:
        CreateReminderResponse with reminder details
    """
    from app.services.reminder_service import ReminderService

    # Parse remind_at
    parsed_remind_at = _parse_remind_at(remind_at)
    if not parsed_remind_at:
        return CreateReminderResponse(
            reminder_id="",
            title=title,
            remind_at="",
            repeat=repeat,
            message=f"无法解析提醒时间：{remind_at}。请使用 YYYY-MM-DD HH:MM 格式。",
        )

    # Parse repeat
    try:
        reminder_repeat = ReminderRepeat(repeat.lower())
    except ValueError:
        reminder_repeat = ReminderRepeat.none

    reminder = ReminderService.create_reminder(
        db=db,
        user_id=user_id,
        title=title,
        remind_at=parsed_remind_at,
        description=description,
        repeat=reminder_repeat,
        tags=tags,
        session_id=session_id,
    )

    remind_at_str = reminder.remind_at.strftime("%Y-%m-%d %H:%M")

    message = f"已设置提醒：{title}，时间：{remind_at_str}"
    if reminder.repeat != ReminderRepeat.none.value:
        repeat_names = {
            "daily": "每天",
            "weekly": "每周",
            "monthly": "每月",
            "yearly": "每年",
        }
        message += f"（{repeat_names.get(reminder.repeat, reminder.repeat)}）"

    return CreateReminderResponse(
        reminder_id=str(reminder.id),
        title=reminder.title,
        remind_at=remind_at_str,
        repeat=reminder.repeat,
        message=message,
    )


@trace_tool_call
def list_reminders(
    include_past: bool = False,
    limit: int = 20,
    db=None,
    user_id: int = None,
) -> ListRemindersResponse:
    """
    List user's reminders.

    Use this tool when the user wants to:
    - See all their reminders
    - Check upcoming reminders
    - Review scheduled notifications

    Args:
        include_past: Include past/triggered reminders
        limit: Maximum number of reminders
        db: Database session (injected)
        user_id: User ID (injected)

    Returns:
        ListRemindersResponse with reminders list
    """
    from app.services.reminder_service import ReminderService

    reminders, total = ReminderService.list_reminders(
        db=db,
        user_id=user_id,
        include_past=include_past,
        limit=limit,
    )

    reminders_data = [reminder.to_dict() for reminder in reminders]
    due_count = sum(1 for reminder in reminders if reminder.is_due)

    if total == 0:
        message = "您没有设置任何提醒。"
    else:
        message = f"共有 {total} 个提醒"
        if due_count > 0:
            message += f"，其中 {due_count} 个已到时间"
        message += "。"

    return ListRemindersResponse(
        reminders=reminders_data,
        total=total,
        due_count=due_count,
        message=message,
    )


@trace_tool_call
def get_due_reminders(
    db=None,
    user_id: int = None,
) -> ListRemindersResponse:
    """
    Get reminders that are due.

    Use this tool when the user wants to:
    - Check if any reminders are due
    - See what needs attention now

    Args:
        db: Database session (injected)
        user_id: User ID (injected)

    Returns:
        ListRemindersResponse with due reminders
    """
    from app.services.reminder_service import ReminderService

    reminders = ReminderService.get_due_reminders(
        db=db,
        user_id=user_id,
    )

    reminders_data = [reminder.to_dict() for reminder in reminders]

    if len(reminders) == 0:
        message = "目前没有到期的提醒。"
    else:
        message = f"您有 {len(reminders)} 个提醒已到时间！"

    return ListRemindersResponse(
        reminders=reminders_data,
        total=len(reminders),
        due_count=len(reminders),
        message=message,
    )


@trace_tool_call
def get_upcoming_reminders(
    within_hours: int = 24,
    db=None,
    user_id: int = None,
) -> ListRemindersResponse:
    """
    Get upcoming reminders within specified hours.

    Use this tool when the user wants to:
    - See what's coming up today
    - Check tomorrow's reminders
    - Plan ahead

    Args:
        within_hours: Hours to look ahead (default 24)
        db: Database session (injected)
        user_id: User ID (injected)

    Returns:
        ListRemindersResponse with upcoming reminders
    """
    from app.services.reminder_service import ReminderService

    reminders = ReminderService.get_upcoming_reminders(
        db=db,
        user_id=user_id,
        within_hours=within_hours,
    )

    reminders_data = [reminder.to_dict() for reminder in reminders]

    if len(reminders) == 0:
        message = f"未来 {within_hours} 小时内没有提醒。"
    else:
        message = f"未来 {within_hours} 小时内有 {len(reminders)} 个提醒。"

    return ListRemindersResponse(
        reminders=reminders_data,
        total=len(reminders),
        due_count=0,
        message=message,
    )


@trace_tool_call
def snooze_reminder(
    reminder_id: str,
    snooze_minutes: int = 15,
    db=None,
    user_id: int = None,
) -> SnoozeReminderResponse:
    """
    Snooze a reminder.

    Use this tool when the user wants to:
    - Delay a reminder
    - Snooze an alert
    - Be reminded again later

    Args:
        reminder_id: ID of the reminder to snooze
        snooze_minutes: Minutes to snooze (default 15)
        db: Database session (injected)
        user_id: User ID (injected)

    Returns:
        SnoozeReminderResponse with snooze details
    """
    from app.services.reminder_service import ReminderService
    from uuid import UUID

    try:
        reminder_uuid = UUID(reminder_id)
    except ValueError:
        return SnoozeReminderResponse(
            reminder_id=reminder_id,
            title="",
            snoozed_until="",
            message="无效的提醒ID。",
        )

    reminder = ReminderService.snooze_reminder(
        db=db,
        reminder_id=reminder_uuid,
        user_id=user_id,
        snooze_minutes=snooze_minutes,
    )

    if not reminder:
        return SnoozeReminderResponse(
            reminder_id=reminder_id,
            title="",
            snoozed_until="",
            message="未找到该提醒。",
        )

    snoozed_until_str = reminder.snoozed_until.strftime("%Y-%m-%d %H:%M")

    return SnoozeReminderResponse(
        reminder_id=str(reminder.id),
        title=reminder.title,
        snoozed_until=snoozed_until_str,
        message=f"提醒已延后至 {snoozed_until_str}。",
    )
