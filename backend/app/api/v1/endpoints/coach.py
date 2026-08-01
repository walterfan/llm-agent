"""
AI Coach API endpoints.

Provides learning goal management, study session logging, progress tracking,
and coach chat with 3 modes (coach/tutor/quiz).
"""

import json
import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Annotated, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, get_current_user_from_query
from app.db.base import get_db
from app.models.learning_goal import GoalStatus, LearningGoal
from app.models.study_session import Difficulty, StudySession
from app.models.user import User
from app.schemas.coach import CoachChatRequest, CoachChatResponse, CoachMode
from app.schemas.learning_goal import (
    GoalCreate,
    GoalResponse,
    GoalUpdate,
    ProgressReport,
    SessionCreate,
    SessionResponse,
)
from app.services.rag.engine import get_rag_engine

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# Learning Goals
# ============================================================================


@router.post("/goals", response_model=GoalResponse, status_code=status.HTTP_201_CREATED)
def create_goal(
    payload: GoalCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """Create a new learning goal."""
    goal = LearningGoal(
        id=uuid4(),
        user_id=current_user.id,
        subject=payload.subject,
        description=payload.description,
        daily_target_minutes=payload.daily_target_minutes,
        deadline=payload.deadline,
    )
    db.add(goal)
    db.commit()
    db.refresh(goal)

    logger.info(
        f"Goal created: {payload.subject} (id={goal.id}, user={current_user.id})"
    )
    return goal


@router.get("/goals", response_model=list[GoalResponse])
def list_goals(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    goal_status: Optional[str] = Query(
        None, alias="status", description="Filter by status"
    ),
):
    """List learning goals for the current user."""
    query = db.query(LearningGoal).filter(LearningGoal.user_id == current_user.id)

    if goal_status:
        try:
            status_enum = GoalStatus(goal_status)
            query = query.filter(LearningGoal.status == status_enum)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status: {goal_status}. Valid: {[s.value for s in GoalStatus]}",
            )

    goals = query.order_by(LearningGoal.created_at.desc()).all()
    return goals


