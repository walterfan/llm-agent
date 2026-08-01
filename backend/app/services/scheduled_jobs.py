"""
Scheduled Job Functions for Lazy Rabbit Agent.

Each function is a self-contained job that:
  1. Creates its own DB session (jobs run outside request context)
  2. Performs the business logic
  3. Optionally triggers AI agent for intelligent processing
  4. Cleans up resources

Jobs are registered in scheduler.py and executed by APScheduler.

Design:
  - All jobs are async (APScheduler AsyncIOScheduler supports this)
  - Each job manages its own DB session lifecycle
  - Errors are caught and logged (APScheduler also catches them)
  - Jobs are idempotent — safe to re-run
"""

import logging
from datetime import datetime, timedelta
from typing import Any

from app.db.base import SessionLocal
from app.models.reminder import Reminder, ReminderRepeat, ReminderStatus
from app.models.task import Task, TaskStatus
from app.models.user import User

logger = logging.getLogger("scheduled_jobs")


# ============================================================================
# Job 1: Check Due Reminders (every 5 minutes)
# ============================================================================


async def job_check_due_reminders() -> dict[str, Any]:
    """
    Check all users for due reminders and trigger notifications.

    For each due reminder:
      - Mark it as triggered
      - If it has a repeat schedule, create the next occurrence
      - Log the notification (future: push via WebSocket / email / webhook)

    Returns:
        Summary dict with counts.
    """
    logger.info("🔔 [Job] Checking due reminders...")
    db = SessionLocal()
    total_triggered = 0
    total_repeated = 0

    try:
        now = datetime.utcnow()

        # Find all pending reminders that are due
        due_reminders = (
            db.query(Reminder)
            .filter(
                Reminder.deleted_at.is_(None),
                Reminder.status.in_(
                    [
                        ReminderStatus.pending.value,
                        ReminderStatus.snoozed.value,
                    ]
                ),
                Reminder.remind_at <= now,
            )
            .all()
        )

        for reminder in due_reminders:
            # Also check snoozed_until for snoozed reminders
            if (
                reminder.status == ReminderStatus.snoozed.value
                and reminder.snoozed_until
                and reminder.snoozed_until > now
            ):
                continue

            # Mark as triggered
            reminder.status = ReminderStatus.triggered.value
            total_triggered += 1

            logger.info(
                f"  🔔 Triggered: [{reminder.user_id}] {reminder.title} "
                f"(due: {reminder.remind_at})"
            )

            # Handle repeating reminders — create next occurrence
            if reminder.repeat and reminder.repeat != ReminderRepeat.none.value:
                next_time = _calculate_next_occurrence(
                    reminder.remind_at, reminder.repeat
                )
                if next_time:
                    new_reminder = Reminder(
                        user_id=reminder.user_id,
                        title=reminder.title,
                        description=reminder.description,
                        remind_at=next_time,
                        repeat=reminder.repeat,
                        tags=reminder.tags,
                        session_id=reminder.session_id,
                    )
                    db.add(new_reminder)
                    total_repeated += 1
                    logger.info(f"  🔁 Created next occurrence: {next_time}")

            # TODO: Send notification via WebSocket / push / email
            # await notify_user(reminder.user_id, {
            #     "type": "reminder",
            #     "title": reminder.title,
            #     "description": reminder.description,
            # })

        db.commit()

    except Exception as e:
        logger.error(f"❌ [Job] check_due_reminders failed: {e}", exc_info=True)
        db.rollback()
    finally:
        db.close()

    result = {
        "triggered": total_triggered,
        "repeated": total_repeated,
        "checked_at": datetime.utcnow().isoformat(),
    }
    logger.info(
        f"🔔 [Job] Reminders: {total_triggered} triggered, {total_repeated} repeated"
    )
    return result


# ============================================================================
# Job 2: Check Overdue Tasks (every 30 minutes)
# ============================================================================


async def job_check_overdue_tasks() -> dict[str, Any]:
    """
    Check for overdue tasks and log warnings.

    Future enhancement: trigger AI agent to suggest rescheduling
    or send notifications to users.

    Returns:
        Summary dict with counts.
    """
    logger.info("📋 [Job] Checking overdue tasks...")
    db = SessionLocal()
    overdue_count = 0
    users_affected = set()

    try:
        now = datetime.utcnow()

        overdue_tasks = (
            db.query(Task)
            .filter(
                Task.deleted_at.is_(None),
                Task.status.in_(
                    [
                        TaskStatus.pending.value,
                        TaskStatus.in_progress.value,
                    ]
                ),
                Task.due_date.isnot(None),
                Task.due_date < now,
            )
            .all()
        )

        for task in overdue_tasks:
            overdue_count += 1
            users_affected.add(task.user_id)
            logger.info(
                f"  ⚠️ Overdue: [{task.user_id}] {task.title} " f"(due: {task.due_date})"
            )

        # TODO: For each affected user, optionally trigger Secretary Agent
        # to generate a summary or suggest rescheduling:
        #
        # for user_id in users_affected:
        #     agent = SecretaryAgent(user_id=user_id, db=db)
        #     await agent.chat(
        #         user_message="请检查我的逾期任务并给出建议",
        #         chat_history=[],
        #     )

    except Exception as e:
        logger.error(f"❌ [Job] check_overdue_tasks failed: {e}", exc_info=True)
    finally:
        db.close()

    result = {
        "overdue_count": overdue_count,
        "users_affected": len(users_affected),
        "checked_at": datetime.utcnow().isoformat(),
    }
    logger.info(
        f"📋 [Job] Tasks: {overdue_count} overdue, {len(users_affected)} users affected"
    )
    return result


