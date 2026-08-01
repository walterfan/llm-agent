"""
Translation agent: normalize URL/file to source text, then LLM translate + explain + summarize.

Reuses article_processor for fetch and PDF/HTML extraction. Enforces configurable
max file size and max source length (truncate with indication).
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any, AsyncIterator

import httpx
from pydantic import BaseModel, Field

from app.core.config import settings
from app.services.secretary_agent.tools.article_processor import (
    CONTENT_TYPE_HTML,
    CONTENT_TYPE_PDF,
    CONTENT_TYPE_PLAIN,
    extract_from_pdf,
    extract_to_markdown,
    fetch_article,
)
from app.services.llm.provider_factory import LLMProviderFactory

logger = logging.getLogger(__name__)

# Allowed upload content types
ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "text/plain",
    "text/markdown",
}

# Default truncation suffix when source exceeds max length
TRUNCATED_SUFFIX = "\n\n（内容已截断，仅翻译前文。）"


@dataclass
class NormalizedInput:
    """Result of normalizing URL or file to source text."""

    source_text: str
    truncated: bool
    title: str = ""


class TranslationResult(BaseModel):
    """Structured translation response."""

    translated_markdown: str = Field(
        description="Translated content (Chinese only or bilingual)"
    )
    explanation: str = Field(description="Key terms and context explanation in Chinese")
    summary: str = Field(description="Concise summary in Chinese")
    source_truncated: bool = Field(
        default=False, description="Whether source was truncated to max length"
    )


def _truncate_source(text: str) -> tuple[str, bool]:
    """Truncate to TRANSLATION_MAX_SOURCE_LENGTH; return (text, was_truncated)."""
    max_len = getattr(settings, "TRANSLATION_MAX_SOURCE_LENGTH", 12_000)
    if len(text) <= max_len:
        return text, False
    return text[:max_len] + TRUNCATED_SUFFIX, True


# PubMed URL patterns: pubmed.ncbi.nlm.nih.gov/PMID or ncbi.nlm.nih.gov/pubmed/PMID
_PUBMED_URL_PATTERN = re.compile(
    r"(?:pubmed\.ncbi\.nlm\.nih\.gov|ncbi\.nlm\.nih\.gov/pubmed)/(\d+)",
    re.IGNORECASE,
)

NCBI_EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"


def _extract_pubmed_pmid(url: str) -> str | None:
    """Extract PubMed ID from a PubMed URL, or return None."""
    match = _PUBMED_URL_PATTERN.search(url)
    return match.group(1) if match else None


async def _fetch_pubmed_abstract(pmid: str) -> tuple[str, str]:
    """
    Fetch article abstract from PubMed via NCBI E-utilities.
    Returns (title, abstract_text). Raises ValueError on failure.
    """
    params = {
        "db": "pubmed",
        "id": pmid,
        "rettype": "abstract",
        "retmode": "text",
    }
    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(15.0),
            follow_redirects=True,
            verify=getattr(settings, "LLM_VERIFY_SSL", True),
        ) as client:
            response = await client.get(NCBI_EFETCH_URL, params=params)
            response.raise_for_status()
    except httpx.HTTPStatusError as e:
        raise ValueError(
            f"PubMed API returned HTTP {e.response.status_code} for PMID {pmid}."
        ) from e
    except httpx.RequestError as e:
        raise ValueError(f"Failed to fetch from PubMed: {e}") from e

    text = response.text.strip()
    if not text:
        raise ValueError(f"No abstract found for PubMed ID {pmid}.")

    # efetch rettype=abstract retmode=text returns citation, title, authors, abstract
    return f"PubMed {pmid}", text


async def normalize_input_from_url(url: str) -> NormalizedInput:
    """
    Fetch URL, extract content (HTML or PDF), return source text.
    For PubMed URLs, uses NCBI E-utilities to fetch the abstract (avoids 403 from HTML page).
    Enforces TRANSLATION_MAX_SOURCE_LENGTH (truncates and marks).
    """
    pmid = _extract_pubmed_pmid(url)
    if pmid:
        try:
            title, abstract = await _fetch_pubmed_abstract(pmid)
            content = f"{title}\n\n{abstract}".strip()
            if not content:
                raise ValueError("PubMed returned no content.")
            source_text, truncated = _truncate_source(content)
            return NormalizedInput(
                source_text=source_text, truncated=truncated, title=title
            )
        except ValueError as e:
            logger.info(
                "PubMed efetch failed (%s), falling back to fetch_article: %s", pmid, e
            )
            # Fall through to normal fetch (may still 403)

    fetch_result = await fetch_article(url=url)
    if fetch_result.content_type == CONTENT_TYPE_PDF:
        assert isinstance(fetch_result.body, bytes)
        extracted = await extract_from_pdf(
            pdf_bytes=fetch_result.body,
            url=fetch_result.final_url,
        )
    elif fetch_result.content_type == CONTENT_TYPE_PLAIN:
        assert isinstance(fetch_result.body, str)
        content = fetch_result.body.strip()
        if not content:
            raise ValueError("URL returned empty text.")
        title = "Untitled"
        source_text, truncated = _truncate_source(content)
        return NormalizedInput(
            source_text=source_text, truncated=truncated, title=title
        )
    else:
        assert isinstance(fetch_result.body, str)
        extracted = await extract_to_markdown(
            html=fetch_result.body,
            url=fetch_result.final_url,
        )
    title = extracted.get("title") or "Untitled"
    content = extracted.get("content", "").strip()
    if not content:
        raise ValueError("No text could be extracted from the URL.")
    source_text, truncated = _truncate_source(content)
    return NormalizedInput(source_text=source_text, truncated=truncated, title=title)


def normalize_input_from_text(text: str) -> NormalizedInput:
    """
    Use pasted text as source. Enforces TRANSLATION_MAX_SOURCE_LENGTH (truncates and marks).
    """
    content = (text or "").strip()
    if not content:
        raise ValueError("Pasted text is empty.")
    source_text, truncated = _truncate_source(content)
    return NormalizedInput(
        source_text=source_text, truncated=truncated, title="Pasted text"
    )


async def normalize_input_from_file(
    file_bytes: bytes,
    content_type: str,
    filename: str = "",
) -> NormalizedInput:
    """
    Extract source text from uploaded file (PDF, text/plain, text/markdown).
    Enforces TRANSLATION_MAX_SOURCE_LENGTH (truncates and marks).
    """
    ct = (content_type or "").split(";")[0].strip().lower()
    # Normalize common aliases
    if ct in ("text/md", "text/x-markdown") or (
        filename and filename.lower().endswith(".md")
    ):
        ct = "text/markdown"
    if ct not in ALLOWED_CONTENT_TYPES:
        raise ValueError(
            f"Unsupported file type: {content_type}. "
            f"Allowed: {', '.join(sorted(ALLOWED_CONTENT_TYPES))}"
        )

    if ct == CONTENT_TYPE_PDF:
        extracted = await extract_from_pdf(pdf_bytes=file_bytes, url=filename or None)
        title = extracted.get("title") or "Uploaded PDF"
        content = extracted.get("content", "").strip()
    else:
        try:
            content = file_bytes.decode("utf-8").strip()
        except UnicodeDecodeError as e:
            raise ValueError(f"File must be UTF-8 text: {e}") from e
        title = "Uploaded text"

    if not content:
        raise ValueError("File contains no extractable text.")
    source_text, truncated = _truncate_source(content)
    return NormalizedInput(source_text=source_text, truncated=truncated, title=title)


def _translation_prompt(source_text: str, output_mode: str) -> str:
    """Build prompt for full translation (chinese_only or bilingual)."""
    mode_instruction = (
        "Output only the Chinese translation, preserving markdown structure."
        if output_mode == "chinese_only"
        else (
            "For each paragraph or segment, output the original English first, "
            "then a blank line, then the Chinese translation in a blockquote (e.g. '> 中文'). "
            "Preserve markdown structure. Output format: English paragraph, blank line, '> Chinese translation'."
        )
    )
    return f"""Translate the following English text to Chinese.

