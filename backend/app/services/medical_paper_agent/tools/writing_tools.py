"""
Writing tools for the Writer Agent.

Provides section writing, revision, and merging capabilities
for IMRAD-structured medical papers.
"""

import logging
from typing import Any, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger("medical_paper_agent")


class WriteSectionInput(BaseModel):
    section_type: str = Field(
        description="Section type: introduction, methods, results, discussion, abstract"
    )
    context: dict[str, Any] = Field(
        description="Context including references, stats, study design"
    )
    word_limit: int = Field(
        default=500, description="Approximate word limit for the section"
    )


class ReviseSectionInput(BaseModel):
    section_type: str = Field(description="Section type to revise")
    current_content: str = Field(description="Current section content")
    feedback: str = Field(description="Revision feedback from compliance or reviewer")


class MergeSectionsInput(BaseModel):
    sections: dict[str, str] = Field(description="Dict of section_type -> content")


SECTION_ORDER = ["abstract", "introduction", "methods", "results", "discussion"]


def write_section_prompt(
    section_type: str,
    context: dict[str, Any],
    word_limit: int = 500,
) -> str:
    """
    Generate the prompt for writing a manuscript section.

    This returns the prompt text; the actual LLM call is done by the agent.
    """
    paper_type = context.get("paper_type", "rct")
    research_question = context.get("research_question", "")
    references = context.get("references", "")
    stats_report = context.get("stats_report", "")
    study_design = context.get("study_design", "")

    prompts = {
        "introduction": f"""Write the Introduction section for a {paper_type} paper.
Research Question: {research_question}
References: {references}
Structure: Background → Literature Review → Gap → Objective
Word limit: {word_limit} words. Cite references as [Author, Year].""",
        "methods": f"""Write the Methods section for a {paper_type} paper.
Study Design: {study_design}
Statistical Plan: {stats_report}
Structure: Design → Participants → Interventions → Outcomes → Statistics
Word limit: {word_limit} words. Use past tense.""",
        "results": f"""Write the Results section for a {paper_type} paper.
Statistical Results: {stats_report}
Study Design: {study_design}
Structure: Participant Flow → Baseline → Primary Outcome → Secondary → Adverse Events
Word limit: {word_limit} words. Report exact p-values and CIs.""",
        "discussion": f"""Write the Discussion section for a {paper_type} paper.
Research Question: {research_question}
Key Results: {stats_report}
References: {references}
Structure: Summary → Interpretation → Comparison → Strengths → Limitations → Implications
Word limit: {word_limit} words.""",
        "abstract": f"""Write a structured abstract for a {paper_type} paper.
Research Question: {research_question}
Methods: {study_design}
Results: {stats_report}
Sections: Background, Methods, Results, Conclusions
Word limit: {word_limit} words.""",
    }

    return prompts.get(
        section_type, f"Write the {section_type} section. Word limit: {word_limit}"
    )


def revise_section_prompt(
    section_type: str,
    current_content: str,
    feedback: str,
) -> str:
    """Generate the prompt for revising a manuscript section based on feedback."""
    return f"""Revise the {section_type} section based on the following feedback.

Current Content:
{current_content}

Feedback/Issues to Address:
{feedback}

Requirements:
- Address ALL feedback points
- Maintain academic tone and style
- Keep the same overall structure unless feedback requires restructuring
- Preserve citations and references
- Mark significant changes with [REVISED] comments"""


def merge_sections(sections: dict[str, str]) -> dict[str, Any]:
    """
    Merge individual sections into a complete manuscript.

    Ensures proper ordering and adds transition markers.
    """
    ordered_sections = []
    total_words = 0

    for section_type in SECTION_ORDER:
        content = sections.get(section_type, "")
        if content:
            word_count = len(content.split())
            total_words += word_count
            ordered_sections.append(
                {
                    "section_type": section_type,
                    "title": section_type.replace("_", " ").title(),
                    "content": content,
                    "word_count": word_count,
                }
            )

    return {
        "sections": ordered_sections,
        "total_word_count": total_words,
        "section_count": len(ordered_sections),
    }
