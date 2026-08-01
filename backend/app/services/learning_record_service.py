"""
Learning record service for managing user's learning content.

Provides CRUD operations for learning records (words, sentences,
topics, articles, questions, ideas).
"""

import logging
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import desc, or_
from sqlalchemy.orm import Session

from app.models.learning_record import LearningRecord, LearningRecordType

logger = logging.getLogger(__name__)


class LearningRecordService:
    """
    Service for learning record management.

    Provides operations for:
    - Saving learning content on user confirmation
    - Listing and filtering learning records
    - Searching learning records
    - Managing favorites and review tracking
    """

    @staticmethod
    def save_learning_record(
        db: Session,
        user_id: int,
        input_type: LearningRecordType,
        user_input: str,
        response_payload: dict[str, Any],
        session_id: Optional[UUID] = None,
        tags: Optional[list[str]] = None,
    ) -> LearningRecord:
        """
        Save a learning record to the database.

        Called when user confirms they want to save learning content.

        Args:
            db: Database session
            user_id: ID of the user
            input_type: Type of learning content
            user_input: The original user input (word, sentence, URL, etc.)
            response_payload: Structured response from AI
            session_id: Optional chat session ID
            tags: Optional tags for categorization

        Returns:
            The created LearningRecord
        """
        record = LearningRecord(
            user_id=user_id,
            input_type=input_type,
            user_input=user_input,
            response_payload=response_payload,
            session_id=session_id,
            tags=tags or [],
        )
        db.add(record)
        db.commit()
        db.refresh(record)

        logger.info(
            f"Saved learning record {record.id} "
            f"(type={input_type.value}) for user {user_id}"
        )
        return record

    @staticmethod
    def get_record(
        db: Session, record_id: UUID, user_id: int
    ) -> Optional[LearningRecord]:
        """
        Get a learning record by ID with ownership validation.

        Args:
            db: Database session
            record_id: UUID of the record
            user_id: ID of the user (for ownership check)

        Returns:
            LearningRecord if found and owned by user, None otherwise
        """
        return (
            db.query(LearningRecord)
            .filter(
                LearningRecord.id == record_id,
                LearningRecord.user_id == user_id,
                LearningRecord.is_deleted == False,  # noqa: E712
            )
            .first()
        )

    @staticmethod
    def list_learning_records(
        db: Session,
        user_id: int,
        type_filter: Optional[LearningRecordType] = None,
        favorites_only: bool = False,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[LearningRecord], int]:
        """
        List learning records for a user with filtering.

        Args:
            db: Database session
            user_id: ID of the user
            type_filter: Optional filter by record type
            favorites_only: Only return favorites
            limit: Maximum number of records
            offset: Number of records to skip

        Returns:
            Tuple of (list of records, total count)
        """
        query = db.query(LearningRecord).filter(
            LearningRecord.user_id == user_id,
            LearningRecord.is_deleted == False,  # noqa: E712
        )

        if type_filter:
            query = query.filter(LearningRecord.input_type == type_filter)

        if favorites_only:
            query = query.filter(LearningRecord.is_favorite == True)  # noqa: E712

        total = query.count()

        records = (
            query.order_by(desc(LearningRecord.created_at))
            .offset(offset)
            .limit(limit)
            .all()
        )

        return records, total

    @staticmethod
    def search_learning_records(
        db: Session,
        user_id: int,
        query_text: str,
        type_filter: Optional[LearningRecordType] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[LearningRecord], int]:
        """
        Search learning records by text.

        Searches in user_input field using case-insensitive matching.

        Args:
            db: Database session
            user_id: ID of the user
            query_text: Text to search for
            type_filter: Optional filter by record type
            limit: Maximum number of records
            offset: Number of records to skip

        Returns:
            Tuple of (list of matching records, total count)
        """
        search_pattern = f"%{query_text}%"

        query = db.query(LearningRecord).filter(
            LearningRecord.user_id == user_id,
            LearningRecord.is_deleted == False,  # noqa: E712
            LearningRecord.user_input.ilike(search_pattern),
        )

        if type_filter:
            query = query.filter(LearningRecord.input_type == type_filter)

        total = query.count()

        records = (
            query.order_by(desc(LearningRecord.created_at))
            .offset(offset)
            .limit(limit)
            .all()
        )

        return records, total

    @staticmethod
    def delete_learning_record(db: Session, record_id: UUID, user_id: int) -> bool:
        """
        Soft delete a learning record.

        Args:
            db: Database session
            record_id: UUID of the record
            user_id: ID of the user (for ownership check)

        Returns:
            True if deleted, False if not found or not owned
        """
        record = LearningRecordService.get_record(db, record_id, user_id)
        if not record:
            return False

        record.is_deleted = True
        db.commit()

        logger.info(f"Soft deleted learning record {record_id} for user {user_id}")
        return True

    @staticmethod
    def toggle_favorite(
        db: Session, record_id: UUID, user_id: int
    ) -> Optional[LearningRecord]:
        """
        Toggle the favorite status of a learning record.

        Args:
            db: Database session
            record_id: UUID of the record
            user_id: ID of the user

        Returns:
            Updated LearningRecord, or None if not found
        """
        record = LearningRecordService.get_record(db, record_id, user_id)
        if not record:
            return None

        record.is_favorite = not record.is_favorite
        db.commit()
        db.refresh(record)
        return record

    @staticmethod
    def mark_reviewed(
        db: Session, record_id: UUID, user_id: int
    ) -> Optional[LearningRecord]:
        """
        Mark a learning record as reviewed (increment review count).

        Args:
            db: Database session
            record_id: UUID of the record
            user_id: ID of the user

        Returns:
            Updated LearningRecord, or None if not found
        """
        record = LearningRecordService.get_record(db, record_id, user_id)
        if not record:
            return None

        record.review_count += 1
        record.last_reviewed_at = datetime.utcnow()
        db.commit()
        db.refresh(record)
        return record

    @staticmethod
    def update_tags(
        db: Session, record_id: UUID, user_id: int, tags: list[str]
    ) -> Optional[LearningRecord]:
        """
        Update the tags of a learning record.

        Args:
            db: Database session
            record_id: UUID of the record
            user_id: ID of the user
            tags: New list of tags

        Returns:
            Updated LearningRecord, or None if not found
        """
        record = LearningRecordService.get_record(db, record_id, user_id)
        if not record:
            return None

        record.tags = tags
        db.commit()
        db.refresh(record)
        return record

    @staticmethod
    def get_statistics(db: Session, user_id: int) -> dict[str, Any]:
        """
        Get learning statistics for a user.

        Args:
            db: Database session
            user_id: ID of the user

        Returns:
            Dictionary with statistics
        """
        base_query = db.query(LearningRecord).filter(
            LearningRecord.user_id == user_id,
            LearningRecord.is_deleted == False,  # noqa: E712
        )

        # Total count by type
        type_counts = {}
        for record_type in LearningRecordType:
            count = base_query.filter(LearningRecord.input_type == record_type).count()
            type_counts[record_type.value] = count

        # Favorites count
        favorites_count = base_query.filter(
            LearningRecord.is_favorite == True  # noqa: E712
        ).count()

        # Total reviews
        total_reviews = sum(r.review_count for r in base_query.all())

        return {
            "total": sum(type_counts.values()),
            "by_type": type_counts,
            "favorites": favorites_count,
            "total_reviews": total_reviews,
        }
