"""
Article processing pipeline for the Personal Secretary agent.

Pipeline: URL → Fetch → Markdown (or PDF text) → Bilingual Translation → Summary → Mindmap → PNG

Handles:
- Plain HTML: trafilatura extraction.
- PDF: pypdf text extraction (URL or Content-Type application/pdf).
- JS-rendered / login-required: clear error messages and workaround suggestions.

Each step is independently testable and traced for observability.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Any, Optional

import httpx
import trafilatura
from pydantic import BaseModel, Field

from app.core.config import settings
from app.services.secretary_agent.prompts import get_prompt
from app.services.secretary_agent.tracing import trace_llm_call, trace_tool_call
from app.services.secretary_agent.tools.plantuml_renderer import render_plantuml_to_png

logger = logging.getLogger("secretary_agent")


# ============================================================================
# Input / Output Schemas
# ============================================================================


class LearnArticleInput(BaseModel):
    """Input schema for learn_article tool."""

    url: str = Field(description="URL of the article to learn from")


class ArticleSummary(BaseModel):
    """Structured summary output from LLM."""

    summary: str = Field(description="3-5 sentence summary in Chinese")
    key_points: list[str] = Field(description="Main takeaways in Chinese")
    tags: list[str] = Field(description="Auto-generated topic tags")


# ============================================================================
# Step 1: Fetch Article
# ============================================================================

# Content types we handle
CONTENT_TYPE_HTML = "text/html"
CONTENT_TYPE_PDF = "application/pdf"
CONTENT_TYPE_PLAIN = "text/plain"  # raw text or markdown (e.g. raw GitHub files)

# URL suffix hint for PDF when server doesn't send correct Content-Type
PDF_URL_SUFFIXES = (".pdf", ".PDF")


@dataclass(frozen=True)
class FetchResult:
    """Result of fetching a URL: content type and raw body."""

    content_type: (
        str  # "text/html", "application/pdf", or "text/plain" (raw text/markdown)
    )
    body: str | bytes  # str for HTML or plain text, bytes for PDF
    final_url: str


def _is_pdf_url(url: str) -> bool:
    """Return True if URL looks like a PDF (by path)."""
    return url.rstrip("/").split("?")[0].endswith(PDF_URL_SUFFIXES)


def _content_type_from_response(response: httpx.Response, url: str) -> str:
    """Determine content type from response or URL."""
    ct = response.headers.get("content-type", "").split(";")[0].strip().lower()
    if "pdf" in ct or _is_pdf_url(url):
        return CONTENT_TYPE_PDF
    if ct in ("text/plain", "text/markdown") or "text/markdown" in ct:
        return CONTENT_TYPE_PLAIN
    return CONTENT_TYPE_HTML


@trace_tool_call
async def fetch_article(url: str) -> FetchResult:
    """
    Fetch article content from a URL.

    Detects HTML vs PDF by Content-Type or URL path. Uses a browser-like
    User-Agent and redirect following. For 401/403, raises with a hint that
    the page may require login.

    Args:
        url: The article URL to fetch

    Returns:
        FetchResult with content_type ("text/html", "application/pdf", or "text/plain")
        and body (str for HTML/plain, bytes for PDF)

    Raises:
        ValueError: If the URL is invalid, unreachable, or requires login
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": (
            "text/html,application/xhtml+xml,application/xml;q=0.9,"
            "application/pdf;q=0.8,*/*;q=0.7"
        ),
        "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
    }

    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(30.0),
            follow_redirects=True,
            verify=getattr(settings, "LLM_VERIFY_SSL", True),
        ) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()

            content_type = _content_type_from_response(response, str(response.url))
            final_url = str(response.url)

            if content_type == CONTENT_TYPE_PDF:
                return FetchResult(
                    content_type=CONTENT_TYPE_PDF,
                    body=response.content,
                    final_url=final_url,
                )
            if content_type == CONTENT_TYPE_PLAIN:
                return FetchResult(
                    content_type=CONTENT_TYPE_PLAIN,
                    body=response.text,
                    final_url=final_url,
                )
            return FetchResult(
                content_type=CONTENT_TYPE_HTML,
                body=response.text,
                final_url=final_url,
            )
    except httpx.TimeoutException:
        raise ValueError(
            f"Timeout fetching article: {url}. "
            "The site may be slow or blocking automated requests."
        )
    except httpx.HTTPStatusError as exc:
        code = exc.response.status_code
        if code in (401, 403):
            raise ValueError(
                f"This URL may require login (HTTP {code}). "
                "Try opening it in a browser, then copy the article text and paste it here, "
                "or save the page as PDF and share the PDF link if supported."
            )
        raise ValueError(f"HTTP {code} fetching article: {url}")
    except httpx.RequestError as exc:
        raise ValueError(f"Error fetching article ({type(exc).__name__}): {url}")


