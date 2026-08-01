"""
Translation API: POST /translation (JSON URL or multipart file), POST /translation/stream (SSE).
"""

import json
import logging
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse

from app.api.deps import get_current_active_user
from app.core.config import settings
from app.models.user import User
from app.schemas.translation import TranslationResponse
from app.services.translation import (
    TranslationResult,
    TranslationService,
    normalize_input_from_file,
    normalize_input_from_text,
    normalize_input_from_url,
)

logger = logging.getLogger(__name__)

router = APIRouter()

ALLOWED_CONTENT_TYPES = {"application/pdf", "text/plain", "text/markdown"}
OUTPUT_MODES: tuple[str, ...] = ("chinese_only", "bilingual")


def _get_max_file_size() -> int:
    return getattr(settings, "TRANSLATION_MAX_FILE_SIZE_BYTES", 10_485_760)


def _parse_output_mode(mode: str | None) -> str:
    if not mode or mode not in OUTPUT_MODES:
        return "chinese_only"
    return mode


async def _get_source_from_request(request: Request) -> tuple[str, bool, str]:
    """
    Parse request as either JSON (url) or multipart (file). Return (source_text, truncated, output_mode).
    Raises HTTPException 400 if neither/both or invalid.
    """
    content_type = (
        (request.headers.get("content-type") or "").split(";")[0].strip().lower()
    )
    output_mode = "chinese_only"

    if content_type == "application/json":
        body = await request.json()
        if not isinstance(body, dict):
            raise HTTPException(status_code=400, detail="JSON body must be an object.")
        url = body.get("url")
        text = body.get("text")
        output_mode = _parse_output_mode(body.get("output_mode"))
        has_url = url is not None and str(url).strip()
        has_text = text is not None and str(text).strip()
        if has_url and has_text:
            raise HTTPException(
                status_code=400,
                detail="Provide exactly one of 'url' or 'text' in JSON body, not both.",
            )
        if has_text:
            try:
                normalized = normalize_input_from_text(str(text).strip())
            except ValueError as e:
                raise HTTPException(status_code=422, detail=str(e)) from e
            return normalized.source_text, normalized.truncated, output_mode
        if has_url:
            try:
                normalized = await normalize_input_from_url(str(url).strip())
            except ValueError as e:
                raise HTTPException(status_code=422, detail=str(e)) from e
            return normalized.source_text, normalized.truncated, output_mode
        raise HTTPException(
            status_code=400,
            detail="When sending JSON, provide exactly one of 'url' or 'text'. For file upload use multipart form.",
        )

    if content_type.startswith("multipart/form-data"):
        form = await request.form()
        file: UploadFile | None = form.get("file")
        if isinstance(file, list):
            file = file[0] if file else None
        output_mode = _parse_output_mode(
            form.get("output_mode")
            if isinstance(form.get("output_mode"), str)
            else None
        )
        if not file or not file.filename:
            raise HTTPException(
                status_code=400,
                detail="When sending multipart form, provide exactly one 'file' part (PDF, .txt, or .md). URL is not accepted in form.",
            )
        # Read file and check size
        raw = await file.read()
        max_size = _get_max_file_size()
        if len(raw) > max_size:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Maximum size: {max_size} bytes ({max_size // (1024*1024)} MB).",
            )
        ct = (file.content_type or "").split(";")[0].strip().lower()
        if ct in ("text/md", "text/x-markdown"):
            ct = "text/markdown"
        if ct not in ALLOWED_CONTENT_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {file.content_type}. Allowed: {', '.join(sorted(ALLOWED_CONTENT_TYPES))}",
            )
        try:
            normalized = await normalize_input_from_file(
                file_bytes=raw,
                content_type=ct,
                filename=file.filename or "",
            )
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e)) from e
        return normalized.source_text, normalized.truncated, output_mode

    raise HTTPException(
        status_code=400,
        detail="Provide JSON body with 'url' or 'text' (Content-Type: application/json), or multipart form with 'file' (Content-Type: multipart/form-data).",
    )


@router.post("/", response_model=TranslationResponse)
async def translate(
    request: Request,
    current_user: User = Depends(get_current_active_user),
):
    """
    Translate content from URL or uploaded file. Send JSON with `url` or multipart with `file`.
    Returns translated_markdown, explanation, and summary.
    """
    try:
        source_text, source_truncated, output_mode = await _get_source_from_request(
            request
        )
    except HTTPException:
        raise

    if not source_text.strip():
        raise HTTPException(status_code=422, detail="No source text to translate.")

    try:
        service = TranslationService()
        result: TranslationResult = await service.translate(
            source_text=source_text,
            output_mode=output_mode,
            source_truncated=source_truncated,
        )
    except Exception as e:
        logger.exception("Translation failed: %s", e)
        raise HTTPException(
            status_code=500, detail="Translation failed. Please try again."
        ) from e

    return TranslationResponse(
        translated_markdown=result.translated_markdown,
        explanation=result.explanation,
        summary=result.summary,
        source_truncated=result.source_truncated,
    )


@router.post("/stream")
async def translate_stream(
    request: Request,
    current_user: User = Depends(get_current_active_user),
):
    """
    Stream translation: SSE events token, explanation, summary, done.
    Same input as POST / (JSON url or multipart file).
    """
    try:
        source_text, source_truncated, output_mode = await _get_source_from_request(
            request
        )
    except HTTPException:
        raise

    if not source_text.strip():
        raise HTTPException(status_code=422, detail="No source text to translate.")

    async def sse_events():
        try:
            service = TranslationService()
            async for ev in service.translate_stream(
                source_text=source_text,
                output_mode=output_mode,
                source_truncated=source_truncated,
            ):
                yield f"data: {json.dumps(ev)}\n\n"
        except Exception as e:
            logger.exception("Translation stream failed: %s", e)
            yield f"data: {json.dumps({'event': 'error', 'data': str(e)})}\n\n"

    return StreamingResponse(
        sse_events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )
