"""Request/response schemas for translation API."""

from pydantic import BaseModel, Field


class TranslationUrlRequest(BaseModel):
    """JSON body for URL-based translation."""

    url: str = Field(..., description="URL of the content to translate")
    output_mode: str = Field(
        default="chinese_only",
        description="Output mode: chinese_only or bilingual",
    )


class TranslationResponse(BaseModel):
    """Response body for non-streaming translation."""

    translated_markdown: str = Field(
        ..., description="Translated content (Chinese or bilingual)"
    )
    explanation: str = Field(..., description="Key terms and context explanation")
    summary: str = Field(..., description="Concise summary in Chinese")
    source_truncated: bool = Field(
        default=False,
        description="True if source was truncated to max length",
    )
