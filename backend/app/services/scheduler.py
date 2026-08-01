"""
APScheduler-based Job Scheduler for Lazy Rabbit Agent.

Provides an in-process async scheduler that triggers AI agent tasks
on configurable cron/interval schedules. Integrates with FastAPI's
asyncio event loop.

Architecture:
    ┌──────────────────────────────────────────────┐
    │  AsyncIOScheduler                            │
    │  ┌────────────┐ ┌────────────┐ ┌──────────┐ │
    │  │ check      │ │ daily      │ │ send     │ │
    │  │ reminders  │ │ learning   │ │ emails   │ │
    │  │ (5 min)    │ │ (8:00 AM)  │ │ (hourly) │ │
    │  └─────┬──────┘ └─────┬──────┘ └────┬─────┘ │
    │        │              │             │        │
    │        ▼              ▼             ▼        │
    │  ┌──────────────────────────────────────┐    │
    │  │  scheduled_jobs.py (job functions)   │    │
    │  └──────────────────────────────────────┘    │
    └──────────────────────────────────────────────┘

Usage:
    from app.services.scheduler import scheduler_service

    # In FastAPI startup:
    scheduler_service.start()

    # In FastAPI shutdown:
    scheduler_service.shutdown()

    # Dynamic job management via API:
    scheduler_service.add_job(...)
    scheduler_service.remove_job(...)
    scheduler_service.list_jobs()
"""

import logging
from datetime import datetime
from typing import Any, Callable, Optional

from apscheduler.events import (
    EVENT_JOB_ERROR,
    EVENT_JOB_EXECUTED,
    EVENT_JOB_MISSED,
    JobEvent,
    JobExecutionEvent,
)
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger("scheduler")


