"""Schemas for Philosophy Master agent endpoints."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class PhilosophyPreset(BaseModel):
    """
    Preset controls for response style. Values are validated by allowlists in service layer
    (so we can return HTTP 400 with a clear message).
    """

    school: Optional[str] = Field(
        default=None,
        description="eastern|western|zen|confucian|stoic|existential|kant|nietzsche|schopenhauer|idealism|materialism|mixed",
    )
    tone: Optional[str] = Field(default=None, description="gentle|direct|rigorous|zen")
    depth: Optional[str] = Field(default=None, description="shallow|medium|deep")
    mode: Optional[str] = Field(
        default=None, description="advice|story|compare|daily_practice"
    )
    multi_perspective: Optional[bool] = Field(
        default=None, description="If true, compare 2-3 lenses"
    )


class PhilosophyChatRequest(BaseModel):
    """Non-streaming and streaming request schema."""

    message: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="User message / problem statement",
    )
    preset: Optional[PhilosophyPreset] = Field(
        default=None, description="Optional style preset"
    )
    context: Optional[str] = Field(
        default=None, max_length=20000, description="Optional extra background context"
    )


class PhilosophyChatResponse(BaseModel):
    """Non-streaming response schema."""

    content: str = Field(..., description="Assistant response content (markdown/text)")
    sections: Optional[dict[str, Any]] = Field(
        default=None,
        description="Optional structured sections (analysis/actions/reflection_questions/story/reading_list, etc.)",
    )
