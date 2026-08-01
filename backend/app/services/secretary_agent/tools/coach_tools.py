"""
Coach-specific tools for the Coach sub-agent.

ISP: Only tools relevant to coaching/knowledge are included.
"""

import logging
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

logger = logging.getLogger("secretary_agent.coach_tools")


# ============================================================================
# Tool Input Schemas
# ============================================================================


class QueryKnowledgeInput(BaseModel):
    """Input for querying the knowledge base."""

    query: str = Field(..., description="Search query text")
    top_k: int = Field(default=3, description="Number of results to return")


class CreateGoalInput(BaseModel):
    """Input for creating a learning goal."""

    subject: str = Field(..., description="Subject/topic of the goal")
    description: Optional[str] = Field(None, description="Detailed description")
    daily_target_minutes: int = Field(
        default=30, description="Daily study target in minutes"
    )


class LogStudySessionInput(BaseModel):
    """Input for logging a study session."""

    goal_id: Optional[str] = Field(None, description="Associated learning goal ID")
    duration_minutes: int = Field(..., description="Duration in minutes")
    notes: Optional[str] = Field(None, description="Session notes")
    difficulty: Optional[str] = Field(None, description="Difficulty: easy/medium/hard")


class GetProgressInput(BaseModel):
    """Input for getting progress report."""

    goal_id: str = Field(..., description="Learning goal ID")


# ============================================================================
# Tool Functions
# ============================================================================


def query_knowledge(
    query: str,
    top_k: int = 3,
    user_id: Optional[int] = None,
    **kwargs,
) -> str:
    """Query the user's knowledge base using semantic search."""
    from app.services.rag.engine import get_rag_engine

    rag = get_rag_engine()
    if not rag or not rag.is_available:
        return "知识库暂不可用。请先上传一些学习资料。"

    if not user_id:
        return "无法确定用户身份，请重新登录。"

    response = rag.query(query_text=query, user_id=user_id, top_k=top_k)

    if not response.results:
        return f"在知识库中没有找到与「{query}」相关的内容。请尝试其他关键词，或上传更多学习资料。"

    parts = [f"找到 {len(response.results)} 条相关内容:\n"]
    for i, r in enumerate(response.results, 1):
        title = r.metadata.get("title", "未知文档")
        parts.append(f"[{i}] 来源: {title} (相关度: {r.score:.2f})")
        parts.append(f"    {r.content[:300]}")
        parts.append("")

    return "\n".join(parts)


def create_goal(
    subject: str,
    description: Optional[str] = None,
    daily_target_minutes: int = 30,
    db: Optional[Session] = None,
    user_id: Optional[int] = None,
    **kwargs,
) -> str:
    """Create a new learning goal."""
    if not db or not user_id:
        return "无法创建学习目标：缺少数据库连接或用户信息。"

    from app.models.learning_goal import LearningGoal

    goal = LearningGoal(
        id=uuid4(),
        user_id=user_id,
        subject=subject,
        description=description,
        daily_target_minutes=daily_target_minutes,
    )
    db.add(goal)
    db.commit()
    db.refresh(goal)

    return (
        f"✅ 学习目标已创建！\n"
        f"- 主题: {subject}\n"
        f"- 每日目标: {daily_target_minutes} 分钟\n"
        f"- 目标 ID: {goal.id}\n"
        f"加油！坚持就是胜利 💪"
    )


def log_study_session(
    duration_minutes: int,
    goal_id: Optional[str] = None,
    notes: Optional[str] = None,
    difficulty: Optional[str] = None,
    db: Optional[Session] = None,
    user_id: Optional[int] = None,
    **kwargs,
) -> str:
    """Log a study session."""
    if not db or not user_id:
        return "无法记录学习会话：缺少数据库连接或用户信息。"

    from app.models.study_session import Difficulty, StudySession

    diff_enum = None
    if difficulty:
        try:
            diff_enum = Difficulty(difficulty)
        except ValueError:
            pass

    session = StudySession(
        id=uuid4(),
        user_id=user_id,
        goal_id=UUID(goal_id) if goal_id else None,
        duration_minutes=duration_minutes,
        notes=notes,
        difficulty=diff_enum,
    )
    db.add(session)
    db.commit()

    return (
        f"✅ 学习记录已保存！\n"
        f"- 时长: {duration_minutes} 分钟\n"
        f"- 难度: {difficulty or '未评价'}\n"
        f"- 笔记: {notes or '无'}\n"
        f"继续保持！🎯"
    )


def get_progress(
    goal_id: str,
    db: Optional[Session] = None,
    user_id: Optional[int] = None,
    **kwargs,
) -> str:
    """Get progress report for a learning goal."""
    if not db or not user_id:
        return "无法获取进度：缺少数据库连接或用户信息。"

    from app.models.learning_goal import LearningGoal
    from app.models.study_session import StudySession

    goal = (
        db.query(LearningGoal)
        .filter(LearningGoal.id == goal_id, LearningGoal.user_id == user_id)
        .first()
    )
    if not goal:
        return f"未找到目标 (ID: {goal_id})。请检查目标 ID 是否正确。"

    sessions = db.query(StudySession).filter(StudySession.goal_id == goal_id).all()

    total_sessions = len(sessions)
    total_minutes = sum(s.duration_minutes for s in sessions)
    avg_minutes = total_minutes / total_sessions if total_sessions > 0 else 0

    # Simple streak calculation
    session_dates = sorted(set(s.created_at.date() for s in sessions))
    streak = 0
    if session_dates:
        today = datetime.utcnow().date()
        from datetime import timedelta

        if session_dates[-1] >= today - timedelta(days=1):
            streak = 1
            for i in range(len(session_dates) - 2, -1, -1):
                if (session_dates[i + 1] - session_dates[i]).days == 1:
                    streak += 1
                else:
                    break

    report = (
        f"📊 学习进度报告: {goal.subject}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"- 状态: {goal.status.value}\n"
        f"- 总学习次数: {total_sessions} 次\n"
        f"- 总学习时长: {total_minutes} 分钟\n"
        f"- 平均每次: {avg_minutes:.0f} 分钟\n"
        f"- 当前连续学习: {streak} 天\n"
        f"- 每日目标: {goal.daily_target_minutes} 分钟\n"
    )

    if goal.deadline:
        remaining = (goal.deadline - datetime.utcnow()).days
        report += f"- 截止日期: {goal.deadline.strftime('%Y-%m-%d')} (剩余 {max(0, remaining)} 天)\n"

    return report
