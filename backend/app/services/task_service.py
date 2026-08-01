"""
Task service for Personal Secretary agent.

Provides CRUD operations for tasks/to-do items.
"""

from datetime import datetime
from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.models.task import Task, TaskStatus, TaskPriority


class TaskService:
    """Service for managing tasks."""

    @staticmethod
    def create_task(
        db: Session,
        user_id: int,
        title: str,
        description: Optional[str] = None,
        priority: TaskPriority = TaskPriority.medium,
        due_date: Optional[datetime] = None,
        tags: Optional[List[str]] = None,
        session_id: Optional[UUID] = None,
    ) -> Task:
        """
        Create a new task.

        Args:
            db: Database session
            user_id: Owner user ID
            title: Task title
            description: Optional task description
            priority: Task priority level
            due_date: Optional due date
            tags: Optional list of tags
            session_id: Optional chat session ID

        Returns:
            Created Task object
        """
        task = Task(
            user_id=user_id,
            title=title,
            description=description,
            priority=priority.value if isinstance(priority, TaskPriority) else priority,
            due_date=due_date,
            tags=tags or [],
            session_id=session_id,
        )

        db.add(task)
        db.commit()
        db.refresh(task)

        return task

    @staticmethod
    def get_task(
        db: Session,
        task_id: UUID,
        user_id: int,
    ) -> Optional[Task]:
        """
        Get a task by ID.

        Args:
            db: Database session
            task_id: Task ID
            user_id: Owner user ID

        Returns:
            Task if found and owned by user, None otherwise
        """
        return (
            db.query(Task)
            .filter(
                and_(
                    Task.id == task_id,
                    Task.user_id == user_id,
                    Task.deleted_at.is_(None),
                )
            )
            .first()
        )

    @staticmethod
    def list_tasks(
        db: Session,
        user_id: int,
        status_filter: Optional[TaskStatus] = None,
        priority_filter: Optional[TaskPriority] = None,
        include_completed: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[Task], int]:
        """
        List user's tasks with pagination.

        Args:
            db: Database session
            user_id: Owner user ID
            status_filter: Filter by status
            priority_filter: Filter by priority
            include_completed: Include completed tasks
            limit: Maximum number of tasks
            offset: Number of tasks to skip

        Returns:
            Tuple of (tasks list, total count)
        """
        query = db.query(Task).filter(
            and_(
                Task.user_id == user_id,
                Task.deleted_at.is_(None),
            )
        )

        if status_filter:
            status_val = (
                status_filter.value
                if isinstance(status_filter, TaskStatus)
                else status_filter
            )
            query = query.filter(Task.status == status_val)
        elif not include_completed:
            query = query.filter(Task.status != TaskStatus.completed.value)

        if priority_filter:
            priority_val = (
                priority_filter.value
                if isinstance(priority_filter, TaskPriority)
                else priority_filter
            )
            query = query.filter(Task.priority == priority_val)

        # Count before pagination
        total = query.count()

        # Order by priority (urgent first), then by due date
        priority_order = {
            TaskPriority.urgent.value: 0,
            TaskPriority.high.value: 1,
            TaskPriority.medium.value: 2,
            TaskPriority.low.value: 3,
        }

        # Order by due date (nulls last), then created_at
        query = query.order_by(
            Task.due_date.asc().nullslast(),
            Task.created_at.desc(),
        )

        tasks = query.offset(offset).limit(limit).all()

        return tasks, total

    @staticmethod
    def get_due_tasks(
        db: Session,
        user_id: int,
        before: Optional[datetime] = None,
    ) -> List[Task]:
        """
        Get tasks that are due.

        Args:
            db: Database session
            user_id: Owner user ID
            before: Get tasks due before this time (default: now)

        Returns:
            List of due tasks
        """
        if before is None:
            before = datetime.utcnow()

        return (
            db.query(Task)
            .filter(
                and_(
                    Task.user_id == user_id,
                    Task.deleted_at.is_(None),
                    Task.status.in_(
                        [TaskStatus.pending.value, TaskStatus.in_progress.value]
                    ),
                    Task.due_date.isnot(None),
                    Task.due_date <= before,
                )
            )
            .order_by(Task.due_date.asc())
            .all()
        )

    @staticmethod
    def complete_task(
        db: Session,
        task_id: UUID,
        user_id: int,
    ) -> Optional[Task]:
        """
        Mark a task as completed.

        Returns:
            Updated Task if found, None otherwise
        """
        task = TaskService.get_task(db, task_id, user_id)
        if not task:
            return None

        task.complete()
        db.commit()
        db.refresh(task)

        return task

    @staticmethod
    def update_status(
        db: Session,
        task_id: UUID,
        user_id: int,
        status: TaskStatus,
    ) -> Optional[Task]:
        """Update task status."""
        task = TaskService.get_task(db, task_id, user_id)
        if not task:
            return None

        task.status = status.value if isinstance(status, TaskStatus) else status
        if status == TaskStatus.completed:
            task.completed_at = datetime.utcnow()

        db.commit()
        db.refresh(task)

        return task

    @staticmethod
    def update_task(
        db: Session,
        task_id: UUID,
        user_id: int,
        title: Optional[str] = None,
        description: Optional[str] = None,
        priority: Optional[TaskPriority] = None,
        due_date: Optional[datetime] = None,
        tags: Optional[List[str]] = None,
    ) -> Optional[Task]:
        """
        Update a task.

        Returns:
            Updated Task if found, None otherwise
        """
        task = TaskService.get_task(db, task_id, user_id)
        if not task:
            return None

        if title is not None:
            task.title = title
        if description is not None:
            task.description = description
        if priority is not None:
            task.priority = (
                priority.value if isinstance(priority, TaskPriority) else priority
            )
        if due_date is not None:
            task.due_date = due_date
        if tags is not None:
            task.tags = tags

        db.commit()
        db.refresh(task)

        return task

    @staticmethod
    def delete_task(
        db: Session,
        task_id: UUID,
        user_id: int,
    ) -> bool:
        """
        Soft delete a task.

        Returns:
            True if deleted, False if not found
        """
        task = TaskService.get_task(db, task_id, user_id)
        if not task:
            return False

        task.soft_delete()
        db.commit()

        return True

    @staticmethod
    def get_statistics(
        db: Session,
        user_id: int,
    ) -> dict:
        """
        Get task statistics for a user.

        Returns:
            Dictionary with task counts by status and priority
        """
        tasks = (
            db.query(Task)
            .filter(
                and_(
                    Task.user_id == user_id,
                    Task.deleted_at.is_(None),
                )
            )
            .all()
        )

        stats = {
            "total": len(tasks),
            "by_status": {
                "pending": 0,
                "in_progress": 0,
                "completed": 0,
                "cancelled": 0,
            },
            "by_priority": {
                "low": 0,
                "medium": 0,
                "high": 0,
                "urgent": 0,
            },
            "overdue": 0,
        }

        for task in tasks:
            if task.status in stats["by_status"]:
                stats["by_status"][task.status] += 1
            if task.priority in stats["by_priority"]:
                stats["by_priority"][task.priority] += 1
            if task.is_overdue:
                stats["overdue"] += 1

        return stats