# ============================================================================
# Step 2: Extract to Markdown (HTML) or Text (PDF)
# ============================================================================

# Message when HTML extraction yields no main content (JS-rendered, paywall, etc.)
_EXTRACT_EMPTY_MSG = (
    "Could not extract main content from this page. Common causes: "
    "(1) The page is rendered by JavaScript — try saving as PDF or copying the article text and pasting it here; "
    "(2) The page requires login or a subscription; "
    "(3) The URL is not an article page (e.g. a hub or redirect). "
    "For PDFs, use a direct .pdf link."
)


@trace_tool_call
async def extract_to_markdown(html: str, url: Optional[str] = None) -> dict[str, Any]:
    """
    Extract the main content from HTML and convert to clean markdown.

    Uses trafilatura to remove navigation, ads, footers, etc.
    Returns the markdown content along with metadata.
    Fails with a clear message if the page is JS-rendered or login-required.

    Args:
        html: Raw HTML content
        url: Original URL (helps trafilatura resolve relative links)

    Returns:
        Dictionary with keys: title, author, date, content, word_count
    """
    # Extract main content as markdown
    content = trafilatura.extract(
        html,
        url=url,
        include_links=True,
        include_images=False,
        include_tables=True,
        output_format="txt",  # plain text with structure
        favor_recall=True,
    )

    if not content or not content.strip():
        raise ValueError(_EXTRACT_EMPTY_MSG)

    # Extract metadata
    metadata = trafilatura.extract_metadata(html, default_url=url)

    title = ""
    author = None
    date = None
    if metadata:
        title = getattr(metadata, "title", "") or ""
        author = getattr(metadata, "author", None)
        date = getattr(metadata, "date", None)

    # Estimate word count
    word_count = len(content.split())

    return {
        "title": title,
        "author": author,
        "date": date,
        "content": content,
        "word_count": word_count,
    }


@trace_tool_call
async def extract_from_pdf(
    pdf_bytes: bytes, url: Optional[str] = None
) -> dict[str, Any]:
    """
    Extract text from a PDF document.

    Uses pypdf to get page text. Metadata (title, author, date) is read from
    the PDF when available. Returns the same shape as extract_to_markdown
    for use in the rest of the pipeline.

    Args:
        pdf_bytes: Raw PDF bytes
        url: Original URL (for logging)

    Returns:
        Dictionary with keys: title, author, date, content, word_count
    """
    from pypdf import PdfReader
    from io import BytesIO

    try:
        reader = PdfReader(BytesIO(pdf_bytes))
    except Exception as e:
        raise ValueError(f"Invalid or corrupted PDF: {e}") from e

    text_parts: list[str] = []
    for page in reader.pages:
        t = page.extract_text()
        if t:
            text_parts.append(t)

    content = "\n\n".join(text_parts).strip()
    if not content:
        raise ValueError(
            "No text could be extracted from the PDF (it may be scanned images). "
            "Use an OCR tool or paste the article text instead."
        )

    metadata = reader.metadata
    title = (metadata and metadata.get("/Title")) or ""
    if title and isinstance(title, bytes):
        try:
            title = title.decode("utf-8", errors="replace")
        except Exception:
            title = ""
    author = None
    date = None
    if metadata:
        author = metadata.get("/Author")
        if author and isinstance(author, bytes):
            try:
                author = author.decode("utf-8", errors="replace")
            except Exception:
                author = None
        # /CreationDate or /ModDate often in D:... format
        date = metadata.get("/CreationDate") or metadata.get("/ModDate")

    word_count = len(content.split())

    return {
        "title": title or "Untitled PDF",
        "author": author,
        "date": date,
        "content": content,
        "word_count": word_count,
    }


# ============================================================================
# Step 3: Bilingual Translation
# ============================================================================


def _split_paragraphs(text: str) -> list[str]:
    """Split text into paragraphs, preserving code blocks."""
    paragraphs: list[str] = []
    current: list[str] = []
    in_code_block = False

    for line in text.split("\n"):
        stripped = line.strip()

        # Track code block boundaries
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            current.append(line)
            if not in_code_block:
                # End of code block — flush
                paragraphs.append("\n".join(current))
                current = []
            continue

        if in_code_block:
            current.append(line)
            continue

        if stripped == "":
            if current:
                paragraphs.append("\n".join(current))
                current = []
        else:
            current.append(line)

    if current:
        paragraphs.append("\n".join(current))

    return paragraphs


