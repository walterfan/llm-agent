"""
Prompt template loader for the Personal Secretary agent.

Prompts are stored in YAML files for easy maintenance and A/B testing.
This module provides utilities to load, cache, and format prompts.
"""

import logging
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

import yaml

logger = logging.getLogger(__name__)

# Directory containing prompt YAML files
PROMPTS_DIR = Path(__file__).parent


class PromptNotFoundError(Exception):
    """Raised when a prompt template is not found."""

    pass


class PromptVariableError(Exception):
    """Raised when required prompt variables are missing."""

    pass


@lru_cache(maxsize=10)
def load_prompt_file(filename: str) -> dict[str, Any]:
    """
    Load and cache a prompt YAML file.

    Args:
        filename: Name of the YAML file (e.g., 'learning_tools.yaml')

    Returns:
        Parsed YAML content as dictionary

    Raises:
        FileNotFoundError: If the file doesn't exist
        yaml.YAMLError: If the file contains invalid YAML
    """
    filepath = PROMPTS_DIR / filename

    if not filepath.exists():
        raise FileNotFoundError(f"Prompt file not found: {filepath}")

    with open(filepath, "r", encoding="utf-8") as f:
        content = yaml.safe_load(f)

    logger.debug(f"Loaded prompt file: {filename}")
    return content


def get_prompt(filename: str, prompt_name: str, **variables: Any) -> str:
    """
    Get a prompt template and fill in variables.

    Args:
        filename: YAML file name (e.g., 'learning_tools.yaml')
        prompt_name: Prompt key (e.g., 'learn_word')
        **variables: Template variables to substitute

    Returns:
        Formatted prompt string

    Raises:
        FileNotFoundError: If the YAML file doesn't exist
        PromptNotFoundError: If the prompt name doesn't exist
        PromptVariableError: If required variables are missing

    Example:
        prompt = get_prompt('learning_tools.yaml', 'learn_word', word='serendipity')
    """
    data = load_prompt_file(filename)

    prompts = data.get("prompts", {})
    if prompt_name not in prompts:
        available = list(prompts.keys())
        raise PromptNotFoundError(
            f"Prompt '{prompt_name}' not found in {filename}. "
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


def get_prompt_metadata(filename: str, prompt_name: str) -> dict[str, Any]:
    """
    Get metadata about a prompt (variables, description, etc.).

    Args:
        filename: YAML file name
        prompt_name: Prompt key

    Returns:
        Dictionary with prompt metadata
    """
    data = load_prompt_file(filename)
    prompts = data.get("prompts", {})

    if prompt_name not in prompts:
        raise PromptNotFoundError(f"Prompt '{prompt_name}' not found in {filename}")

    prompt_config = prompts[prompt_name]
    return {
        "variables": prompt_config.get("variables", []),
        "description": prompt_config.get("description", ""),
    }


def list_prompts(filename: str) -> list[str]:
    """
    List all prompt names in a file.

    Args:
        filename: YAML file name

    Returns:
        List of prompt names
    """
    data = load_prompt_file(filename)
    return list(data.get("prompts", {}).keys())


def reload_prompts() -> None:
    """
    Clear the prompt cache and force reload on next access.

    Useful for development when prompts are being modified,
    or for hot-reloading in production.
    """
    load_prompt_file.cache_clear()
    logger.info("Prompt cache cleared")