class SchedulerService:
    """
    Manages the APScheduler lifecycle and provides a clean API
    for adding/removing/listing scheduled jobs.
    """

    def __init__(self) -> None:
        self._scheduler: Optional[AsyncIOScheduler] = None
        self._started = False
        self._job_history: list[dict[str, Any]] = []  # Recent execution log

    @property
    def is_running(self) -> bool:
        return self._started and self._scheduler is not None and self._scheduler.running

    def start(self, timezone: str = "Asia/Shanghai") -> None:
        """
        Initialize and start the scheduler with all registered jobs.

        Args:
            timezone: IANA timezone for cron triggers.
        """
        if self._started:
            logger.warning("Scheduler already started, skipping")
            return

        self._scheduler = AsyncIOScheduler(
            jobstores={"default": MemoryJobStore()},
            timezone=timezone,
        )

        # Listen for job events (success, error, missed)
        self._scheduler.add_listener(self._on_job_executed, EVENT_JOB_EXECUTED)
        self._scheduler.add_listener(self._on_job_error, EVENT_JOB_ERROR)
        self._scheduler.add_listener(self._on_job_missed, EVENT_JOB_MISSED)

        # Register default jobs
        self._register_default_jobs()

        self._scheduler.start()
        self._started = True
        logger.info(f"⏰ Scheduler started (timezone={timezone})")

    def shutdown(self) -> None:
        """Gracefully shut down the scheduler."""
        if self._scheduler and self._started:
            self._scheduler.shutdown(wait=False)
            self._started = False
            logger.info("⏰ Scheduler shut down")

    # ========================================================================
    # Job registration
    # ========================================================================

    def _register_default_jobs(self) -> None:
        """Register all built-in scheduled jobs."""
        from app.services.scheduled_jobs import (
            job_check_due_reminders,
            job_check_overdue_tasks,
            job_daily_summary,
            job_scheduled_backup,
            job_send_scheduled_emails,
        )

        # 1. Check due reminders — every 5 minutes
        self._scheduler.add_job(
            job_check_due_reminders,
            IntervalTrigger(minutes=5),
            id="check_due_reminders",
            name="Check due reminders and notify users",
            replace_existing=True,
            max_instances=1,
        )

        # 2. Check overdue tasks — every 30 minutes
        self._scheduler.add_job(
            job_check_overdue_tasks,
            IntervalTrigger(minutes=30),
            id="check_overdue_tasks",
            name="Check overdue tasks and alert users",
            replace_existing=True,
            max_instances=1,
        )

        # 3. Daily summary — every day at 08:00
        self._scheduler.add_job(
            job_daily_summary,
            CronTrigger(hour=8, minute=0),
            id="daily_summary",
            name="Generate daily summary for all users",
            replace_existing=True,
            max_instances=1,
        )

        # 4. Send scheduled emails — every hour at :00
        self._scheduler.add_job(
            job_send_scheduled_emails,
            CronTrigger(minute=0),
            id="send_scheduled_emails",
            name="Send scheduled recommendation emails",
            replace_existing=True,
            max_instances=1,
        )

        # 5. Scheduled database backup — every day at 02:00
        self._scheduler.add_job(
            job_scheduled_backup,
            CronTrigger(hour=2, minute=0),
            id="scheduled_backup",
            name="Automatic database backup (JSON + binary)",
            replace_existing=True,
            max_instances=1,
        )

        logger.info(f"📋 Registered {len(self._scheduler.get_jobs())} default jobs")

    # ========================================================================
    # Dynamic job management
    # ========================================================================

    def add_job(
        self,
        job_id: str,
        func: Callable,
        trigger_type: str = "cron",
        name: Optional[str] = None,
        **trigger_kwargs: Any,
    ) -> dict[str, Any]:
        """
        Dynamically add a new scheduled job.

        Args:
            job_id: Unique job identifier.
            func: Async or sync callable to execute.
            trigger_type: "cron" or "interval".
            name: Human-readable job name.
            **trigger_kwargs: Trigger-specific arguments
                For cron: hour, minute, day_of_week, etc.
                For interval: seconds, minutes, hours, etc.

        Returns:
            Job info dict.

        Raises:
            RuntimeError: If scheduler is not running.
            ValueError: If trigger_type is invalid.
        """
        if not self.is_running:
            raise RuntimeError("Scheduler is not running")

        if trigger_type == "cron":
            trigger = CronTrigger(**trigger_kwargs)
        elif trigger_type == "interval":
            trigger = IntervalTrigger(**trigger_kwargs)
        else:
            raise ValueError(f"Unknown trigger_type: {trigger_type}")

        job = self._scheduler.add_job(
            func,
            trigger,
            id=job_id,
            name=name or job_id,
            replace_existing=True,
            max_instances=1,
        )

        logger.info(f"➕ Added job: {job_id} ({trigger_type}: {trigger_kwargs})")
        return self._job_to_dict(job)

    def remove_job(self, job_id: str) -> bool:
        """
        Remove a scheduled job by ID.

        Returns:
            True if removed, False if not found.
        """
        if not self.is_running:
            return False

        try:
            self._scheduler.remove_job(job_id)
            logger.info(f"➖ Removed job: {job_id}")
            return True
        except Exception:
            logger.warning(f"Job not found: {job_id}")
            return False

    def pause_job(self, job_id: str) -> bool:
        """Pause a scheduled job."""
        if not self.is_running:
            return False
        try:
            self._scheduler.pause_job(job_id)
            logger.info(f"⏸️ Paused job: {job_id}")
            return True
        except Exception:
            return False

    def resume_job(self, job_id: str) -> bool:
        """Resume a paused job."""
        if not self.is_running:
            return False
        try:
            self._scheduler.resume_job(job_id)
            logger.info(f"▶️ Resumed job: {job_id}")
            return True
        except Exception:
            return False

    def trigger_job(self, job_id: str) -> bool:
        """
        Immediately trigger a job (run it now, regardless of schedule).

        Returns:
            True if triggered, False if not found.
        """
        if not self.is_running:
            return False
        try:
            job = self._scheduler.get_job(job_id)
            if job:
                job.modify(next_run_time=datetime.now())
                logger.info(f"🔥 Triggered job immediately: {job_id}")
                return True
            return False
        except Exception:
            return False

    def list_jobs(self) -> list[dict[str, Any]]:
        """List all registered jobs with their next run times."""
        if not self.is_running:
            return []

        return [self._job_to_dict(job) for job in self._scheduler.get_jobs()]

    def get_job_history(self, limit: int = 50) -> list[dict[str, Any]]:
        """Get recent job execution history."""
        return self._job_history[-limit:]

    # ========================================================================
    # Event listeners
    # ========================================================================

    def _on_job_executed(self, event: JobExecutionEvent) -> None:
        """Called when a job completes successfully."""
        entry = {
            "job_id": event.job_id,
            "status": "success",
            "scheduled_at": (
                event.scheduled_run_time.isoformat()
                if event.scheduled_run_time
                else None
            ),
            "executed_at": datetime.now().isoformat(),
            "retval": str(event.retval)[:200] if event.retval else None,
        }
        self._job_history.append(entry)
        # Keep history bounded
        if len(self._job_history) > 500:
            self._job_history = self._job_history[-500:]

        logger.info(f"✅ Job executed: {event.job_id}")

    def _on_job_error(self, event: JobExecutionEvent) -> None:
        """Called when a job raises an exception."""
        entry = {
            "job_id": event.job_id,
            "status": "error",
            "scheduled_at": (
                event.scheduled_run_time.isoformat()
                if event.scheduled_run_time
                else None
            ),
            "executed_at": datetime.now().isoformat(),
            "error": str(event.exception)[:500] if event.exception else "Unknown error",
        }
        self._job_history.append(entry)
        if len(self._job_history) > 500:
            self._job_history = self._job_history[-500:]

        logger.error(f"❌ Job failed: {event.job_id} — {event.exception}")

    def _on_job_missed(self, event: JobEvent) -> None:
        """Called when a job's execution was missed (e.g., server was down)."""
        entry = {
            "job_id": event.job_id,
            "status": "missed",
            "scheduled_at": (
                event.scheduled_run_time.isoformat()
                if event.scheduled_run_time
                else None
            ),
            "executed_at": datetime.now().isoformat(),
        }
        self._job_history.append(entry)
        logger.warning(f"⚠️ Job missed: {event.job_id}")

    # ========================================================================
    # Helpers
    # ========================================================================

    @staticmethod
    def _job_to_dict(job) -> dict[str, Any]:
        """Convert an APScheduler Job to a serializable dict."""
        trigger_str = str(job.trigger) if job.trigger else "unknown"
        next_run = job.next_run_time.isoformat() if job.next_run_time else None

        return {
            "id": job.id,
            "name": job.name,
            "trigger": trigger_str,
            "next_run_time": next_run,
            "pending": job.pending,
        }


# ============================================================================
# Global singleton — import this in main.py and endpoints
# ============================================================================
scheduler_service = SchedulerService()
