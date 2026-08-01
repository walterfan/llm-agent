"""
Compliance checking tools for the Compliance Agent.

Checks manuscripts against CONSORT, STROBE, and PRISMA reporting checklists.
"""

import logging
from typing import Any, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger("medical_paper_agent")


# CONSORT 2010 checklist items (25 items for RCT)
CONSORT_ITEMS = [
    ("1a", "Identification as a randomised trial in the title"),
    ("1b", "Structured summary of trial design, methods, results, and conclusions"),
    ("2a", "Scientific background and explanation of rationale"),
    ("2b", "Specific objectives or hypotheses"),
    ("3a", "Description of trial design including allocation ratio"),
    ("3b", "Important changes to methods after trial commencement, with reasons"),
    ("4a", "Eligibility criteria for participants"),
    ("4b", "Settings and locations where the data were collected"),
    ("5", "Interventions for each group with sufficient details"),
    ("6a", "Completely defined pre-specified primary and secondary outcome measures"),
    ("6b", "Any changes to trial outcomes after the trial commenced, with reasons"),
    ("7a", "How sample size was determined"),
    (
        "7b",
        "When applicable, explanation of any interim analyses and stopping guidelines",
    ),
    ("8a", "Method used to generate the random allocation sequence"),
    ("8b", "Type of randomisation; details of any restriction"),
    ("9", "Mechanism used to implement the random allocation sequence"),
    ("10", "Who generated the random allocation sequence, who enrolled, who assigned"),
    ("11a", "If done, who was blinded after assignment and how"),
    ("11b", "If relevant, description of the similarity of interventions"),
    (
        "12a",
        "Statistical methods used to compare groups for primary and secondary outcomes",
    ),
    (
        "12b",
        "Methods for additional analyses, such as subgroup analyses and adjusted analyses",
    ),
    (
        "13a",
        "For each group, numbers of participants randomly assigned, received treatment, analysed",
    ),
    (
        "13b",
        "For each group, losses and exclusions after randomisation, together with reasons",
    ),
    ("14a", "Dates defining the periods of recruitment and follow-up"),
    ("14b", "Why the trial ended or was stopped"),
]

# STROBE checklist items (22 items for observational studies)
STROBE_ITEMS = [
    (
        "1",
        "Indicate the study's design with a commonly used term in the title or abstract",
    ),
    ("2", "Provide in the abstract an informative and balanced summary"),
    ("3", "Explain the scientific background and rationale for the investigation"),
    ("4", "State specific objectives, including any prespecified hypotheses"),
    ("5", "Present key elements of study design early in the paper"),
    ("6", "Describe the setting, locations, and relevant dates"),
    ("7", "Give the eligibility criteria, and the sources and methods of selection"),
    ("8", "Clearly define all outcomes, exposures, predictors, potential confounders"),
    ("9", "Describe any efforts to address potential sources of bias"),
    ("10", "Explain how the study size was arrived at"),
    ("11", "Explain how quantitative variables were handled in the analyses"),
    ("12", "Describe all statistical methods"),
    ("13", "Report numbers of individuals at each stage of study"),
    ("14", "Give characteristics of study participants"),
    ("15", "Report numbers of outcome events or summary measures"),
    (
        "16",
        "Give unadjusted estimates and, if applicable, confounder-adjusted estimates",
    ),
    ("17", "Report other analyses done"),
    ("18", "Summarise key results with reference to study objectives"),
    ("19", "Discuss limitations of the study"),
    ("20", "Give a cautious overall interpretation of results"),
    ("21", "Discuss the generalisability of the study results"),
    ("22", "Give the source of funding and the role of the funders"),
]

# PRISMA checklist items (27 items for systematic reviews)
PRISMA_ITEMS = [
    ("1", "Identify the report as a systematic review, meta-analysis, or both"),
    ("2", "Provide a structured summary"),
    ("3", "Describe the rationale for the review"),
    ("4", "Provide an explicit statement of questions being addressed"),
    ("5", "Indicate if a review protocol exists"),
    ("6", "Specify study characteristics and report characteristics used as criteria"),
    ("7", "Describe all information sources"),
    ("8", "Present full electronic search strategy for at least one database"),
    ("9", "State the process for selecting studies"),
    ("10", "Describe method of data extraction"),
    ("11", "List and define all variables for which data were sought"),
    ("12", "Describe methods used for assessing risk of bias"),
    ("13", "State the principal summary measures"),
    ("14", "Describe the methods of handling data and combining results"),
    (
        "15",
        "Specify any assessment of risk of bias that may affect the cumulative evidence",
    ),
    ("16", "Describe methods of additional analyses"),
    ("17", "Give numbers of studies screened, assessed, and included"),
    ("18", "For each study, present characteristics and data"),
    ("19", "Present data on risk of bias of each study"),
    ("20", "For all outcomes, present simple summary data and effect estimates"),
    ("21", "Present results of each meta-analysis done"),
    ("22", "Present results of any assessment of risk of bias across studies"),
    ("23", "Give results of additional analyses"),
    ("24", "Summarize the main findings"),
    ("25", "Discuss limitations"),
    ("26", "Provide a general interpretation of the results"),
    ("27", "Describe sources of funding"),
]


def get_checklist(paper_type: str) -> tuple[str, list[tuple[str, str]]]:
    """Get the appropriate checklist for a paper type."""
    checklists = {
        "rct": ("CONSORT", CONSORT_ITEMS),
        "cohort": ("STROBE", STROBE_ITEMS),
        "meta_analysis": ("PRISMA", PRISMA_ITEMS),
    }
    return checklists.get(paper_type, ("STROBE", STROBE_ITEMS))


def check_compliance_prompt(manuscript: str, paper_type: str) -> str:
    """
    Generate a prompt for the LLM to check manuscript compliance.

    The actual compliance checking is done by the LLM via this prompt.
    Returns the prompt text for the agent to use.
    """
    checklist_name, items = get_checklist(paper_type)

    items_text = "\n".join(
        f"  {item_id}. {description}" for item_id, description in items
    )

    return f"""Check this {paper_type} manuscript against the {checklist_name} checklist.

Manuscript:
{manuscript}

{checklist_name} Items to check:
{items_text}

For EACH item, provide a JSON object:
{{"item_id": "<id>", "status": "PASS|WARN|FAIL", "finding": "what was found", "suggestion": "how to fix (for WARN/FAIL)"}}

Return a JSON array of all items."""


def generate_compliance_report(
    items: list[dict[str, Any]],
    checklist_type: str,
) -> dict[str, Any]:
    """
    Generate a structured compliance report from individual item checks.
    """
    passed = sum(1 for i in items if i.get("status") == "PASS")
    warnings = sum(1 for i in items if i.get("status") == "WARN")
    failed = sum(1 for i in items if i.get("status") == "FAIL")
    total = len(items)

    score = (passed + 0.5 * warnings) / total if total > 0 else 0.0

    return {
        "checklist_type": checklist_type,
        "total_items": total,
        "passed": passed,
        "warnings": warnings,
        "failed": failed,
        "items": items,
        "overall_score": round(score, 2),
        "needs_revision": failed > 0,
        "failed_items": [i for i in items if i.get("status") == "FAIL"],
        "warning_items": [i for i in items if i.get("status") == "WARN"],
    }
