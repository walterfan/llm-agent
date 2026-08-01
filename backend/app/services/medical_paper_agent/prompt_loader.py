"""
Prompt template loader for the Medical Paper Agent.

Loads versioned YAML prompts from a hierarchical directory structure.
Supports Jinja2-style variable substitution and caching.
"""

import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger("medical_paper_agent")

PROMPTS_DIR = Path(__file__).parent / "prompts"


class PromptNotFoundError(Exception):
    """Raised when a prompt template is not found."""

    pass


class PromptVariableError(Exception):
    """Raised when required prompt variables are missing."""

    pass


@lru_cache(maxsize=50)
def load_prompt_file(relative_path: str) -> dict[str, Any]:
    """
    Load and cache a prompt YAML file.

    Args:
        relative_path: Path relative to prompts/ directory
            e.g., 'supervisor/router.v1.yaml' or 'agents/writer/system.v1.yaml'

    Returns:
        Parsed YAML content as dictionary
    """
    filepath = PROMPTS_DIR / relative_path

    if not filepath.exists():
        raise FileNotFoundError(f"Prompt file not found: {filepath}")

    with open(filepath, "r", encoding="utf-8") as f:
        content = yaml.safe_load(f)

    logger.debug(f"Loaded prompt file: {relative_path}")
    return content


def get_prompt(
    relative_path: str,
    prompt_name: str,
    **variables: Any,
) -> str:
    """
    Get a prompt template and fill in variables.

    Args:
        relative_path: Path relative to prompts/ directory
        prompt_name: Prompt key within the YAML file
        **variables: Template variables to substitute

    Returns:
        Formatted prompt string

    Example:
        prompt = get_prompt(
            'agents/writer/introduction.v1.yaml',
            'write_introduction',
            paper_type='rct',
            research_question='Does Drug X improve...?',
            references='[1] Smith 2024...',
            word_limit=500,
        )
    """
    data = load_prompt_file(relative_path)

    prompts = data.get("prompts", {})
    if prompt_name not in prompts:
        available = list(prompts.keys())
        raise PromptNotFoundError(
            f"Prompt '{prompt_name}' not found in {relative_path}. "
            f"Available prompts: {available}"
        )

    prompt_config = prompts[prompt_name]
    template = prompt_config.get("template", "")

    # Check for required variables
    required_vars = prompt_config.get("variables", [])
    missing_vars = [v for v in required_vars if v not in variables]
    if missing_vars:
        raise PromptVariableError(
            f"Missing required variables for '{prompt_name}': {missing_vars}"
        )

    try:
        return template.format(**variables)
    except KeyError as e:
        raise PromptVariableError(f"Missing variable in template: {e}")


def list_prompts(relative_path: str) -> list[str]:
    """List all prompt names in a YAML file."""
    data = load_prompt_file(relative_path)
    return list(data.get("prompts", {}).keys())


def reload_prompts() -> None:
    """Clear the prompt cache for hot-reload."""
    load_prompt_file.cache_clear()
    logger.info("Medical paper prompt cache cleared")
