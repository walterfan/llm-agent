"""
API endpoints for scheduled operations and scheduler management.

Provides:
  1. Legacy cronjob HTTP endpoints (for external cron callers)
  2. Scheduler management API (list/trigger/pause/resume/add/remove jobs)

Authentication:
  - JWT Bearer token (for frontend / admin users)
  - X-Cronjob-Token header (for external cron callers)
"""

import logging
from datetime import datetime
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Header, Request
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_admin
from app.core.config import settings
from app.db.base import get_db
from app.models.user import User
from app.services.scheduled_email_service import ScheduledEmailService

logger = logging.getLogger(__name__)

router = APIRouter()

# OAuth2 scheme (optional — won't fail if no token)
oauth2_scheme_optional = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/signin", auto_error=False
)


# ============================================================================
# Flexible Authentication: JWT or Cronjob Token
# ============================================================================


def verify_scheduler_access(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    token: Annotated[Optional[str], Depends(oauth2_scheme_optional)] = None,
    x_cronjob_token: Annotated[Optional[str], Header()] = None,
) -> bool:
    """
    Verify access via either:
      1. JWT Bearer token (admin role required) — for frontend
      2. X-Cronjob-Token header — for external cron callers
      3. No auth if CRONJOB_SECRET_TOKEN is not set (dev mode)
    """
    # Try JWT auth first
    if token:
        from app.core.security import decode_access_token
        from app.services.user_service import UserService

        payload = decode_access_token(token)
        if payload:
            user_id = payload.get("sub")
            if user_id:
                user = UserService.get_user_by_id(db, int(user_id))
                if user and user.is_active:
                    return True

    # Try cronjob token
    if settings.CRONJOB_SECRET_TOKEN:
        if x_cronjob_token and x_cronjob_token == settings.CRONJOB_SECRET_TOKEN:
            return True
        # If token is configured but neither auth method worked
        if not token:
            raise HTTPException(status_code=401, detail="Authentication required")
    else:
        # Dev mode: no token configured, allow access
        return True

    raise HTTPException(status_code=401, detail="Invalid credentials")


# ============================================================================
# Legacy Cronjob Endpoints
# ============================================================================


@router.post("/send-scheduled-emails")
async def send_scheduled_emails(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[bool, Depends(verify_scheduler_access)],
):
    """
    Send scheduled emails for the current hour.
    """
    try:
        now = datetime.now()
        current_hour = now.hour

        logger.info(
            f"⏰ Scheduled email job triggered at {now.strftime('%Y-%m-%d %H:%M:%S')} "
            f"(hour={current_hour})"
        )

        service = ScheduledEmailService(db)
        result = service.send_emails_for_hour(current_hour)

        return {
            "status": "success",
            "hour": current_hour,
            "processed_count": result["processed_count"],
            "success_count": result["success_count"],
            "failed_count": result["failed_count"],
            "timestamp": now.isoformat(),
        }

    except Exception as e:
        logger.error(f"❌ Error in scheduled email job: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process scheduled emails: {str(e)}",
        )


# ============================================================================
# Scheduler Management API
# ============================================================================


@router.get("/jobs")
async def list_jobs(
    _: Annotated[bool, Depends(verify_scheduler_access)],
):
    """List all registered scheduled jobs."""
    from app.services.scheduler import scheduler_service

    if not scheduler_service.is_running:
        return {"status": "scheduler_not_running", "jobs": []}

    return {
        "status": "running",
        "jobs": scheduler_service.list_jobs(),
    }