@router.patch("/goals/{goal_id}", response_model=GoalResponse)
def update_goal(
    goal_id: UUID,
    payload: GoalUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """Update a learning goal."""
    goal = (
        db.query(LearningGoal)
        .filter(LearningGoal.id == goal_id, LearningGoal.user_id == current_user.id)
        .first()
    )
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")

    update_data = payload.model_dump(exclude_unset=True)

    if "status" in update_data:
        goal.status = GoalStatus(update_data.pop("status"))
        if goal.status == GoalStatus.COMPLETED:
            goal.completed_at = datetime.utcnow()

    for key, value in update_data.items():
        setattr(goal, key, value)

    db.commit()
    db.refresh(goal)

    logger.info(f"Goal updated: {goal_id}")
    return goal


# ============================================================================
# Study Sessions
# ============================================================================


@router.post(
    "/sessions", response_model=SessionResponse, status_code=status.HTTP_201_CREATED
)
def log_session(
    payload: SessionCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """Log a study session."""
    # Validate goal_id if provided
    if payload.goal_id:
        goal = (
            db.query(LearningGoal)
            .filter(
                LearningGoal.id == payload.goal_id,
                LearningGoal.user_id == current_user.id,
            )
            .first()
        )
        if not goal:
            raise HTTPException(status_code=404, detail="Goal not found")

    session = StudySession(
        id=uuid4(),
        user_id=current_user.id,
        goal_id=payload.goal_id,
        duration_minutes=payload.duration_minutes,
        notes=payload.notes,
        difficulty=Difficulty(payload.difficulty) if payload.difficulty else None,
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    logger.info(
        f"Study session logged: {payload.duration_minutes}min "
        f"(goal={payload.goal_id}, user={current_user.id})"
    )
    return session


@router.get("/sessions", response_model=list[SessionResponse])
def list_sessions(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    goal_id: Optional[UUID] = Query(None, description="Filter by goal ID"),
):
    """List study sessions for the current user."""
    query = db.query(StudySession).filter(StudySession.user_id == current_user.id)

    if goal_id:
        query = query.filter(StudySession.goal_id == goal_id)

    sessions = query.order_by(StudySession.created_at.desc()).all()
    return sessions


# ============================================================================
# Progress
# ============================================================================


@router.get("/progress/{goal_id}", response_model=ProgressReport)
def get_progress(
    goal_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """Get progress report for a learning goal."""
    goal = (
        db.query(LearningGoal)
        .filter(LearningGoal.id == goal_id, LearningGoal.user_id == current_user.id)
        .first()
    )
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")

    # Get all sessions for this goal
    sessions = (
        db.query(StudySession)
        .filter(
            StudySession.goal_id == goal_id, StudySession.user_id == current_user.id
        )
        .order_by(StudySession.created_at.asc())
        .all()
    )

    total_sessions = len(sessions)
    total_minutes = sum(s.duration_minutes for s in sessions)
    avg_minutes = total_minutes / total_sessions if total_sessions > 0 else 0.0

    # Calculate streaks
    current_streak, longest_streak = _calculate_streaks(sessions)

    # Calculate completion percentage
    completion_pct = 0.0
    days_remaining = None
    if goal.deadline:
        total_days = (goal.deadline - goal.created_at).days
        elapsed_days = (datetime.utcnow() - goal.created_at).days
        if total_days > 0:
            completion_pct = min(100.0, (elapsed_days / total_days) * 100)
        remaining = (goal.deadline - datetime.utcnow()).days
        days_remaining = max(0, remaining)

    if goal.status == GoalStatus.COMPLETED:
        completion_pct = 100.0

    return ProgressReport(
        goal=GoalResponse.model_validate(goal),
        total_sessions=total_sessions,
        total_minutes=total_minutes,
        avg_minutes_per_session=round(avg_minutes, 1),
        current_streak_days=current_streak,
        longest_streak_days=longest_streak,
        completion_percentage=round(completion_pct, 1),
        days_remaining=days_remaining,
        ai_feedback=None,  # AI feedback generated on demand via chat
    )


def _calculate_streaks(sessions: list[StudySession]) -> tuple[int, int]:
    """
    Calculate current and longest study streaks.

    A streak is consecutive days with at least one study session.

    Returns:
        (current_streak, longest_streak)
    """
    if not sessions:
        return 0, 0

    # Group sessions by date
    session_dates = sorted(set(s.created_at.date() for s in sessions))

    if not session_dates:
        return 0, 0

    # Calculate longest streak
    longest = 1
    current = 1
    for i in range(1, len(session_dates)):
        if (session_dates[i] - session_dates[i - 1]).days == 1:
            current += 1
            longest = max(longest, current)
        else:
            current = 1

    # Calculate current streak (from today backwards)
    today = datetime.utcnow().date()
    current_streak = 0

    # Check if today or yesterday has a session (allow 1 day gap for "current")
    if session_dates[-1] >= today - timedelta(days=1):
        current_streak = 1
        for i in range(len(session_dates) - 2, -1, -1):
            if (session_dates[i + 1] - session_dates[i]).days == 1:
                current_streak += 1
            else:
                break

    return current_streak, longest


# ============================================================================
# Coach Chat
# ============================================================================


@router.post("/chat", response_model=CoachChatResponse)
async def coach_chat(
    payload: CoachChatRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """Coach chat (non-streaming) with mode selection and RAG context."""
    from app.services.coach_service import get_coach_response

    try:
        result = await get_coach_response(
            message=payload.message,
            mode=payload.mode,
            user_id=current_user.id,
            session_id=payload.session_id,
            goal_id=str(payload.goal_id) if payload.goal_id else None,
            db=db,
        )
        return CoachChatResponse(
            content=result["content"],
            sources=result.get("sources", []),
            session_id=result["session_id"],
            mode=payload.mode.value,
        )
    except Exception as e:
        logger.error(f"Coach chat failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Coach chat failed: {str(e)}")


@router.get("/chat/stream")
async def coach_chat_stream(
    message: str = Query(..., description="User message"),
    mode: str = Query("coach", description="Coaching mode: coach/tutor/quiz"),
    session_id: Optional[str] = Query(None, description="Session ID"),
    goal_id: Optional[str] = Query(None, description="Goal ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_query),
):
    """Coach chat with SSE streaming."""
    from app.services.coach_service import get_coach_response_stream

    try:
        coach_mode = CoachMode(mode)
    except ValueError:
        coach_mode = CoachMode.COACH

    async def event_generator():
        actual_sid = session_id  # Will be updated from stream metadata

        # Send start event (preliminary session_id, may be updated)
        yield f"data: {json.dumps({'type': 'start', 'session_id': session_id or ''})}\n\n"

        try:
            async for chunk in get_coach_response_stream(
                message=message,
                mode=coach_mode,
                user_id=current_user.id,
                session_id=session_id,
                goal_id=goal_id,
                db=db,
            ):
                if chunk.get("type") == "token":
                    yield f"data: {json.dumps({'type': 'token', 'content': chunk['content']})}\n\n"
                elif chunk.get("type") == "meta":
                    actual_sid = chunk.get("session_id", actual_sid)

            # Send done event with the actual session_id
            yield f"data: {json.dumps({'type': 'done', 'session_id': actual_sid or ''})}\n\n"

        except Exception as e:
            logger.error(f"Coach stream error: {e}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
