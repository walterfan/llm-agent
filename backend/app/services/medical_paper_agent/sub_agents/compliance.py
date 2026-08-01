"""
Compliance Agent — Responsible for reporting guideline compliance checking.

SRP: Only handles CONSORT/STROBE/PRISMA checklist verification and reporting.
"""

import logging
from typing import Any

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from app.services.medical_paper_agent.prompt_loader import get_prompt
from app.services.medical_paper_agent.tools.compliance_tools import (
    check_compliance_prompt,
    generate_compliance_report,
    get_checklist,
)

logger = logging.getLogger("medical_paper_agent")


class CheckComplianceInput(BaseModel):
    manuscript: str = Field(description="The manuscript text to check")
    paper_type: str = Field(description="Paper type: rct, cohort, or meta_analysis")


class GenerateReportInput(BaseModel):
    items: list[dict[str, Any]] = Field(
        description="List of compliance item results with item_id, status, finding"
    )
    checklist_type: str = Field(
        description="Checklist type: CONSORT, STROBE, or PRISMA"
    )


class GetChecklistInput(BaseModel):
    paper_type: str = Field(description="Paper type: rct, cohort, or meta_analysis")


def create_compliance_tools() -> list[StructuredTool]:
    """Create the tool set for the Compliance Agent."""
    tools = [
        StructuredTool.from_function(
            func=lambda manuscript, paper_type: check_compliance_prompt(
                manuscript, paper_type
            ),
            name="check_compliance",
            description="Generate a compliance checking prompt for a manuscript against the appropriate checklist (CONSORT/STROBE/PRISMA).",
            args_schema=CheckComplianceInput,
        ),
        StructuredTool.from_function(
            func=lambda items, checklist_type: generate_compliance_report(
                items, checklist_type
            ),
            name="generate_compliance_report",
            description="Generate a structured compliance report from individual item check results.",
            args_schema=GenerateReportInput,
        ),
        StructuredTool.from_function(
            func=lambda paper_type: get_checklist(paper_type),
            name="get_checklist",
            description="Get the appropriate reporting checklist (CONSORT/STROBE/PRISMA) for a paper type.",
            args_schema=GetChecklistInput,
        ),
    ]
    return tools


def create_compliance_agent(llm: Any) -> Any:
    """Create a LangGraph react agent for compliance checking."""
    from langgraph.prebuilt import create_react_agent

    tools = create_compliance_tools()
    system_prompt = get_prompt(
        "agents/compliance/system.v1.yaml",
        "system",
        paper_type="{paper_type}",
        checklist_type="{checklist_type}",
    )

    return create_react_agent(model=llm, tools=tools, prompt=system_prompt)
