"""
Writer Agent — Responsible for IMRAD structure paper writing.

SRP: Only handles manuscript section writing and revision.
"""

import logging
from typing import Any

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from app.services.medical_paper_agent.prompt_loader import get_prompt
from app.services.medical_paper_agent.tools.writing_tools import (
    WriteSectionInput,
    ReviseSectionInput,
    MergeSectionsInput,
    merge_sections,
    revise_section_prompt,
    write_section_prompt,
)

logger = logging.getLogger("medical_paper_agent")


def create_writer_tools() -> list[StructuredTool]:
    """Create the tool set for the Writer Agent."""
    tools = [
        StructuredTool.from_function(
            func=lambda section_type, context, word_limit=500: write_section_prompt(
                section_type, context, word_limit
            ),
            name="write_section",
            description="Generate a prompt for writing a manuscript section (introduction, methods, results, discussion, abstract).",
            args_schema=WriteSectionInput,
        ),
        StructuredTool.from_function(
            func=lambda section_type, current_content, feedback: revise_section_prompt(
                section_type, current_content, feedback
            ),
            name="revise_section",
            description="Generate a prompt for revising a manuscript section based on compliance feedback.",
            args_schema=ReviseSectionInput,
        ),
        StructuredTool.from_function(
            func=lambda sections: merge_sections(sections),
            name="merge_sections",
            description="Merge individual manuscript sections into a complete document in IMRAD order.",
            args_schema=MergeSectionsInput,
        ),
    ]
    return tools


def create_writer_agent(llm: Any) -> Any:
    """Create a LangGraph react agent for paper writing."""
    from langgraph.prebuilt import create_react_agent

    tools = create_writer_tools()
    system_prompt = get_prompt(
        "agents/writer/system.v1.yaml",
        "system",
        paper_type="{paper_type}",
        journal_style="general medical",
    )

    return create_react_agent(model=llm, tools=tools, prompt=system_prompt)
