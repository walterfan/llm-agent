from typing import Optional

from pydantic import BaseModel, Field


class LLMSettingsUpdate(BaseModel):
    """Request body for creating or updating LLM settings."""

    # Text generation
    chat_base_url: Optional[str] = Field(
        None, max_length=500, examples=["https://api.openai.com/v1"]
    )
    chat_api_key: Optional[str] = Field(None, examples=["sk-..."])
    chat_model: Optional[str] = Field(None, max_length=255, examples=["gpt-4o"])
    chat_temperature: Optional[float] = Field(None, ge=0.0, le=2.0, examples=[0.7])

    # Embedding
    embedding_base_url: Optional[str] = Field(None, max_length=500)
    embedding_api_key: Optional[str] = Field(None)
    embedding_model: Optional[str] = Field(
        None, max_length=255, examples=["text-embedding-3-small"]
    )

    # Image generation
    image_base_url: Optional[str] = Field(None, max_length=500)
    image_api_key: Optional[str] = Field(None)
    image_model: Optional[str] = Field(None, max_length=255, examples=["dall-e-3"])


class LLMSettingsResponse(BaseModel):
    """Response for LLM settings — API keys are masked."""

    # Text generation
    chat_base_url: Optional[str] = None
    chat_api_key_set: bool = False
    chat_model: Optional[str] = None
    chat_temperature: Optional[float] = None

    # Embedding
    embedding_base_url: Optional[str] = None
    embedding_api_key_set: bool = False
    embedding_model: Optional[str] = None

    # Image generation
    image_base_url: Optional[str] = None
    image_api_key_set: bool = False
    image_model: Optional[str] = None

    # Server defaults (read-only, for display)
    defaults: Optional[dict] = None

    model_config = {"from_attributes": True}


def mask_api_key(key: Optional[str]) -> str:
    """Return masked representation for display, e.g. 'sk-****abcd'."""
    if not key:
        return ""
    if len(key) <= 8:
        return "****"
    return key[:3] + "****" + key[-4:]
