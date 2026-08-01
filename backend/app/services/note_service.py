"""
Note service for Personal Secretary agent.

Provides CRUD operations for notes/memos.
"""

from datetime import datetime
from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy import and_, or_, func
from sqlalchemy.orm import Session

from app.models.note import Note


class NoteService:
    """Service for managing notes."""

    @staticmethod
    def create_note(
        db: Session,
        user_id: int,
        content: str,
        title: Optional[str] = None,
        tags: Optional[List[str]] = None,
        session_id: Optional[UUID] = None,
    ) -> Note:
        """
        Create a new note.

        Args:
            db: Database session
            user_id: Owner user ID
            content: Note content
            title: Optional note title
            tags: Optional list of tags
            session_id: Optional chat session ID

        Returns:
            Created Note object
        """
        note = Note(
            user_id=user_id,
            content=content,
            title=title,
            tags=tags or [],
            session_id=session_id,
        )

        db.add(note)
        db.commit()
        db.refresh(note)

        return note

    @staticmethod
    def get_note(
        db: Session,
        note_id: UUID,
        user_id: int,
    ) -> Optional[Note]:
        """
        Get a note by ID.

        Args:
            db: Database session
            note_id: Note ID
            user_id: Owner user ID

        Returns:
            Note if found and owned by user, None otherwise
        """
        return (
            db.query(Note)
            .filter(
                and_(
                    Note.id == note_id,
                    Note.user_id == user_id,
                    Note.deleted_at.is_(None),
                )
            )
            .first()
        )

    @staticmethod
    def list_notes(
        db: Session,
        user_id: int,
        include_archived: bool = False,
        tags: Optional[List[str]] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[Note], int]:
        """
        List user's notes with pagination.

        Args:
            db: Database session
            user_id: Owner user ID
            include_archived: Include archived notes
            tags: Filter by tags (any match)
            limit: Maximum number of notes
            offset: Number of notes to skip

        Returns:
            Tuple of (notes list, total count)
        """
        query = db.query(Note).filter(
            and_(
                Note.user_id == user_id,
                Note.deleted_at.is_(None),
            )
        )

        if not include_archived:
            query = query.filter(Note.is_archived == False)

        # Count before pagination
        total = query.count()

        # Order by pinned first, then by updated_at
        query = query.order_by(
            Note.is_pinned.desc(),
            Note.updated_at.desc(),
        )

        notes = query.offset(offset).limit(limit).all()

        return notes, total

    @staticmethod
    def search_notes(
        db: Session,
        user_id: int,
        query_text: str,
        limit: int = 20,
    ) -> Tuple[List[Note], int]:
        """
        Search notes by content or title.

        Args:
            db: Database session
            user_id: Owner user ID
            query_text: Search query
            limit: Maximum number of results

        Returns:
            Tuple of (matching notes, total count)
        """
        search_pattern = f"%{query_text}%"

        query = db.query(Note).filter(
            and_(
                Note.user_id == user_id,
                Note.deleted_at.is_(None),
                or_(
                    Note.title.ilike(search_pattern),
                    Note.content.ilike(search_pattern),
                ),
            )
        )

        total = query.count()
        notes = query.order_by(Note.updated_at.desc()).limit(limit).all()

        return notes, total

    @staticmethod
    def update_note(
        db: Session,
        note_id: UUID,
        user_id: int,
        title: Optional[str] = None,
        content: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> Optional[Note]:
        """
        Update a note.

        Args:
            db: Database session
            note_id: Note ID
            user_id: Owner user ID
            title: New title (if provided)
            content: New content (if provided)
            tags: New tags (if provided)

        Returns:
            Updated Note if found, None otherwise
        """
        note = NoteService.get_note(db, note_id, user_id)
        if not note:
            return None

        if title is not None:
            note.title = title
        if content is not None:
            note.content = content
        if tags is not None:
            note.tags = tags

        db.commit()
        db.refresh(note)

        return note

    @staticmethod
    def toggle_pin(
        db: Session,
        note_id: UUID,
        user_id: int,
    ) -> Optional[Note]:
        """Toggle pin status of a note."""
        note = NoteService.get_note(db, note_id, user_id)
        if not note:
            return None

        note.is_pinned = not note.is_pinned
        db.commit()
        db.refresh(note)

        return note

    @staticmethod
    def toggle_archive(
        db: Session,
        note_id: UUID,
        user_id: int,
    ) -> Optional[Note]:
        """Toggle archive status of a note."""
        note = NoteService.get_note(db, note_id, user_id)
        if not note:
            return None

        note.is_archived = not note.is_archived
        db.commit()
        db.refresh(note)

        return note

    @staticmethod
    def delete_note(
        db: Session,
        note_id: UUID,
        user_id: int,
    ) -> bool:
        """
        Soft delete a note.

        Returns:
            True if deleted, False if not found
        """
        note = NoteService.get_note(db, note_id, user_id)
        if not note:
            return False

        note.soft_delete()
        db.commit()

        return True