{mode_instruction}

English text:
---
{source_text}
---
"""


def _explanation_prompt(translated_markdown: str) -> str:
    """Prompt for key terms and context explanation."""
    excerpt = translated_markdown[:3000] + (
        "..." if len(translated_markdown) > 3000 else ""
    )
    return f"""Based on the following Chinese text (translation of an English source), provide a brief explanation of key terms, concepts, or context that would help a reader understand the content. Write in Chinese. Output only the explanation, no preamble.

---
{excerpt}
---
"""


def _summary_prompt(translated_markdown: str) -> str:
    """Prompt for concise summary."""
    excerpt = translated_markdown[:4000] + (
        "..." if len(translated_markdown) > 4000 else ""
    )
    return f"""Summarize the following Chinese text in 3–5 sentences. Write the summary in Chinese. Output only the summary, no preamble.

---
{excerpt}
---
"""


class TranslationService:
    """Orchestrates translation, explanation, and summary using the configured LLM."""

    def __init__(self) -> None:
        self._provider = LLMProviderFactory.get_provider(
            provider_type=getattr(settings, "LLM_PROVIDER", "openai"),
            base_url=settings.LLM_BASE_URL,
            api_key=settings.LLM_API_KEY,
            model=settings.LLM_MODEL,
            verify_ssl=getattr(settings, "LLM_VERIFY_SSL", True),
            timeout=int(getattr(settings, "LLM_TIMEOUT", 30)),
        )

    async def translate(
        self,
        source_text: str,
        output_mode: str = "chinese_only",
        source_truncated: bool = False,
    ) -> TranslationResult:
        """
        Non-streaming: translate source text, then generate explanation and summary.
        Implemented by consuming translate_stream to avoid forcing JSON for long translation.
        """
        translated_markdown = ""
        explanation = ""
        summary = ""
        async for ev in self.translate_stream(
            source_text, output_mode=output_mode, source_truncated=source_truncated
        ):
            if ev.get("event") == "token":
                translated_markdown += ev.get("data", "")
            elif ev.get("event") == "explanation_token":
                explanation += ev.get("data", "")
            elif ev.get("event") == "summary_token":
                summary += ev.get("data", "")
        return TranslationResult(
            translated_markdown=translated_markdown.strip(),
            explanation=explanation,
            summary=summary,
            source_truncated=source_truncated,
        )

    async def translate_stream(
        self,
        source_text: str,
        output_mode: str = "chinese_only",
        source_truncated: bool = False,
    ) -> AsyncIterator[dict[str, Any]]:
        """
        Stream translation, then explanation, then summary token-by-token; then done.
        Event dicts: {"event": "token", "data": "..."} | {"event": "explanation_token", "data": "..."} | {"event": "summary_token", "data": "..."} | {"event": "done"}.
        """
        prompt = _translation_prompt(source_text, output_mode)
        full_translation: list[str] = []
        async for token in self._provider.generate_completion_stream(
            prompt,
            temperature=0.3,
            max_tokens=4096,
        ):
            full_translation.append(token)
            yield {"event": "token", "data": token}

        translated_markdown = "".join(full_translation).strip()

        # Explanation: stream tokens, then send full text so client always gets content
        expl_prompt = _explanation_prompt(translated_markdown)
        expl_chunks: list[str] = []
        async for t in self._provider.generate_completion_stream(
            expl_prompt, temperature=0.3, max_tokens=1024
        ):
            expl_chunks.append(t)
            yield {"event": "explanation_token", "data": t}
        explanation = "".join(expl_chunks).strip()
        yield {"event": "explanation", "data": explanation}

        # Summary: stream tokens, then send full text
        sum_prompt = _summary_prompt(translated_markdown)
        sum_chunks: list[str] = []
        async for t in self._provider.generate_completion_stream(
            sum_prompt, temperature=0.3, max_tokens=512
        ):
            sum_chunks.append(t)
            yield {"event": "summary_token", "data": t}
        summary = "".join(sum_chunks).strip()
        yield {"event": "summary", "data": summary}

        yield {"event": "done", "source_truncated": source_truncated}
