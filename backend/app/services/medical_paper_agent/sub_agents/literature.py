"""
Literature Agent — Responsible for literature search and reference management.

SRP: Only handles PubMed/ClinicalTrials.gov searches and citation formatting.
"""

import logging
from functools import partial
from typing import Any

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from app.services.medical_paper_agent.prompt_loader import get_prompt
from app.services.medical_paper_agent.tools.literature_tools import (
    format_citation,
    get_article_abstract,
    search_clinicaltrials,
    search_pubmed,
)

logger = logging.getLogger("medical_paper_agent")


class SearchPubMedInput(BaseModel):
    query: str = Field(description="PubMed search query using MeSH terms or keywords")
    max_results: int = Field(default=20, description="Maximum results to return")


class SearchClinicalTrialsInput(BaseModel):
    query: str = Field(description="Search query for ClinicalTrials.gov")
    max_results: int = Field(default=10, description="Maximum results to return")


class GetAbstractInput(BaseModel):
    pmid: str = Field(description="PubMed ID of the article")


class FormatCitationInput(BaseModel):
    reference: dict[str, Any] = Field(
        description="Reference dict with pmid, title, authors, journal, year"
    )
    style: str = Field(
        default="vancouver", description="Citation style: vancouver, apa, ama"
    )


def create_literature_tools() -> list[StructuredTool]:
    """Create the tool set for the Literature Agent."""
    tools = [
        StructuredTool.from_function(
            coroutine=search_pubmed,
            name="search_pubmed",
            description="Search PubMed for medical literature using MeSH terms or keywords. Returns article summaries with PMIDs.",
            args_schema=SearchPubMedInput,
        ),
        StructuredTool.from_function(
            coroutine=search_clinicaltrials,
            name="search_clinicaltrials",
            description="Search ClinicalTrials.gov for registered clinical trials.",
            args_schema=SearchClinicalTrialsInput,
        ),
        StructuredTool.from_function(
            coroutine=get_article_abstract,
            name="get_article_abstract",
            description="Fetch a single article's abstract by PubMed ID (PMID).",
            args_schema=GetAbstractInput,
        ),
        StructuredTool.from_function(
            func=format_citation,
            name="format_citation",
            description="Format a reference in Vancouver, APA, or AMA citation style.",
            args_schema=FormatCitationInput,
        ),
    ]
    return tools


def create_literature_agent(llm: Any) -> Any:
    """
    Create a LangGraph react agent for literature search.

    Uses the literature tools and a system prompt from YAML.
    """
    from langgraph.prebuilt import create_react_agent

    tools = create_literature_tools()
    system_prompt = get_prompt(
        "agents/literature/system.v1.yaml",
        "system",
        paper_type="{paper_type}",
        research_question="{research_question}",
        min_references="10",
        max_references="30",
    )

    return create_react_agent(model=llm, tools=tools, prompt=system_prompt)
