"""
Medical Paper Supervisor — Routes tasks between sub-agents.

Implements the hub-and-spoke supervisor pattern:
  START → supervisor → {literature | stats | writer | compliance | END}
  Each sub-agent → supervisor (for next-step routing)

Routing logic:
  1. Literature: Collect references (≥10)
  2. Stats: Run statistical analysis
  3. Writer: Generate IMRAD manuscript
  4. Compliance: Check reporting guidelines
  5. Revision loop (max 3 rounds) or finalize
"""

import logging
import time
from datetime import datetime
from typing import Any, AsyncIterator, Optional
from uuid import UUID

import httpx
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_openai import ChatOpenAI
from sqlalchemy.orm import Session

from app.core.config import settings
from app.services.medical_paper_agent.a2a import (
    MedicalA2AMessage,
    MedicalA2AStatus,
    create_medical_request,
    create_medical_response,
)
from app.services.medical_paper_agent.prompt_loader import get_prompt
from app.services.medical_paper_agent.state import MedicalPaperState
from app.services.medical_paper_agent.sub_agents.compliance import (
    create_compliance_agent,
)
from app.services.medical_paper_agent.sub_agents.literature import (
    create_literature_agent,
)
from app.services.medical_paper_agent.sub_agents.stats import (
    create_stats_agent,
)
from app.services.medical_paper_agent.sub_agents.writer import (
    create_writer_agent,
)

logger = logging.getLogger("medical_paper_agent")


# ============================================================================
# Constants
# ============================================================================

SUPERVISOR = "supervisor"
LITERATURE_AGENT = "literature_agent"
STATS_AGENT = "stats_agent"
WRITER_AGENT = "writer_agent"
COMPLIANCE_AGENT = "compliance_agent"

SUB_AGENT_NAMES = [
    LITERATURE_AGENT,
    STATS_AGENT,
    WRITER_AGENT,
    COMPLIANCE_AGENT,
]

# Maximum routing iterations to prevent infinite loops
MAX_ROUTING_ITERATIONS = 20

# Minimum references required before proceeding to stats
MIN_REFERENCES = 10

# Compliance score threshold for passing
COMPLIANCE_THRESHOLD = 0.8


