"""
Tool for saving learning records.

This tool allows the agent to save learning content to the user's learning history.
"""

from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.services.secretary_agent.tracing import trace_tool_call


class SaveLearningInput(BaseModel):
    """Input schema for save_learning tool."""

    input_type: str = Field(
        ...,
        description="Type of learning: 'word', 'sentence', 'topic', 'article', 'question', 'idea'",
    )
    user_input: str = Field(
        ...,
        description="The original input from user (word, sentence, topic name, etc.)",
    )
    response_content: str = Field(
        ..., description="The learning content/explanation to save"
    )
    tags: Optional[list[str]] = Field(
        None, description="Optional tags for categorization"
    )


class SaveLearningResponse(BaseModel):
    """Response schema for save_learning tool."""

    success: bool
    record_id: Optional[str] = None
    message: str


@trace_tool_call
def save_learning(
    input_type: str,
    user_input: str,
    response_content: str,
    tags: Optional[list[str]] = None,
    db=None,
    user_id: int = None,
    session_id: Optional[UUID] = None,
) -> SaveLearningResponse:
    """
    Save a learning record to the user's learning history.

    Use this tool when the user:
    - Explicitly asks to save or remember learning content
    - Says "save this", "remember this", "add to my learning"
    - Confirms they want to keep the learning content

    DO NOT use this tool automatically - only when user explicitly requests.

    Args:
        input_type: Type of learning (word, sentence, topic, article, question, idea)
        user_input: The original input from user
        response_content: The learning content to save
        tags: Optional tags for categorization
        db: Database session (injected by agent)
        user_id: User ID (injected by agent)
        session_id: Session ID (injected by agent)

    Returns:
        SaveLearningResponse with success status and record ID
    """
    if db is None or user_id is None:
        return SaveLearningResponse(
            success=False, message="无法保存：缺少数据库连接或用户信息。"
        )

    try:
        from app.models.learning_record import LearningRecordType
        from app.services.learning_record_service import LearningRecordService

        # Map input_type to LearningRecordType
        type_map = {
            "word": LearningRecordType.WORD,
            "sentence": LearningRecordType.SENTENCE,
            "topic": LearningRecordType.TOPIC,
            "article": LearningRecordType.ARTICLE,
            "question": LearningRecordType.QUESTION,
            "idea": LearningRecordType.IDEA,
        }

        record_type = type_map.get(input_type.lower())
        if not record_type:
            return SaveLearningResponse(
                success=False, message=f"不支持的学习类型: {input_type}"
            )

        # Create the learning record
        record = LearningRecordService.save_learning_record(
            db=db,
            user_id=user_id,
            input_type=record_type,
            user_input=user_input,
            response_payload={"content": response_content},
            tags=tags,
            session_id=session_id,
        )

        return SaveLearningResponse(
            success=True,
            record_id=str(record.id),
            message=f"已保存学习记录！类型: {input_type}，内容: {user_input[:50]}...",
        )

    except Exception as e:
        return SaveLearningResponse(success=False, message=f"保存失败: {str(e)}")


class ListLearningInput(BaseModel):
    """Input schema for list_learning tool."""

    type_filter: Optional[str] = Field(
        None, description="Filter by type: word, sentence, topic, etc."
    )
    limit: int = Field(
        10, description="Maximum number of records to return", ge=1, le=50
    )


class ListLearningResponse(BaseModel):
    """Response schema for list_learning tool."""

    records: list[dict]
    total: int
    message: str


@trace_tool_call
def list_learning(
    type_filter: Optional[str] = None,
    limit: int = 10,
    db=None,
    user_id: int = None,
) -> ListLearningResponse:
    """
    List the user's learning records.

    Use this tool when the user wants to:
    - See their learning history
    - Review what they've learned
    - Find previous learning records

    Args:
        type_filter: Optional filter by type
        limit: Maximum records to return
        db: Database session (injected)
        user_id: User ID (injected)

    Returns:
        ListLearningResponse with records list
    """
    if db is None or user_id is None:
        return ListLearningResponse(
            records=[], total=0, message="无法获取：缺少数据库连接或用户信息。"
        )

    try:
        from app.models.learning_record import LearningRecordType
        from app.services.learning_record_service import LearningRecordService

        # Map type filter
        record_type = None
        if type_filter:
            type_map = {
                "word": LearningRecordType.WORD,
                "sentence": LearningRecordType.SENTENCE,
                "topic": LearningRecordType.TOPIC,
                "article": LearningRecordType.ARTICLE,
                "question": LearningRecordType.QUESTION,
                "idea": LearningRecordType.IDEA,
            }
            record_type = type_map.get(type_filter.lower())

        records, total = LearningRecordService.list_learning_records(
            db=db,
            user_id=user_id,
            type_filter=record_type,
            limit=limit,
        )

        records_data = []
        for record in records:
            records_data.append(
                {
                    "id": str(record.id),
                    "type": record.input_type.value,
                    "input": (
                        record.user_input[:100] + "..."
                        if len(record.user_input) > 100
                        else record.user_input
                    ),
                    "created_at": (
                        record.created_at.isoformat() if record.created_at else None
                    ),
                    "is_favorite": record.is_favorite,
                    "review_count": record.review_count,
                }
            )

        if total == 0:
            message = "您还没有学习记录。"
        else:
            message = f"找到 {total} 条学习记录。"

        return ListLearningResponse(
            records=records_data,
            total=total,
            message=message,
        )

    except Exception as e:
        return ListLearningResponse(records=[], total=0, message=f"获取失败: {str(e)}")
