"""
Task management tools for Personal Secretary agent.

Allows the agent to create and manage tasks for the user.
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.task import TaskPriority, TaskStatus
from app.services.secretary_agent.tracing import trace_tool_call


class CreateTaskInput(BaseModel):
    """Input schema for create_task tool."""

    title: str = Field(..., description="Task title")
    description: Optional[str] = Field(None, description="Task description")
    priority: str = Field("medium", description="Priority: low, medium, high, urgent")
    due_date: Optional[str] = Field(
        None, description="Due date in ISO format (YYYY-MM-DD or YYYY-MM-DD HH:MM)"
    )
    tags: Optional[List[str]] = Field(None, description="Optional tags")


class CreateTaskResponse(BaseModel):
    """Response schema for create_task tool."""

    task_id: str
    title: str
    priority: str
    due_date: Optional[str]
    message: str


class ListTasksInput(BaseModel):
    """Input schema for list_tasks tool."""

    include_completed: bool = Field(False, description="Include completed tasks")
    priority: Optional[str] = Field(None, description="Filter by priority")
    limit: int = Field(20, description="Maximum number of tasks", ge=1, le=100)


class ListTasksResponse(BaseModel):
    """Response schema for list_tasks tool."""

    tasks: List[dict]
    total: int
    overdue_count: int
    message: str


class CompleteTaskInput(BaseModel):
    """Input schema for complete_task tool."""

    task_id: str = Field(..., description="ID of the task to complete")


class CompleteTaskResponse(BaseModel):
    """Response schema for complete_task tool."""

    task_id: str
    title: str
    completed_at: str
    message: str


def _parse_due_date(due_date_str: Optional[str]) -> Optional[datetime]:
    """Parse due date string to datetime."""
    if not due_date_str:
        return None

    formats = [
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
        "%Y/%m/%d %H:%M",
        "%Y/%m/%d",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(due_date_str, fmt)
        except ValueError:
            continue

    return None


@trace_tool_call
def create_task(
    title: str,
    description: Optional[str] = None,
    priority: str = "medium",
    due_date: Optional[str] = None,
    tags: Optional[List[str]] = None,
    db=None,
    user_id: int = None,
    session_id: Optional[UUID] = None,
) -> CreateTaskResponse:
    """
    Create a new task for the user.

    Use this tool when the user wants to:
    - Add a to-do item
    - Create a task with a deadline
    - Set a reminder to do something

    Args:
        title: Task title
        description: Optional detailed description
        priority: Priority level (low, medium, high, urgent)
        due_date: Due date in YYYY-MM-DD or YYYY-MM-DD HH:MM format
        tags: Optional tags for categorization
        db: Database session (injected)
        user_id: User ID (injected)
        session_id: Chat session ID (injected)

    Returns:
        CreateTaskResponse with task details
    """
    from app.services.task_service import TaskService

    # Parse priority
    try:
        task_priority = TaskPriority(priority.lower())
    except ValueError:
        task_priority = TaskPriority.medium

    # Parse due date
    parsed_due_date = _parse_due_date(due_date)

    task = TaskService.create_task(
        db=db,
        user_id=user_id,
        title=title,
        description=description,
        priority=task_priority,
        due_date=parsed_due_date,
        tags=tags,
        session_id=session_id,
    )

    due_str = task.due_date.strftime("%Y-%m-%d %H:%M") if task.due_date else None

    message = f"已创建任务：{title}"
    if due_str:
        message += f"，截止日期：{due_str}"

    return CreateTaskResponse(
        task_id=str(task.id),
        title=task.title,
        priority=task.priority,
        due_date=due_str,
        message=message,
    )


@trace_tool_call
def list_tasks(
    include_completed: bool = False,
    priority: Optional[str] = None,
    limit: int = 20,
    db=None,
    user_id: int = None,
) -> ListTasksResponse:
    """
    List user's tasks.

    Use this tool when the user wants to:
    - See their to-do list
    - Check pending tasks
    - Review overdue tasks

    Args:
        include_completed: Include completed tasks
        priority: Filter by priority (optional)
        limit: Maximum number of tasks
        db: Database session (injected)
        user_id: User ID (injected)

    Returns:
        ListTasksResponse with tasks list
    """
    from app.services.task_service import TaskService

    # Parse priority filter
    priority_filter = None
    if priority:
        try:
            priority_filter = TaskPriority(priority.lower())
        except ValueError:
            pass

    tasks, total = TaskService.list_tasks(
        db=db,
        user_id=user_id,
        include_completed=include_completed,
        priority_filter=priority_filter,
        limit=limit,
    )

    tasks_data = [task.to_dict() for task in tasks]
    overdue_count = sum(1 for task in tasks if task.is_overdue)

    if total == 0:
        message = "您没有待办任务。"
    else:
        message = f"共有 {total} 个任务"
        if overdue_count > 0:
            message += f"，其中 {overdue_count} 个已过期"
        message += "。"

    return ListTasksResponse(
        tasks=tasks_data,
        total=total,
        overdue_count=overdue_count,
        message=message,
    )


@trace_tool_call
def complete_task(
    task_id: str,
    db=None,
    user_id: int = None,
) -> CompleteTaskResponse:
    """
    Mark a task as completed.

    Use this tool when the user wants to:
    - Mark a task as done
    - Complete a to-do item
    - Check off a task

    Args:
        task_id: ID of the task to complete
        db: Database session (injected)
        user_id: User ID (injected)

    Returns:
        CompleteTaskResponse with completion details
    """
    from app.services.task_service import TaskService
    from uuid import UUID

    try:
        task_uuid = UUID(task_id)
    except ValueError:
        return CompleteTaskResponse(
            task_id=task_id,
            title="",
            completed_at="",
            message="无效的任务ID。",
        )

    task = TaskService.complete_task(
        db=db,
        task_id=task_uuid,
        user_id=user_id,
    )

    if not task:
        return CompleteTaskResponse(
            task_id=task_id,
            title="",
            completed_at="",
            message="未找到该任务。",
        )

    return CompleteTaskResponse(
        task_id=str(task.id),
        title=task.title,
        completed_at=task.completed_at.isoformat() if task.completed_at else "",
        message=f"任务 '{task.title}' 已完成！",
    )


@trace_tool_call
def get_overdue_tasks(
    db=None,
    user_id: int = None,
) -> ListTasksResponse:
    """
    Get all overdue tasks.

    Use this tool when the user wants to:
    - See what tasks are overdue
    - Check missed deadlines

    Args:
        db: Database session (injected)
        user_id: User ID (injected)

    Returns:
        ListTasksResponse with overdue tasks
    """
    from app.services.task_service import TaskService

    tasks = TaskService.get_due_tasks(
        db=db,
        user_id=user_id,
    )

    tasks_data = [task.to_dict() for task in tasks]

    if len(tasks) == 0:
        message = "太棒了！您没有过期的任务。"
    else:
        message = f"您有 {len(tasks)} 个过期的任务需要处理。"

    return ListTasksResponse(
        tasks=tasks_data,
        total=len(tasks),
        overdue_count=len(tasks),
        message=message,
    )