# ============================================================================
# Job 3: Daily Summary (every day at 08:00)
# ============================================================================


async def job_daily_summary() -> dict[str, Any]:
    """
    Generate a daily summary for each active user by invoking the
    Secretary Agent.

    The agent will:
      - Summarize today's tasks and reminders
      - Highlight overdue items
      - Suggest priorities for the day

    Returns:
        Summary dict with counts.
    """
    logger.info("📰 [Job] Generating daily summaries...")
    db = SessionLocal()
    users_processed = 0
    errors = 0

    try:
        # Get all active users
        active_users = db.query(User).filter(User.is_active == True).all()  # noqa: E712

        for user in active_users:
            try:
                # Gather user's data for summary
                from app.services.reminder_service import ReminderService
                from app.services.task_service import TaskService

                # Get today's reminders
                upcoming = ReminderService.get_upcoming_reminders(
                    db, user.id, within_hours=24
                )
                due = ReminderService.get_due_reminders(db, user.id)

                # Get pending/overdue tasks
                due_tasks = TaskService.get_due_tasks(db, user.id)
                task_stats = TaskService.get_statistics(db, user.id)

                summary_parts = []
                if due:
                    summary_parts.append(f"🔔 {len(due)} reminder(s) due now")
                if upcoming:
                    summary_parts.append(
                        f"⏰ {len(upcoming)} reminder(s) coming up today"
                    )
                if due_tasks:
                    summary_parts.append(f"⚠️ {len(due_tasks)} overdue task(s)")
                summary_parts.append(
                    f"📋 {task_stats['by_status']['pending']} pending, "
                    f"{task_stats['by_status']['in_progress']} in progress"
                )

                summary = " | ".join(summary_parts)
                logger.info(
                    f"  📰 [{user.id}] {user.full_name or user.email}: {summary}"
                )

                # TODO: Trigger Secretary Agent to generate a natural-language
                # daily briefing and send via preferred channel:
                #
                # agent = SecretaryAgent(user_id=user.id, db=db)
                # briefing = await agent.chat(
                #     user_message=(
                #         f"请为我生成今日简报。"
                #         f"今日提醒: {len(upcoming)}个, 逾期提醒: {len(due)}个, "
                #         f"逾期任务: {len(due_tasks)}个, "
                #         f"待办: {task_stats['by_status']['pending']}个"
                #     ),
                #     chat_history=[],
                # )
                # await send_daily_briefing(user, briefing)

                users_processed += 1

            except Exception as e:
                errors += 1
                logger.error(f"  ❌ Failed for user {user.id}: {e}", exc_info=True)

    except Exception as e:
        logger.error(f"❌ [Job] daily_summary failed: {e}", exc_info=True)
    finally:
        db.close()

    result = {
        "users_processed": users_processed,
        "errors": errors,
        "generated_at": datetime.utcnow().isoformat(),
    }
    logger.info(f"📰 [Job] Daily summary: {users_processed} users, {errors} errors")
    return result


# ============================================================================
# Job 4: Send Scheduled Emails (every hour)
# ============================================================================


async def job_send_scheduled_emails() -> dict[str, Any]:
    """
    Send scheduled recommendation emails for the current hour.

    Delegates to the existing ScheduledEmailService.

    Returns:
        Summary dict with counts.
    """
    logger.info("📧 [Job] Sending scheduled emails...")
    db = SessionLocal()

    try:
        from app.services.scheduled_email_service import ScheduledEmailService

        current_hour = datetime.now().hour
        service = ScheduledEmailService(db)
        result = await service.send_emails_for_hour(current_hour)

        logger.info(
            f"📧 [Job] Emails: {result['success_count']}/{result['processed_count']} sent"
        )
        return {
            "hour": current_hour,
            "processed": result["processed_count"],
            "success": result["success_count"],
            "failed": result["failed_count"],
            "sent_at": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"❌ [Job] send_scheduled_emails failed: {e}", exc_info=True)
        return {
            "error": str(e),
            "sent_at": datetime.utcnow().isoformat(),
        }
    finally:
        db.close()


# ============================================================================
# Job 5: Scheduled Database Backup (daily at 02:00)
# ============================================================================


async def job_scheduled_backup() -> dict[str, Any]:
    """
    Perform automatic database backup (JSON export + binary copy).

    Creates timestamped backups and rotates old ones based on
    retention policy (default: keep last 30).

    Returns:
        Summary dict with backup results.
    """
    logger.info("💾 [Job] Starting scheduled database backup...")

    try:
        from app.services.backup_service import backup_service

        result = backup_service.scheduled_backup()
        logger.info(f"💾 [Job] Backup complete: {result}")
        return result

    except Exception as e:
        logger.error(f"❌ [Job] scheduled_backup failed: {e}", exc_info=True)
        return {
            "error": str(e),
            "backup_at": datetime.utcnow().isoformat(),
        }


# ============================================================================
# Helper functions
# ============================================================================


def _calculate_next_occurrence(current_time: datetime, repeat: str) -> datetime | None:
    """
    Calculate the next occurrence for a repeating reminder.

    Args:
        current_time: The current reminder time.
        repeat: Repeat frequency string.

    Returns:
        Next occurrence datetime, or None if not repeating.
    """
    repeat_deltas = {
        ReminderRepeat.daily.value: timedelta(days=1),
        ReminderRepeat.weekly.value: timedelta(weeks=1),
        ReminderRepeat.monthly.value: timedelta(days=30),  # Approximate
        ReminderRepeat.yearly.value: timedelta(days=365),  # Approximate
    }

    delta = repeat_deltas.get(repeat)
    if delta:
        return current_time + delta
    return None