def _is_code_block(paragraph: str) -> bool:
    """Return True if the paragraph is a fenced code block."""
    stripped = paragraph.strip()
    return stripped.startswith("```") and stripped.endswith("```")


def _is_heading(paragraph: str) -> bool:
    """Return True if the paragraph is a markdown heading."""
    return paragraph.strip().startswith("#")


@trace_tool_call
async def translate_bilingual(
    content: str,
    llm_call_fn: Any = None,
) -> str:
    """
    Create a bilingual (English + Chinese) version of the article.

    Translates paragraph by paragraph, keeping the original English
    followed by the Chinese translation. Code blocks and headings
    are preserved without translation.

    Args:
        content: Original article content (markdown/text)
        llm_call_fn: Async function to call LLM for translation

    Returns:
        Bilingual content with English paragraphs followed by Chinese translations
    """
    if llm_call_fn is None:
        raise ValueError("llm_call_fn is required for translation")

    paragraphs = _split_paragraphs(content)
    bilingual_parts: list[str] = []

    for paragraph in paragraphs:
        # Don't translate code blocks, headings, or very short text
        if _is_code_block(paragraph) or len(paragraph.strip()) < 10:
            bilingual_parts.append(paragraph)
            continue

        if _is_heading(paragraph):
            # Translate headings inline: ## Title → ## Title / 标题
            prompt = get_prompt(
                "article_tools.yaml",
                "translate_paragraph",
                paragraph=paragraph.lstrip("#").strip(),
            )
            translation = await llm_call_fn(prompt)
            bilingual_parts.append(f"{paragraph} / {translation.strip()}")
            continue

        # Regular paragraph: keep English, add Chinese below
        prompt = get_prompt(
            "article_tools.yaml",
            "translate_paragraph",
            paragraph=paragraph,
        )
        translation = await llm_call_fn(prompt)
        bilingual_parts.append(paragraph)
        bilingual_parts.append(f"> {translation.strip()}")
        bilingual_parts.append("")  # blank line separator

    return "\n\n".join(bilingual_parts)


# ============================================================================
# Step 4: Generate Summary
# ============================================================================


@trace_tool_call
async def generate_summary(
    title: str,
    content: str,
    llm_call_fn: Any = None,
) -> ArticleSummary:
    """
    Generate a structured summary of the article using LLM.

    Args:
        title: Article title
        content: Article content (first ~4000 chars used)
        llm_call_fn: Async function to call LLM

    Returns:
        ArticleSummary with summary, key_points, and tags
    """
    if llm_call_fn is None:
        raise ValueError("llm_call_fn is required for summarization")

    # Truncate content to avoid token limits
    truncated = content[:4000]
    if len(content) > 4000:
        truncated += "\n\n... (content truncated)"

    prompt = get_prompt(
        "article_tools.yaml",
        "generate_summary",
        title=title,
        content=truncated,
    )
    raw_response = await llm_call_fn(prompt)

    # Parse JSON from response
    try:
        # Try to extract JSON from the response
        json_match = re.search(r"\{.*\}", raw_response, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group())
        else:
            data = json.loads(raw_response)
        return ArticleSummary(**data)
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        logger.warning(f"Failed to parse summary JSON: {exc}. Using fallback.")
        return ArticleSummary(
            summary=raw_response[:500],
            key_points=[raw_response[:200]],
            tags=[],
        )


# ============================================================================
# Step 5: Generate Mindmap PlantUML
# ============================================================================


def _extract_headings(content: str) -> str:
    """Extract heading lines from markdown content for mindmap structure."""
    headings: list[str] = []
    for line in content.split("\n"):
        stripped = line.strip()
        if stripped.startswith("#"):
            headings.append(stripped)
    return "\n".join(headings) if headings else "(no headings found)"


@trace_tool_call
async def generate_mindmap_plantuml(
    title: str,
    key_points: list[str],
    content: str,
    llm_call_fn: Any = None,
) -> str:
    """
    Generate a PlantUML mindmap script from article content.

    Args:
        title: Article title
        key_points: Key points from summary
        content: Article content (for heading extraction)
        llm_call_fn: Async function to call LLM

    Returns:
        PlantUML mindmap script string
    """
    if llm_call_fn is None:
        raise ValueError("llm_call_fn is required for mindmap generation")

    headings = _extract_headings(content)
    key_points_text = "\n".join(f"- {kp}" for kp in key_points)

    prompt = get_prompt(
        "article_tools.yaml",
        "generate_mindmap",
        title=title,
        key_points=key_points_text,
        headings=headings,
    )
    raw = await llm_call_fn(prompt)

    # Clean up: ensure proper start/end tags
    cleaned = raw.strip()

    # Remove markdown code fences if LLM wraps the output
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        # Remove first and last lines (``` markers)
        lines = [l for l in lines if not l.strip().startswith("```")]
        cleaned = "\n".join(lines).strip()

    if not cleaned.startswith("@startmindmap"):
        cleaned = "@startmindmap\n" + cleaned
    if not cleaned.endswith("@endmindmap"):
        cleaned = cleaned + "\n@endmindmap"

    return cleaned