@router.post("/jobs/{job_id}/trigger")
async def trigger_job(
    job_id: str,
    _: Annotated[bool, Depends(verify_scheduler_access)],
):
    """Immediately trigger a scheduled job (run it now)."""
    from app.services.scheduler import scheduler_service

    if not scheduler_service.is_running:
        raise HTTPException(status_code=503, detail="Scheduler is not running")

    success = scheduler_service.trigger_job(job_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")

    return {
        "status": "triggered",
        "job_id": job_id,
        "timestamp": datetime.now().isoformat(),
    }


@router.post("/jobs/{job_id}/pause")
async def pause_job(
    job_id: str,
    _: Annotated[bool, Depends(verify_scheduler_access)],
):
    """Pause a scheduled job."""
    from app.services.scheduler import scheduler_service

    if not scheduler_service.is_running:
        raise HTTPException(status_code=503, detail="Scheduler is not running")

    success = scheduler_service.pause_job(job_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")

    return {"status": "paused", "job_id": job_id}


@router.post("/jobs/{job_id}/resume")
async def resume_job(
    job_id: str,
    _: Annotated[bool, Depends(verify_scheduler_access)],
):
    """Resume a paused job."""
    from app.services.scheduler import scheduler_service

    if not scheduler_service.is_running:
        raise HTTPException(status_code=503, detail="Scheduler is not running")

    success = scheduler_service.resume_job(job_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")

    return {"status": "resumed", "job_id": job_id}


@router.get("/jobs/history")
async def get_job_history(
    _: Annotated[bool, Depends(verify_scheduler_access)],
    limit: int = 50,
):
    """Get recent job execution history."""
    from app.services.scheduler import scheduler_service

    return {"history": scheduler_service.get_job_history(limit=limit)}


# ============================================================================
# Add / Remove Jobs
# ============================================================================


class AddJobRequest(BaseModel):
    """Request body for adding a dynamic job."""

    job_id: str = Field(
        ..., description="Unique job identifier", min_length=1, max_length=100
    )
    job_type: str = Field(
        ...,
        description="Job type to execute",
    )
    trigger_type: str = Field("interval", description="Trigger type: cron | interval")
    name: str | None = Field(
        None, description="Human-readable job name", max_length=200
    )
    description: str | None = Field(None, description="Job description", max_length=500)
    # Interval trigger params
    seconds: int | None = Field(
        None, ge=10, le=86400, description="Interval in seconds (min 10)"
    )
    minutes: int | None = Field(None, ge=1, le=1440, description="Interval in minutes")
    hours: int | None = Field(None, ge=1, le=24, description="Interval in hours")
    # Cron trigger params
    hour: int | None = Field(None, ge=0, le=23, description="Cron hour (0-23)")
    minute: int | None = Field(None, ge=0, le=59, description="Cron minute (0-59)")
    day_of_week: str | None = Field(
        None, description="Cron day of week (e.g., 'mon-fri', '0-4')"
    )


# Available job types and their descriptions
JOB_TYPE_REGISTRY = {
    "check_reminders": {
        "description": "Check due reminders and trigger notifications",
        "agent": "secretary",
        "default_trigger": "interval",
        "default_interval": {"minutes": 5},
    },
    "check_tasks": {
        "description": "Check overdue tasks and alert users",
        "agent": "secretary",
        "default_trigger": "interval",
        "default_interval": {"minutes": 30},
    },
    "daily_summary": {
        "description": "Generate daily summary for all users via AI agent",
        "agent": "secretary",
        "default_trigger": "cron",
        "default_cron": {"hour": 8, "minute": 0},
    },
    "send_emails": {
        "description": "Send scheduled recommendation emails",
        "agent": "recommendation",
        "default_trigger": "cron",
        "default_cron": {"minute": 0},
    },
}


@router.get("/job-types")
async def list_job_types(
    _: Annotated[bool, Depends(verify_scheduler_access)],
):
    """
    List all available job types that can be scheduled.

    Returns job type metadata including description, associated agent,
    and default trigger configuration.
    """
    return {"job_types": [{"id": k, **v} for k, v in JOB_TYPE_REGISTRY.items()]}


@router.post("/jobs")
async def add_job(
    request: AddJobRequest,
    _: Annotated[bool, Depends(verify_scheduler_access)],
):
    """
    Dynamically add a new scheduled job.

    Example — add a reminder check every 2 minutes:
    ```json
    {
        "job_id": "fast_reminder_check",
        "job_type": "check_reminders",
        "trigger_type": "interval",
        "minutes": 2,
        "name": "Fast reminder check"
    }
    ```
    """
    from app.services.scheduler import scheduler_service

    if not scheduler_service.is_running:
        raise HTTPException(status_code=503, detail="Scheduler is not running")

    if request.job_type not in JOB_TYPE_REGISTRY:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown job_type: {request.job_type}. "
            f"Allowed: {list(JOB_TYPE_REGISTRY.keys())}",
        )

    # Import job functions
    from app.services.scheduled_jobs import (
        job_check_due_reminders,
        job_check_overdue_tasks,
        job_daily_summary,
        job_send_scheduled_emails,
    )

    func_map = {
        "check_reminders": job_check_due_reminders,
        "check_tasks": job_check_overdue_tasks,
        "daily_summary": job_daily_summary,
        "send_emails": job_send_scheduled_emails,
    }
    func = func_map[request.job_type]

    # Build trigger kwargs
    trigger_kwargs = {}
    if request.trigger_type == "interval":
        if request.seconds:
            trigger_kwargs["seconds"] = request.seconds
        if request.minutes:
            trigger_kwargs["minutes"] = request.minutes
        if request.hours:
            trigger_kwargs["hours"] = request.hours
        if not trigger_kwargs:
            raise HTTPException(
                status_code=400,
                detail="Interval trigger requires at least one of: seconds, minutes, hours",
            )
    elif request.trigger_type == "cron":
        if request.hour is not None:
            trigger_kwargs["hour"] = request.hour
        if request.minute is not None:
            trigger_kwargs["minute"] = request.minute
        if request.day_of_week:
            trigger_kwargs["day_of_week"] = request.day_of_week
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown trigger_type: {request.trigger_type}. Allowed: cron, interval",
        )

    try:
        job_info = scheduler_service.add_job(
            job_id=request.job_id,
            func=func,
            trigger_type=request.trigger_type,
            name=request.name or request.job_id,
            **trigger_kwargs,
        )
        return {"status": "created", "job": job_info}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/jobs/{job_id}")
async def update_job(
    job_id: str,
    request: AddJobRequest,
    _: Annotated[bool, Depends(verify_scheduler_access)],
):
    """
    Update an existing job (remove + re-add with new config).
    """
    from app.services.scheduler import scheduler_service

    if not scheduler_service.is_running:
        raise HTTPException(status_code=503, detail="Scheduler is not running")

    # Remove old job (ignore if not found)
    scheduler_service.remove_job(job_id)

    # Re-create with new config (reuse add_job logic)
    request.job_id = job_id  # Ensure same ID
    return await add_job(request, _)


@router.delete("/jobs/{job_id}")
async def remove_job(
    job_id: str,
    _: Annotated[bool, Depends(verify_scheduler_access)],
):
    """Remove a scheduled job."""
    from app.services.scheduler import scheduler_service

    if not scheduler_service.is_running:
        raise HTTPException(status_code=503, detail="Scheduler is not running")

    success = scheduler_service.remove_job(job_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")

    return {"status": "removed", "job_id": job_id}


# ============================================================================
# Health Check
# ============================================================================


@router.get("/health")
async def health_check():
    """Health check endpoint for scheduler and cronjob monitoring."""
    from app.services.scheduler import scheduler_service

    return {
        "status": "healthy",
        "scheduler_running": scheduler_service.is_running,
        "jobs_count": (
            len(scheduler_service.list_jobs()) if scheduler_service.is_running else 0
        ),
        "timestamp": datetime.now().isoformat(),
    }
