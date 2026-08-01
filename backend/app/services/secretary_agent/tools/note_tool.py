"""
Note/memo tools for Personal Secretary agent.

Allows the agent to save and search notes for the user.
"""

from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.services.secretary_agent.tracing import trace_tool_call


class SaveNoteInput(BaseModel):
    """Input schema for save_note tool."""

    content: str = Field(..., description="Note content to save")
    title: Optional[str] = Field(None, description="Optional note title")
    tags: Optional[List[str]] = Field(
        None, description="Optional tags for categorization"
    )


class SaveNoteResponse(BaseModel):
    """Response schema for save_note tool."""

    note_id: str
    title: Optional[str]
    content: str
    tags: List[str]
    message: str


class SearchNotesInput(BaseModel):
    """Input schema for search_notes tool."""

    query: str = Field(..., description="Search query to find notes")
    limit: int = Field(10, description="Maximum number of results", ge=1, le=50)


class SearchNotesResponse(BaseModel):
    """Response schema for search_notes tool."""

    notes: List[dict]
    total: int
    message: str


class ListNotesInput(BaseModel):
    """Input schema for list_notes tool."""

    include_archived: bool = Field(False, description="Include archived notes")
    limit: int = Field(20, description="Maximum number of notes", ge=1, le=100)


class ListNotesResponse(BaseModel):
    """Response schema for list_notes tool."""

    notes: List[dict]
    total: int
    message: str


@trace_tool_call
def save_note(
    content: str,
    title: Optional[str] = None,
    tags: Optional[List[str]] = None,
    db=None,
    user_id: int = None,
    session_id: Optional[UUID] = None,
) -> SaveNoteResponse:
    """
    Save a note or memo for the user.

    Use this tool when the user wants to:
    - Save a piece of information for later
    - Create a memo or note
    - Record something important

    Args:
        content: The note content to save
        title: Optional title for the note
        tags: Optional tags for categorization
        db: Database session (injected)
        user_id: User ID (injected)
        session_id: Chat session ID (injected)

    Returns:
        SaveNoteResponse with note details and confirmation
    """
    from app.services.note_service import NoteService

    note = NoteService.create_note(
        db=db,
        user_id=user_id,
        content=content,
        title=title,
        tags=tags,
        session_id=session_id,
    )

    return SaveNoteResponse(
        note_id=str(note.id),
        title=note.title,
        content=note.content,
        tags=note.tags or [],
        message=f"已保存笔记{'：' + note.title if note.title else ''}。",
    )


@trace_tool_call
def search_notes(
    query: str,
    limit: int = 10,
    db=None,
    user_id: int = None,
) -> SearchNotesResponse:
    """
    Search through user's saved notes.

    Use this tool when the user wants to:
    - Find a previously saved note
    - Search their memos
    - Look up saved information

    Args:
        query: Search query
        limit: Maximum number of results
        db: Database session (injected)
        user_id: User ID (injected)

    Returns:
        SearchNotesResponse with matching notes
    """
    from app.services.note_service import NoteService

    notes, total = NoteService.search_notes(
        db=db,
        user_id=user_id,
        query_text=query,
        limit=limit,
    )

    notes_data = [note.to_dict() for note in notes]

    if total == 0:
        message = f"没有找到包含 '{query}' 的笔记。"
    else:
        message = f"找到 {total} 条相关笔记。"

    return SearchNotesResponse(
        notes=notes_data,
        total=total,
        message=message,
    )


@trace_tool_call
def list_notes(
    include_archived: bool = False,
    limit: int = 20,
    db=None,
    user_id: int = None,
) -> ListNotesResponse:
    """
    List user's notes.

    Use this tool when the user wants to:
    - See all their notes
    - Browse their memos
    - Get an overview of saved notes

    Args:
        include_archived: Include archived notes
        limit: Maximum number of notes
        db: Database session (injected)
        user_id: User ID (injected)

    Returns:
        ListNotesResponse with notes list
    """
    from app.services.note_service import NoteService

    notes, total = NoteService.list_notes(
        db=db,
        user_id=user_id,
        include_archived=include_archived,
        limit=limit,
    )

    notes_data = [note.to_dict() for note in notes]

    if total == 0:
        message = "您还没有保存任何笔记。"
    else:
        message = f"共有 {total} 条笔记。"

    return ListNotesResponse(
        notes=notes_data,
        total=total,
        message=message,
    )