class MedicalPaperSupervisor:
    """
    Medical Paper Writing Assistant — Supervisor Pattern.

    Orchestrates four specialist sub-agents through a multi-stage pipeline:
    - LiteratureAgent: PubMed search and citation formatting
    - StatsAgent: Statistical analysis (t-test, chi-square, survival)
    - WriterAgent: IMRAD manuscript section generation
    - ComplianceAgent: CONSORT/STROBE/PRISMA compliance checking

    Uses LangGraph StateGraph for workflow orchestration.
    """

    def __init__(
        self,
        user_id: Optional[int] = None,
        task_id: Optional[str] = None,
        db: Optional[Session] = None,
    ):
        self.user_id = user_id
        self.task_id = task_id
        self.db = db
        self.llm = self._create_llm()
        self.workflow = self._build_workflow()

    def _create_llm(self) -> ChatOpenAI:
        """Create the LLM instance with SSL configuration."""
        http_client = httpx.AsyncClient(
            verify=getattr(settings, "LLM_VERIFY_SSL", True),
            timeout=httpx.Timeout(timeout=getattr(settings, "LLM_TIMEOUT", 60.0)),
        )

        return ChatOpenAI(
            model=settings.LLM_MODEL,
            openai_api_key=settings.LLM_API_KEY,
            openai_api_base=settings.LLM_BASE_URL,
            temperature=0.3,  # Lower temperature for medical writing
            streaming=True,
            http_async_client=http_client,
        )

    def _build_workflow(self):
        """
        Build the LangGraph StateGraph for the medical paper pipeline.

        Topology:
            START → supervisor → {literature | stats | writer | compliance | END}
            Each sub-agent → supervisor (for next-step routing)
        """
        from langgraph.graph import END, START, StateGraph
        from langgraph.prebuilt import create_react_agent

        # Create sub-agents with SRP tools
        literature = create_literature_agent(self.llm)
        stats = create_stats_agent(self.llm)
        writer = create_writer_agent(self.llm)
        compliance = create_compliance_agent(self.llm)

        # Create supervisor (no tools — routing only)
        supervisor_prompt = get_prompt(
            "supervisor/router.v1.yaml",
            "route_task",
            paper_type="{paper_type}",
            current_step="{current_step}",
        )

        supervisor = create_react_agent(
            model=self.llm,
            tools=[],
            prompt=supervisor_prompt,
            name=SUPERVISOR,
        )

        # Assemble the StateGraph
        graph = StateGraph(MedicalPaperState)

        # Add supervisor with allowed routing destinations
        graph.add_node(
            supervisor,
            destinations=(
                LITERATURE_AGENT,
                STATS_AGENT,
                WRITER_AGENT,
                COMPLIANCE_AGENT,
                END,
            ),
        )

        # Add sub-agent nodes
        graph.add_node(literature)
        graph.add_node(stats)
        graph.add_node(writer)
        graph.add_node(compliance)

        # Wire edges: START → supervisor
        graph.add_edge(START, SUPERVISOR)

        # Every sub-agent returns to supervisor for next-step routing
        graph.add_edge(LITERATURE_AGENT, SUPERVISOR)
        graph.add_edge(STATS_AGENT, SUPERVISOR)
        graph.add_edge(WRITER_AGENT, SUPERVISOR)
        graph.add_edge(COMPLIANCE_AGENT, SUPERVISOR)

        compiled = graph.compile()

        logger.info(
            "Built medical paper workflow: "
            f"supervisor → [{', '.join(SUB_AGENT_NAMES)}]"
        )

        return compiled

    # ========================================================================
    # Public API
    # ========================================================================

    async def run(
        self,
        paper_type: str,
        research_question: str,
        study_design: Optional[dict[str, Any]] = None,
        raw_data: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """
        Run the full medical paper writing pipeline.

        Args:
            paper_type: Type of paper (rct, cohort, meta_analysis)
            research_question: The research question
            study_design: Study design parameters
            raw_data: Raw data for statistical analysis

        Returns:
            Dictionary with manuscript, references, stats, compliance report
        """
        start_time = time.perf_counter()

        # Build initial state
        initial_message = HumanMessage(
            content=f"Write a {paper_type} paper. "
            f"Research question: {research_question}"
        )

        initial_state = {
            "messages": [initial_message],
            "task_id": self.task_id,
            "user_id": self.user_id,
            "paper_type": paper_type,
            "research_question": research_question,
            "study_design": study_design or {},
            "raw_data": raw_data or {},
            "current_step": "literature",
        }

        # Log A2A request
        a2a_req = create_medical_request(
            sender="user",
            receiver=SUPERVISOR,
            intent="write_paper",
            input_data={
                "paper_type": paper_type,
                "research_question": research_question,
            },
        )
        logger.info(f"Starting paper pipeline: {a2a_req.correlation_id}")

        try:
            result = await self.workflow.ainvoke(
                initial_state,
                config={"recursion_limit": MAX_ROUTING_ITERATIONS},
            )

            duration_ms = (time.perf_counter() - start_time) * 1000

            # Extract final response
            response_content = self._extract_final_response(result)

            logger.info(
                f"Paper pipeline completed ({duration_ms:.0f}ms, "
                f"revision rounds: {result.get('revision_round', 0)})"
            )

            return {
                "content": response_content,
                "references": result.get("references", []),
                "stats_report": result.get("stats_report", {}),
                "manuscript_sections": result.get("manuscript_sections", {}),
                "compliance_report": result.get("compliance_report", {}),
                "revision_rounds": result.get("revision_round", 0),
                "correlation_id": a2a_req.correlation_id,
            }

        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.error(f"Paper pipeline failed: {e}", exc_info=True)

            return {
                "content": f"Paper generation failed: {str(e)}",
                "error": str(e),
                "correlation_id": a2a_req.correlation_id,
            }

    async def run_stream(
        self,
        paper_type: str,
        research_question: str,
        study_design: Optional[dict[str, Any]] = None,
        raw_data: Optional[dict[str, Any]] = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """
        Run the pipeline with streaming events.

        Yields:
            Event dicts with type: token | tool_call | tool_result |
            agent_start | agent_end | step_complete | done | error
        """
        initial_message = HumanMessage(
            content=f"Write a {paper_type} paper. "
            f"Research question: {research_question}"
        )

        initial_state = {
            "messages": [initial_message],
            "task_id": self.task_id,
            "user_id": self.user_id,
            "paper_type": paper_type,
            "research_question": research_question,
            "study_design": study_design or {},
            "raw_data": raw_data or {},
            "current_step": "literature",
        }

        try:
            async for event in self.workflow.astream_events(
                initial_state,
                version="v1",
                config={"recursion_limit": MAX_ROUTING_ITERATIONS},
            ):
                kind = event.get("event")

                if kind == "on_chat_model_stream":
                    content = event.get("data", {}).get("chunk", {})
                    if hasattr(content, "content") and content.content:
                        yield {"type": "token", "content": content.content}

                elif kind == "on_tool_start":
                    yield {
                        "type": "tool_call",
                        "tool": event.get("name", "unknown"),
                        "args": event.get("data", {}).get("input", {}),
                    }

                elif kind == "on_tool_end":
                    yield {
                        "type": "tool_result",
                        "tool": event.get("name", "unknown"),
                        "result": str(event.get("data", {}).get("output", "")),
                    }

                elif kind == "on_chain_start":
                    name = event.get("name", "")
                    if name in SUB_AGENT_NAMES:
                        yield {"type": "agent_start", "agent": name}

                elif kind == "on_chain_end":
                    name = event.get("name", "")
                    if name in SUB_AGENT_NAMES:
                        yield {"type": "agent_end", "agent": name}

            yield {"type": "done"}

        except Exception as e:
            logger.error(f"Streaming pipeline failed: {e}", exc_info=True)
            yield {"type": "error", "content": str(e)}

    # ========================================================================
    # Internal helpers
    # ========================================================================

    def _extract_final_response(self, result: dict) -> str:
        """Extract the final AI response from workflow result."""
        messages = result.get("messages", [])
        for msg in reversed(messages):
            if isinstance(msg, AIMessage) and msg.content:
                return msg.content
        return ""
