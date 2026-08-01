"""
Reminder service for Personal Secretary agent.

Provides CRUD operations for reminders.
"""

from datetime import datetime, timedelta
from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.models.reminder import Reminder, ReminderStatus, ReminderRepeat


class ReminderService:
    """Service for managing reminders."""

    @staticmethod
    def create_reminder(
        db: Session,
        user_id: int,
        title: str,
        remind_at: datetime,
        description: Optional[str] = None,
        repeat: ReminderRepeat = ReminderRepeat.none,
        tags: Optional[List[str]] = None,
        session_id: Optional[UUID] = None,
    ) -> Reminder:
        """
        Create a new reminder.

        Args:
            db: Database session
            user_id: Owner user ID
            title: Reminder title
            remind_at: When to trigger the reminder
            description: Optional description
            repeat: Repeat frequency
            tags: Optional list of tags
            session_id: Optional chat session ID

        Returns:
            Created Reminder object
        """
        reminder = Reminder(
            user_id=user_id,
            title=title,
            remind_at=remind_at,
            description=description,
            repeat=repeat.value if isinstance(repeat, ReminderRepeat) else repeat,
            tags=tags or [],
            session_id=session_id,
        )

        db.add(reminder)
        db.commit()
        db.refresh(reminder)

        return reminder

    @staticmethod
    def get_reminder(
        db: Session,
        reminder_id: UUID,
        user_id: int,
    ) -> Optional[Reminder]:
        """
        Get a reminder by ID.

        Args:
            db: Database session
            reminder_id: Reminder ID
            user_id: Owner user ID

        Returns:
            Reminder if found and owned by user, None otherwise
        """
        return (
            db.query(Reminder)
            .filter(
                and_(
                    Reminder.id == reminder_id,
                    Reminder.user_id == user_id,
                    Reminder.deleted_at.is_(None),
                )
            )
            .first()
        )

    @staticmethod
    def list_reminders(
        db: Session,
        user_id: int,
        status_filter: Optional[ReminderStatus] = None,
        include_past: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[Reminder], int]:
        """
        List user's reminders with pagination.

        Args:
            db: Database session
            user_id: Owner user ID
            status_filter: Filter by status
            include_past: Include past/triggered reminders
            limit: Maximum number of reminders
            offset: Number of reminders to skip

        Returns:
            Tuple of (reminders list, total count)
        """
        query = db.query(Reminder).filter(
            and_(
                Reminder.user_id == user_id,
                Reminder.deleted_at.is_(None),
            )
        )

        if status_filter:
            status_val = (
                status_filter.value
                if isinstance(status_filter, ReminderStatus)
                else status_filter
            )
            query = query.filter(Reminder.status == status_val)
        elif not include_past:
            # Only show pending or snoozed reminders
            query = query.filter(
                Reminder.status.in_(
                    [
                        ReminderStatus.pending.value,
                        ReminderStatus.snoozed.value,
                    ]
                )
            )

        # Count before pagination
        total = query.count()

        # Order by remind_at
        query = query.order_by(Reminder.remind_at.asc())

        reminders = query.offset(offset).limit(limit).all()

        return reminders, total

    @staticmethod
    def get_due_reminders(
        db: Session,
        user_id: int,
    ) -> List[Reminder]:
        """
        Get reminders that are due to trigger.

        Args:
            db: Database session
            user_id: Owner user ID

        Returns:
            List of due reminders
        """
        now = datetime.utcnow()

        return (
            db.query(Reminder)
            .filter(
                and_(
                    Reminder.user_id == user_id,
                    Reminder.deleted_at.is_(None),
                    or_(
                        # Pending and due
                        and_(
                            Reminder.status == ReminderStatus.pending.value,
                            Reminder.remind_at <= now,
                        ),
                        # Snoozed and snooze time passed
                        and_(
                            Reminder.status == ReminderStatus.snoozed.value,
                            Reminder.snoozed_until <= now,
                        ),
                    ),
                )
            )
            .order_by(Reminder.remind_at.asc())
            .all()
        )

    @staticmethod
    def get_upcoming_reminders(
        db: Session,
        user_id: int,
        within_hours: int = 24,
    ) -> List[Reminder]:
        """
        Get reminders coming up within specified hours.

        Args:
            db: Database session
            user_id: Owner user ID
            within_hours: Hours to look ahead

        Returns:
            List of upcoming reminders
        """
        now = datetime.utcnow()
        cutoff = now + timedelta(hours=within_hours)

        return (
            db.query(Reminder)
            .filter(
                and_(
                    Reminder.user_id == user_id,
                    Reminder.deleted_at.is_(None),
                    Reminder.status == ReminderStatus.pending.value,
                    Reminder.remind_at > now,
                    Reminder.remind_at <= cutoff,
                )
            )
            .order_by(Reminder.remind_at.asc())
            .all()
        )

    @staticmethod
    def trigger_reminder(
        db: Session,
        reminder_id: UUID,
        user_id: int,
    ) -> Optional[Reminder]:
        """
        Mark a reminder as triggered.

        Returns:
            Updated Reminder if found, None otherwise
        """
        reminder = ReminderService.get_reminder(db, reminder_id, user_id)
        if not reminder:
            return None

        reminder.trigger()
        db.commit()
        db.refresh(reminder)

        return reminder

    @staticmethod
    def snooze_reminder(
        db: Session,
        reminder_id: UUID,
        user_id: int,
        snooze_minutes: int = 15,
    ) -> Optional[Reminder]:
        """
        Snooze a reminder.

        Args:
            db: Database session
            reminder_id: Reminder ID
            user_id: Owner user ID
            snooze_minutes: Minutes to snooze

        Returns:
            Updated Reminder if found, None otherwise
        """
        reminder = ReminderService.get_reminder(db, reminder_id, user_id)
        if not reminder:
            return None

        snooze_until = datetime.utcnow() + timedelta(minutes=snooze_minutes)
        reminder.snooze(snooze_until)

        db.commit()
        db.refresh(reminder)

        return reminder

    @staticmethod
    def dismiss_reminder(
        db: Session,
        reminder_id: UUID,
        user_id: int,
    ) -> Optional[Reminder]:
        """
        Dismiss a reminder.

        Returns:
            Updated Reminder if found, None otherwise
        """
        reminder = ReminderService.get_reminder(db, reminder_id, user_id)
        if not reminder:
            return None

        reminder.dismiss()
        db.commit()
        db.refresh(reminder)

        return reminder

    @staticmethod
    def update_reminder(
        db: Session,
        reminder_id: UUID,
        user_id: int,
        title: Optional[str] = None,
        description: Optional[str] = None,
        remind_at: Optional[datetime] = None,
        repeat: Optional[ReminderRepeat] = None,
        tags: Optional[List[str]] = None,
    ) -> Optional[Reminder]:
        """
        Update a reminder.

        Returns:
            Updated Reminder if found, None otherwise
        """
        reminder = ReminderService.get_reminder(db, reminder_id, user_id)
        if not reminder:
            return None

        if title is not None:
            reminder.title = title
        if description is not None:
            reminder.description = description
        if remind_at is not None:
            reminder.remind_at = remind_at
            # Reset status if rescheduled
            if reminder.status in [
                ReminderStatus.triggered.value,
                ReminderStatus.dismissed.value,
            ]:
                reminder.status = ReminderStatus.pending.value
        if repeat is not None:
            reminder.repeat = (
                repeat.value if isinstance(repeat, ReminderRepeat) else repeat
            )
        if tags is not None:
            reminder.tags = tags

        db.commit()
        db.refresh(reminder)

        return reminder

    @staticmethod
    def delete_reminder(
        db: Session,
        reminder_id: UUID,
        user_id: int,
    ) -> bool:
        """
        Soft delete a reminder.

        Returns:
            True if deleted, False if not found
        """
        reminder = ReminderService.get_reminder(db, reminder_id, user_id)
        if not reminder:
            return False

        reminder.soft_delete()
        db.commit()

        return True