# ============================================================================
# Full Pipeline: learn_article tool
# ============================================================================


@trace_tool_call
async def learn_article(url: str) -> str:
    """
    Process an article URL through the full learning pipeline.

    Pipeline:
    1. Fetch article from URL
    2. Extract to clean markdown
    3. Translate to bilingual (English + Chinese)
    4. Generate summary with key points
    5. Generate PlantUML mindmap
    6. Render mindmap to PNG

    Args:
        url: The article URL

    Returns:
        JSON string with the full ArticleResponse
    """
    from app.services.secretary_agent.tools.learning_tools import ArticleResponse

    # Create LLM call function
    llm_fn = _create_llm_call_fn()

    # Step 1: Fetch (detects HTML vs PDF)
    logger.info(f"[Article] Step 1: Fetching {url}")
    fetch_result = await fetch_article(url=url)

    # Step 2: Extract (HTML → trafilatura, PDF → pypdf, plain text/markdown → use as-is)
    logger.info("[Article] Step 2: Extracting content")
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
        extracted = {
            "title": "Untitled",
            "author": None,
            "date": None,
            "content": content,
            "word_count": len(content.split()),
        }
    else:
        assert isinstance(fetch_result.body, str)
        extracted = await extract_to_markdown(
            html=fetch_result.body,
            url=fetch_result.final_url,
        )

    title = extracted["title"] or "Untitled Article"
    content = extracted["content"]

    # Step 3: Translate
    logger.info("[Article] Step 3: Translating to bilingual")
    bilingual = await translate_bilingual(content=content, llm_call_fn=llm_fn)

    # Step 4: Summarize
    logger.info("[Article] Step 4: Generating summary")
    summary = await generate_summary(title=title, content=content, llm_call_fn=llm_fn)

    # Step 5: Generate mindmap
    logger.info("[Article] Step 5: Generating mindmap PlantUML")
    puml_script = await generate_mindmap_plantuml(
        title=title,
        key_points=summary.key_points,
        content=content,
        llm_call_fn=llm_fn,
    )

    # Step 6: Render mindmap
    logger.info("[Article] Step 6: Rendering mindmap to PNG")
    try:
        image_path = await render_plantuml_to_png(puml_script)
    except Exception as exc:
        logger.warning(f"Failed to render mindmap PNG: {exc}")
        image_path = None

    # Estimate reading time (~200 words per minute)
    word_count = extracted["word_count"]
    reading_minutes = max(1, word_count // 200)
    reading_time = f"~{reading_minutes} min"

    # Build response
    response = ArticleResponse(
        url=url,
        title=title,
        author=extracted.get("author"),
        published_date=extracted.get("date"),
        original_markdown=content,
        bilingual_content=bilingual,
        summary=summary.summary,
        key_points=summary.key_points,
        mindmap_plantuml=puml_script,
        mindmap_image_path=image_path,
        word_count=word_count,
        reading_time=reading_time,
        language="en",  # Assumed English input
        tags=summary.tags,
    )

    return response.model_dump_json(indent=2)


# ============================================================================
# LLM Call Helper
# ============================================================================


@trace_llm_call(prompt_template="article_tools")
async def _call_llm(prompt: str) -> str:
    """
    Call the configured LLM with a prompt and return the text response.

    Uses the OpenAI-compatible API via httpx. Respects LLM_VERIFY_SSL
    for self-hosted models with self-signed certificates.
    """
    from openai import AsyncOpenAI

    client = AsyncOpenAI(
        api_key=settings.LLM_API_KEY,
        base_url=settings.LLM_BASE_URL,
        http_client=httpx.AsyncClient(
            verify=getattr(settings, "LLM_VERIFY_SSL", True),
            timeout=httpx.Timeout(60.0),
        ),
    )

    response = await client.chat.completions.create(
        model=settings.LLM_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=2000,
    )

    return response.choices[0].message.content or ""


def _create_llm_call_fn():
    """Return the default LLM call function."""
    return _call_llm
