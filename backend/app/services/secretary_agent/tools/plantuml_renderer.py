"""
PlantUML renderer for converting PlantUML scripts to PNG images.

Supports two rendering modes:
1. Local PlantUML jar (if PLANTUML_JAR_PATH is set and jar exists)
2. Remote PlantUML server (default: http://www.plantuml.com/plantuml)

The renderer auto-detects the best available mode.
"""

import hashlib
import logging
import os
import subprocess
import zlib
from pathlib import Path
from typing import Optional

import httpx

from app.core.config import settings

logger = logging.getLogger("secretary_agent")

# ============================================================================
# PlantUML Text Encoding (for server mode)
# ============================================================================

_PLANTUML_ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-_"


def _encode_6bit(value: int) -> str:
    """Encode a 6-bit value to PlantUML alphabet character."""
    if 0 <= value <= 63:
        return _PLANTUML_ALPHABET[value]
    return "?"


def _encode_3bytes(b1: int, b2: int, b3: int) -> str:
    """Encode 3 bytes into 4 PlantUML characters."""
    c1 = b1 >> 2
    c2 = ((b1 & 0x3) << 4) | (b2 >> 4)
    c3 = ((b2 & 0xF) << 2) | (b3 >> 6)
    c4 = b3 & 0x3F
    return _encode_6bit(c1) + _encode_6bit(c2) + _encode_6bit(c3) + _encode_6bit(c4)


def plantuml_text_encode(text: str) -> str:
    """
    Encode PlantUML text for use in server URL.

    Uses deflate compression + custom base64 encoding as specified
    by the PlantUML server protocol.
    """
    data = zlib.compress(text.encode("utf-8"))[2:-4]  # strip zlib header/checksum
    encoded = ""
    i = 0
    while i < len(data):
        if i + 2 < len(data):
            encoded += _encode_3bytes(data[i], data[i + 1], data[i + 2])
        elif i + 1 < len(data):
            encoded += _encode_3bytes(data[i], data[i + 1], 0)
        else:
            encoded += _encode_3bytes(data[i], 0, 0)
        i += 3
    return encoded


# ============================================================================
# Output Directory
# ============================================================================


def _get_output_dir() -> Path:
    """Get or create the output directory for mindmap images."""
    output_dir = Path(getattr(settings, "PLANTUML_OUTPUT_DIR", "static/mindmaps"))
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def _generate_filename(puml_script: str) -> str:
    """Generate a unique filename from the PlantUML script content."""
    content_hash = hashlib.md5(puml_script.encode("utf-8")).hexdigest()[:12]
    return f"mindmap_{content_hash}.png"


# ============================================================================
# Rendering Backends
# ============================================================================


async def render_via_server(
    puml_script: str,
    server_url: Optional[str] = None,
) -> bytes:
    """
    Render PlantUML via remote server.

    Args:
        puml_script: PlantUML source code
        server_url: PlantUML server URL (default from settings or public server)

    Returns:
        PNG image bytes

    Raises:
        RuntimeError: If the server request fails
    """
    base_url = (
        server_url
        or getattr(settings, "PLANTUML_SERVER_URL", None)
        or "http://www.plantuml.com/plantuml"
    )
    encoded = plantuml_text_encode(puml_script)
    url = f"{base_url}/png/{encoded}"

    async with httpx.AsyncClient(
        timeout=httpx.Timeout(30.0),
        verify=getattr(settings, "LLM_VERIFY_SSL", True),
    ) as client:
        response = await client.get(url)
        if response.status_code != 200:
            raise RuntimeError(
                f"PlantUML server returned {response.status_code}: "
                f"{response.text[:200]}"
            )
        content_type = response.headers.get("content-type", "")
        if "image" not in content_type and len(response.content) < 100:
            raise RuntimeError(
                f"PlantUML server returned unexpected content-type: {content_type}"
            )
        return response.content


def render_via_jar(
    puml_script: str,
    jar_path: Optional[str] = None,
) -> bytes:
    """
    Render PlantUML via local jar file.

    Args:
        puml_script: PlantUML source code
        jar_path: Path to plantuml.jar (default from settings)

    Returns:
        PNG image bytes

    Raises:
        FileNotFoundError: If jar not found
        RuntimeError: If rendering fails
    """
    resolved_jar = jar_path or getattr(settings, "PLANTUML_JAR_PATH", None)
    if not resolved_jar or not Path(resolved_jar).exists():
        raise FileNotFoundError(f"PlantUML jar not found at: {resolved_jar}")

    # Write script to temp file
    import tempfile

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".puml", delete=False, encoding="utf-8"
    ) as f:
        f.write(puml_script)
        puml_path = f.name

    try:
        png_path = puml_path.replace(".puml", ".png")

        result = subprocess.run(
            ["java", "-jar", resolved_jar, "-tpng", puml_path],
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode != 0:
            raise RuntimeError(
                f"PlantUML jar failed (exit {result.returncode}): {result.stderr[:500]}"
            )

        if not Path(png_path).exists():
            raise RuntimeError("PlantUML jar did not produce output PNG")

        return Path(png_path).read_bytes()

    finally:
        # Clean up temp files
        for path in [puml_path, puml_path.replace(".puml", ".png")]:
            try:
                os.unlink(path)
            except OSError:
                pass


# ============================================================================
# Public API
# ============================================================================


def _jar_available() -> bool:
    """Check whether a local PlantUML jar is configured and exists."""
    jar_path = getattr(settings, "PLANTUML_JAR_PATH", None)
    return bool(jar_path and Path(jar_path).exists())


async def render_plantuml_to_png(
    puml_script: str,
    filename: Optional[str] = None,
) -> str:
    """
    Render a PlantUML script to PNG and save to the output directory.

    Auto-selects the best rendering backend:
    1. Local jar if available (faster, no network)
    2. Remote server as fallback

    Args:
        puml_script: PlantUML source code
        filename: Optional output filename (auto-generated if not provided)

    Returns:
        Relative path to the saved PNG file (e.g. "static/mindmaps/mindmap_abc123.png")
    """
    output_dir = _get_output_dir()
    fname = filename or _generate_filename(puml_script)
    output_path = output_dir / fname

    # Skip if already rendered (cache by content hash)
    if output_path.exists() and output_path.stat().st_size > 0:
        logger.info(f"PlantUML already rendered: {output_path}")
        return str(output_path)

    # Choose backend
    if _jar_available():
        logger.info("Rendering PlantUML via local jar")
        png_bytes = render_via_jar(puml_script)
    else:
        logger.info("Rendering PlantUML via remote server")
        png_bytes = await render_via_server(puml_script)

    output_path.write_bytes(png_bytes)
    logger.info(f"PlantUML rendered to: {output_path} ({len(png_bytes)} bytes)")
    return str(output_path)
