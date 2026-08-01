"""
API endpoints for learning record management.

Provides endpoints for:
- Saving learning records (on user confirmation)
- Listing and searching learning records
- Managing favorites and reviews
"""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, get_db
from app.models.learning_record import LearningRecordType
from app.models.user import User
from app.schemas.learning_record import (
    LearningRecordCreate,
    LearningRecordListResponse,
    LearningRecordResponse,
    LearningRecordUpdate,
    LearningStatisticsResponse,
)
from app.services.learning_record_service import LearningRecordService
from app.services.secretary_agent.metrics import (
    record_learning_record,
    record_learning_review,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# ============================================================================
# Learning Record CRUD
# ============================================================================


@router.post("/confirm", response_model=LearningRecordResponse)
async def confirm_learning(
    request: LearningRecordCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Save a learning record after user confirmation.

    Called when user confirms they want to save learning content
    (word, sentence, topic, article, question, or idea).
    """
    record = LearningRecordService.save_learning_record(
        db=db,
        user_id=current_user.id,
        input_type=request.input_type,
        user_input=request.user_input,
        response_payload=request.response_payload,
        session_id=request.session_id,
        tags=request.tags,
    )

    # Record metrics
    record_learning_record(request.input_type.value)

    return LearningRecordResponse(
        id=record.id,
        input_type=record.input_type,
        user_input=record.user_input,
        response_payload=record.response_payload,
        session_id=record.session_id,
        tags=record.tags or [],
        is_favorite=record.is_favorite,
        review_count=record.review_count,
        last_reviewed_at=record.last_reviewed_at,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


@router.get("/records", response_model=LearningRecordListResponse)
async def list_records(
    type: Optional[LearningRecordType] = Query(
        None, description="Filter by record type"
    ),
    favorites_only: bool = Query(False, description="Only show favorites"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    List learning records with optional filtering.

    Supports filtering by:
    - type: word, sentence, topic, article, question, idea
    - favorites_only: only return favorited records
    """
    offset = (page - 1) * page_size

    records, total = LearningRecordService.list_learning_records(
        db=db,
        user_id=current_user.id,
        type_filter=type,
        favorites_only=favorites_only,
        limit=page_size,
        offset=offset,
    )

    return LearningRecordListResponse(
        records=[
            LearningRecordResponse(
                id=r.id,
                input_type=r.input_type,
                user_input=r.user_input,
                response_payload=r.response_payload,
                session_id=r.session_id,
                tags=r.tags or [],
                is_favorite=r.is_favorite,
                review_count=r.review_count,
                last_reviewed_at=r.last_reviewed_at,
                created_at=r.created_at,
                updated_at=r.updated_at,
            )
            for r in records
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/records/{record_id}", response_model=LearningRecordResponse)
async def get_record(
    record_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get a single learning record by ID."""
    record = LearningRecordService.get_record(db, record_id, current_user.id)
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")

    return LearningRecordResponse(
        id=record.id,
        input_type=record.input_type,
        user_input=record.user_input,
        response_payload=record.response_payload,
        session_id=record.session_id,
        tags=record.tags or [],
        is_favorite=record.is_favorite,
        review_count=record.review_count,
        last_reviewed_at=record.last_reviewed_at,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


@router.patch("/records/{record_id}", response_model=LearningRecordResponse)
async def update_record(
    record_id: UUID,
    request: LearningRecordUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Update a learning record (tags, favorite status)."""
    record = LearningRecordService.get_record(db, record_id, current_user.id)
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")

    if request.tags is not None:
        record = LearningRecordService.update_tags(
            db, record_id, current_user.id, request.tags
        )

    if request.is_favorite is not None:
        if request.is_favorite != record.is_favorite:
            record = LearningRecordService.toggle_favorite(
                db, record_id, current_user.id
            )

    return LearningRecordResponse(
        id=record.id,
        input_type=record.input_type,
        user_input=record.user_input,
        response_payload=record.response_payload,
        session_id=record.session_id,
        tags=record.tags or [],
        is_favorite=record.is_favorite,
        review_count=record.review_count,
        last_reviewed_at=record.last_reviewed_at,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


@router.delete("/records/{record_id}", status_code=204)
async def delete_record(
    record_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Delete a learning record."""
    success = LearningRecordService.delete_learning_record(
        db, record_id, current_user.id
    )
    if not success:
        raise HTTPException(status_code=404, detail="Record not found")
    return None


# ============================================================================
# Search
# ============================================================================


@router.get("/search", response_model=LearningRecordListResponse)
async def search_records(
    q: str = Query(..., min_length=1, description="Search query"),
    type: Optional[LearningRecordType] = Query(
        None, description="Filter by record type"
    ),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Search learning records by text.

    Searches in user_input field.
    """
    offset = (page - 1) * page_size

    records, total = LearningRecordService.search_learning_records(
        db=db,
        user_id=current_user.id,
        query_text=q,
        type_filter=type,
        limit=page_size,
        offset=offset,
    )

    return LearningRecordListResponse(
        records=[
            LearningRecordResponse(
                id=r.id,
                input_type=r.input_type,
                user_input=r.user_input,
                response_payload=r.response_payload,
                session_id=r.session_id,
                tags=r.tags or [],
                is_favorite=r.is_favorite,
                review_count=r.review_count,
                last_reviewed_at=r.last_reviewed_at,
                created_at=r.created_at,
                updated_at=r.updated_at,
            )
            for r in records
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


# ============================================================================
# Engagement
# ============================================================================


@router.post("/records/{record_id}/review", response_model=LearningRecordResponse)
async def mark_reviewed(
    record_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Mark a learning record as reviewed (increment review count)."""
    record = LearningRecordService.mark_reviewed(db, record_id, current_user.id)
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")

    # Record metrics
    record_learning_review(record.input_type.value)

    return LearningRecordResponse(
        id=record.id,
        input_type=record.input_type,
        user_input=record.user_input,
        response_payload=record.response_payload,
        session_id=record.session_id,
        tags=record.tags or [],
        is_favorite=record.is_favorite,
        review_count=record.review_count,
        last_reviewed_at=record.last_reviewed_at,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


@router.post("/records/{record_id}/favorite", response_model=LearningRecordResponse)
async def toggle_favorite(
    record_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Toggle favorite status of a learning record."""
    record = LearningRecordService.toggle_favorite(db, record_id, current_user.id)
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")

    return LearningRecordResponse(
        id=record.id,
        input_type=record.input_type,
        user_input=record.user_input,
        response_payload=record.response_payload,
        session_id=record.session_id,
        tags=record.tags or [],
        is_favorite=record.is_favorite,
        review_count=record.review_count,
        last_reviewed_at=record.last_reviewed_at,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


# ============================================================================
# Statistics
# ============================================================================


@router.get("/statistics", response_model=LearningStatisticsResponse)
async def get_statistics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get learning statistics for the current user."""
    stats = LearningRecordService.get_statistics(db, current_user.id)

    return LearningStatisticsResponse(
        total=stats["total"],
        by_type=stats["by_type"],
        favorites=stats["favorites"],
        total_reviews=stats["total_reviews"],
    )
