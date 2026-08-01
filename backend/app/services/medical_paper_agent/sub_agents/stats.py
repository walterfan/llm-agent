"""
Stats Agent — Responsible for statistical analysis.

SRP: Only handles statistical tests, sample size calculations, and report generation.
"""

import logging
from typing import Any

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from app.services.medical_paper_agent.prompt_loader import get_prompt
from app.services.medical_paper_agent.tools.stats_tools import (
    TTestInput,
    ChiSquareInput,
    SurvivalInput,
    SampleSizeInput,
    calculate_sample_size,
    generate_stats_report,
    run_chi_square,
    run_survival_analysis,
    run_ttest,
)

logger = logging.getLogger("medical_paper_agent")


def create_stats_tools() -> list[StructuredTool]:
    """Create the tool set for the Stats Agent."""
    tools = [
        StructuredTool.from_function(
            func=lambda group1, group2, paired=False: run_ttest(group1, group2, paired),
            name="run_ttest",
            description="Run an independent or paired t-test. Returns statistic, p-value, CI, and effect size.",
            args_schema=TTestInput,
        ),
        StructuredTool.from_function(
            func=lambda observed: run_chi_square(observed),
            name="run_chi_square",
            description="Run a chi-square test of independence on a contingency table.",
            args_schema=ChiSquareInput,
        ),
        StructuredTool.from_function(
            func=lambda times, events, groups=None: run_survival_analysis(
                times, events, groups
            ),
            name="run_survival_analysis",
            description="Run Kaplan-Meier survival analysis with optional log-rank test.",
            args_schema=SurvivalInput,
        ),
        StructuredTool.from_function(
            func=lambda effect_size, alpha=0.05, power=0.80, test_type="two_sample_ttest": calculate_sample_size(
                effect_size, alpha, power, test_type
            ),
            name="calculate_sample_size",
            description="Calculate required sample size for a given effect size, alpha, and power.",
            args_schema=SampleSizeInput,
        ),
    ]
    return tools


def create_stats_agent(llm: Any) -> Any:
    """Create a LangGraph react agent for statistical analysis."""
    from langgraph.prebuilt import create_react_agent

    tools = create_stats_tools()
    system_prompt = get_prompt(
        "agents/stats/system.v1.yaml",
        "system",
        paper_type="{paper_type}",
        study_design="{study_design}",
        alpha="0.05",
    )

    return create_react_agent(model=llm, tools=tools, prompt=system_prompt)
