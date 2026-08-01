"""LLM Settings API — per-user LLM provider configuration."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.core.config import settings
from app.db.base import get_db
from app.models.llm_settings import LLMSettings
from app.models.user import User
from app.schemas.llm_settings import (
    LLMSettingsResponse,
    LLMSettingsUpdate,
    mask_api_key,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def _server_defaults() -> dict:
    """Expose non-secret server defaults for the frontend to show as placeholders."""
    return {
        "chat_base_url": settings.LLM_BASE_URL,
        "chat_model": settings.LLM_MODEL,
        "embedding_base_url": settings.EMBEDDING_BASE_URL or settings.LLM_BASE_URL,
        "embedding_model": settings.EMBEDDING_MODEL or settings.LLM_EMBEDDING_MODEL,
        "image_base_url": "",
        "image_model": "",
    }


def _to_response(row: LLMSettings | None) -> LLMSettingsResponse:
    if row is None:
        return LLMSettingsResponse(defaults=_server_defaults())
    return LLMSettingsResponse(
        chat_base_url=row.chat_base_url,
        chat_api_key_set=bool(row.chat_api_key),
        chat_model=row.chat_model,
        chat_temperature=row.chat_temperature,
        embedding_base_url=row.embedding_base_url,
        embedding_api_key_set=bool(row.embedding_api_key),
        embedding_model=row.embedding_model,
        image_base_url=row.image_base_url,
        image_api_key_set=bool(row.image_api_key),
        image_model=row.image_model,
        defaults=_server_defaults(),
    )


@router.get("", response_model=LLMSettingsResponse)
def get_llm_settings(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """Get the current user's LLM settings (API keys are masked)."""
    row = db.query(LLMSettings).filter(LLMSettings.user_id == current_user.id).first()
    return _to_response(row)


@router.put("", response_model=LLMSettingsResponse)
def update_llm_settings(
    payload: LLMSettingsUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """Create or update the current user's LLM settings."""
    row = db.query(LLMSettings).filter(LLMSettings.user_id == current_user.id).first()

    if row is None:
        row = LLMSettings(user_id=current_user.id)
        db.add(row)

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(row, field, value if value != "" else None)

    db.commit()
    db.refresh(row)

    logger.info(f"LLM settings updated for user {current_user.id}")
    return _to_response(row)


@router.get("/masked-keys")
def get_masked_keys(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """Return masked API keys for display confirmation."""
    row = db.query(LLMSettings).filter(LLMSettings.user_id == current_user.id).first()
    if row is None:
        return {"chat_api_key": "", "embedding_api_key": "", "image_api_key": ""}
    return {
        "chat_api_key": mask_api_key(row.chat_api_key),
        "embedding_api_key": mask_api_key(row.embedding_api_key),
        "image_api_key": mask_api_key(row.image_api_key),
    }
