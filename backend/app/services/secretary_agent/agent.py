"""
Personal Secretary AI Agent — Supervisor + SubAgent Architecture.

Refactored from a monolithic agent to a multi-agent workflow based on:
  journal_20260206_ai-agent-workflow.md

Architecture:
  ┌─────────────────────────────────────────────────┐
  │  SecretaryAgent (Supervisor)                    │
  │  Routes to sub-agents via LangGraph StateGraph  │
  └──┬──────────────┬──────────────┬────────────────┘
     │              │              │
     ▼              ▼              ▼
  ┌──────────┐ ┌────────────┐ ┌──────────┐
  │ Learning │ │Productivity│ │ Utility  │
  │  Agent   │ │   Agent    │ │  Agent   │
  │  (SRP)   │ │   (SRP)    │ │  (SRP)   │
  └──────────┘ └────────────┘ └──────────┘

Design Principles Applied:
  SRP:  Each sub-agent handles one domain only
  OCP:  Add new agent = add new module + graph node
  LSP:  Any sub-agent can be swapped if it respects MessagesState
  ISP:  Each agent only gets the tools it needs
  DIP:  Supervisor depends on A2A contract, not implementation details

Workflow:
  User message → Supervisor (routes) → SubAgent (executes) → Supervisor → ...
  The supervisor can loop back if more work is needed.
"""

import logging
import time
from datetime import datetime
from typing import Any, AsyncIterator, Literal, Optional
from uuid import UUID

import httpx
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import create_react_agent
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.config import settings
from app.services.secretary_agent.a2a import (
    A2AMessage,
    A2AMetrics,
    A2AStatus,
    create_a2a_request,
    create_a2a_response,
)
from app.services.secretary_agent.prompts import get_prompt
from app.services.secretary_agent.sub_agents.learning import (
    create_learning_agent,
    create_learning_tools,
)
from app.services.secretary_agent.sub_agents.productivity import (
    create_productivity_agent,
    create_productivity_tools,
)
from app.services.secretary_agent.sub_agents.coach import (
    create_coach_agent,
    create_coach_tools,
)
from app.services.secretary_agent.sub_agents.utility import (
    create_utility_agent,
    create_utility_tools,
)
from app.services.secretary_agent.tracing import (
    get_trace_context,
    new_trace,
    trace_llm_call,
)

logger = logging.getLogger("secretary_agent")


# ============================================================================
# Constants
# ============================================================================

# Sub-agent node names (used in StateGraph)
SUPERVISOR = "supervisor"
LEARNING_AGENT = "learning_agent"
PRODUCTIVITY_AGENT = "productivity_agent"
UTILITY_AGENT = "utility_agent"
COACH_AGENT = "coach_agent"

# All sub-agent names
SUB_AGENT_NAMES = [LEARNING_AGENT, PRODUCTIVITY_AGENT, UTILITY_AGENT, COACH_AGENT]

# Maximum number of supervisor routing loops before forcing END
MAX_ROUTING_ITERATIONS = 10


class RoutingDecision(BaseModel):
    """Structured output for supervisor routing decisions."""

    next: Literal[
        "learning_agent", "productivity_agent", "utility_agent", "coach_agent", "FINISH"
    ] = Field(
        description="The next agent to route to, or FINISH if the user's request has been fully handled"
    )


class SecretaryState(MessagesState):
    """Extended state with routing information."""

    next_agent: str


class SecretaryAgent:
    """
    Personal Secretary AI Agent — Supervisor Pattern.

    The Supervisor orchestrates three specialist sub-agents:
    - LearningAgent: English, tech topics, articles, Q&A
    - ProductivityAgent: notes, tasks, reminders
    - UtilityAgent: weather, calculator, datetime

    Uses LangGraph StateGraph for declarative workflow orchestration.
    Preserves backward-compatible API (chat / chat_stream).
    """

    def __init__(
        self,
        user_id: Optional[int] = None,
        session_id: Optional[UUID] = None,
        db: Optional[Session] = None,
    ):
        """
        Initialize the Secretary Agent (Supervisor).

        Args:
            user_id: ID of the current user
            session_id: ID of the current chat session
            db: Database session for tools that need database access
        """
        self.user_id = user_id
        self.session_id = session_id
        self.db = db

        # Initialize LLM with SSL configuration for self-hosted models
        self.llm = self._create_llm()

        # Build the multi-agent workflow (declarative DAG)
        self.workflow = self._build_workflow()

        # Collect all tools for /tools endpoint
        self.tools = self._collect_all_tools()

    def _create_llm(self) -> ChatOpenAI:
        """
        Create the LLM instance with proper SSL configuration.

        Supports self-hosted LLMs with self-signed certificates
        via LLM_VERIFY_SSL setting.
        """
        http_client = httpx.AsyncClient(
            verify=getattr(settings, "LLM_VERIFY_SSL", True),
            timeout=httpx.Timeout(timeout=getattr(settings, "LLM_TIMEOUT", 60.0)),
        )

        return ChatOpenAI(
            model=settings.LLM_MODEL,
            openai_api_key=settings.LLM_API_KEY,
            openai_api_base=settings.LLM_BASE_URL,
            temperature=0.7,
            streaming=True,
            http_async_client=http_client,
        )

    def _build_workflow(self):
        """
        Build the LangGraph StateGraph workflow.

        Topology:
            START → supervisor (routing decision via structured output)
                  → {learning_agent | productivity_agent | utility_agent | END}
            Each sub-agent → supervisor (for potential follow-up routing)
        """
        # Create sub-agents (each with ISP-minimal tool sets)
        learning = create_learning_agent(
            llm=self.llm,
            db=self.db,
            user_id=self.user_id,
            session_id=self.session_id,
        )

        productivity = create_productivity_agent(
            llm=self.llm,
            db=self.db,
            user_id=self.user_id,
            session_id=self.session_id,
        )

        utility = create_utility_agent(llm=self.llm)

        coach = create_coach_agent(
            llm=self.llm,
            db=self.db,
            user_id=self.user_id,
            session_id=self.session_id,
        )

        # Supervisor prompt for routing decisions
        supervisor_prompt = get_prompt(
            "sub_agents.yaml",
            "supervisor",
            current_date=datetime.now().strftime("%Y-%m-%d"),
            timezone="Asia/Shanghai",
        )

        # Router LLM with structured output for reliable routing
        router_llm = self.llm.with_structured_output(RoutingDecision)

        # Supervisor node — decides which sub-agent to route to
        async def supervisor_node(state: dict) -> dict:
            state_messages = state.get("messages", [])

            # Check if a sub-agent has already responded (i.e., we're in a follow-up loop).
            # If the last message is an AIMessage (from a sub-agent response),
            # default to FINISH to avoid infinite routing loops.
            sub_agent_responded = False
            for msg in reversed(state_messages):
                if isinstance(msg, HumanMessage):
                    break
                if isinstance(msg, AIMessage) and not msg.tool_calls:
                    sub_agent_responded = True
                    break

            if sub_agent_responded:
                logger.info("Supervisor: sub-agent already responded, finishing")
                return {"next_agent": "FINISH"}

            messages = [SystemMessage(content=supervisor_prompt)] + state_messages
            try:
                decision = await router_llm.ainvoke(messages)
                next_agent = decision.next
            except Exception as e:
                logger.warning(f"Structured routing failed, using fallback: {e}")
                # Fallback: ask the LLM directly and parse the response
                fallback_msg = (
                    "Based on the conversation, respond with ONLY one of these exact words: "
                    "learning_agent, productivity_agent, utility_agent, FINISH"
                )
                resp = await self.llm.ainvoke(
                    messages + [HumanMessage(content=fallback_msg)]
                )
                content = resp.content.strip().lower()
                if "learning" in content:
                    next_agent = "learning_agent"
                elif "productivity" in content:
                    next_agent = "productivity_agent"
                elif "coach" in content:
                    next_agent = "coach_agent"
                elif "utility" in content:
                    next_agent = "utility_agent"
                else:
                    next_agent = "FINISH"

            logger.info(f"Supervisor routed to: {next_agent}")
            return {"next_agent": next_agent}

        # Route decision function for conditional edges
        def route_decision(state: dict) -> str:
            next_agent = state.get("next_agent", "FINISH")
            if next_agent == "FINISH":
                return END
            return next_agent

        # Assemble the StateGraph — declarative DAG
        graph = StateGraph(SecretaryState)

        # Add nodes
        graph.add_node(SUPERVISOR, supervisor_node)
        graph.add_node(learning)
        graph.add_node(productivity)
        graph.add_node(utility)
        graph.add_node(coach)

        # Wire the edges
        graph.add_edge(START, SUPERVISOR)

        # Supervisor routes conditionally to sub-agents or END
        graph.add_conditional_edges(
            SUPERVISOR,
            route_decision,
            {
                LEARNING_AGENT: LEARNING_AGENT,
                PRODUCTIVITY_AGENT: PRODUCTIVITY_AGENT,
                UTILITY_AGENT: UTILITY_AGENT,
                COACH_AGENT: COACH_AGENT,
                END: END,
            },
        )

        # Every sub-agent returns to supervisor for potential follow-up
        graph.add_edge(LEARNING_AGENT, SUPERVISOR)
        graph.add_edge(PRODUCTIVITY_AGENT, SUPERVISOR)
        graph.add_edge(UTILITY_AGENT, SUPERVISOR)
        graph.add_edge(COACH_AGENT, SUPERVISOR)

        # Compile the workflow
        compiled = graph.compile()

        logger.info(
            "Built multi-agent workflow: "
            f"supervisor → [{', '.join(SUB_AGENT_NAMES)}]"
        )

        return compiled

    def _collect_all_tools(self) -> list:
        """
        Collect all tools from all sub-agents (for /tools endpoint).

        This does NOT give all tools to one agent (that would violate ISP).
        It's only used for API discovery.
        """
        all_tools = []
        all_tools.extend(
            create_learning_tools(
                db=self.db,
                user_id=self.user_id,
                session_id=self.session_id,
            )
        )
        all_tools.extend(
            create_productivity_tools(
                db=self.db,
                user_id=self.user_id,
                session_id=self.session_id,
            )
        )
        all_tools.extend(create_utility_tools())
        all_tools.extend(
            create_coach_tools(
                db=self.db,
                user_id=self.user_id,
                session_id=self.session_id,
            )
        )
        return all_tools

    # ========================================================================
    # Public API (backward compatible)
    # ========================================================================

    async def chat(
        self,
        user_message: str,
        chat_history: Optional[list[dict]] = None,
    ) -> dict[str, Any]:
        """
        Process a chat message and return the response.

        Args:
            user_message: The user's message
            chat_history: Previous messages in the conversation

        Returns:
            Dictionary with response content and metadata
        """
        trace_id = new_trace(
            user_id=self.user_id,
            session_id=str(self.session_id) if self.session_id else None,
        )

        start_time = time.perf_counter()

        # Build message list for LangGraph
        messages = self._build_messages(chat_history, user_message)

        # Log A2A request
        a2a_req = create_a2a_request(
            sender="user",
            receiver=SUPERVISOR,
            intent="chat",
            input_data={"message": user_message},
            correlation_id=trace_id,
        )
        logger.debug(f"A2A request: {a2a_req.model_dump_json()}")

        try:
            # Invoke the workflow
            result = await self.workflow.ainvoke(
                {"messages": messages},
                config={"recursion_limit": MAX_ROUTING_ITERATIONS},
            )

            duration_ms = (time.perf_counter() - start_time) * 1000

            # Extract the final AI response
            response_content = self._extract_final_response(result)
            tool_calls = self._extract_tool_calls_from_messages(result)

            # Log A2A response
            a2a_resp = create_a2a_response(
                request=a2a_req,
                output={"content": response_content[:200]},
                metrics=A2AMetrics(
                    latency_ms=duration_ms,
                    tool_calls=len(tool_calls),
                ),
            )
            logger.info(
                f"Chat completed ({duration_ms:.0f}ms, "
                f"{len(tool_calls)} tool calls)"
            )
            logger.debug(f"A2A response: {a2a_resp.model_dump_json()}")

            return {
                "content": response_content,
                "tool_calls": tool_calls,
                "trace_id": trace_id,
            }

        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.error(f"Agent execution failed: {e}", exc_info=True)

            # Log A2A error
            a2a_resp = create_a2a_response(
                request=a2a_req,
                status=A2AStatus.ERROR,
                metrics=A2AMetrics(latency_ms=duration_ms),
            )

            return {
                "content": f"抱歉，处理您的请求时出现了问题: {str(e)}",
                "tool_calls": [],
                "trace_id": trace_id,
                "error": str(e),
            }

    async def chat_stream(
        self,
        user_message: str,
        chat_history: Optional[list[dict]] = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """
        Process a chat message and stream the response.

        Yields:
            Dictionaries with:
            - type: "token" | "tool_call" | "tool_result" |
                    "agent_start" | "agent_end" | "done" | "error"
            - content: The content
        """
        trace_id = new_trace(
            user_id=self.user_id,
            session_id=str(self.session_id) if self.session_id else None,
        )

        messages = self._build_messages(chat_history, user_message)

        try:
            async for event in self.workflow.astream_events(
                {"messages": messages},
                version="v1",
                config={"recursion_limit": MAX_ROUTING_ITERATIONS},
            ):
                kind = event.get("event")

                if kind == "on_chat_model_stream":
                    # Skip tokens from the supervisor routing LLM call
                    ev_tags = event.get("tags", [])
                    ev_meta = event.get("metadata", {})
                    if (
                        SUPERVISOR in ev_tags
                        or ev_meta.get("langgraph_node") == SUPERVISOR
                    ):
                        continue

                    # Streaming token from sub-agents
                    content = event.get("data", {}).get("chunk", {})
                    if hasattr(content, "content") and content.content:
                        yield {
                            "type": "token",
                            "content": content.content,
                        }

                elif kind == "on_tool_start":
                    tool_name = event.get("name", "unknown")
                    yield {
                        "type": "tool_call",
                        "tool": tool_name,
                        "args": event.get("data", {}).get("input", {}),
                    }

                elif kind == "on_tool_end":
                    yield {
                        "type": "tool_result",
                        "tool": event.get("name", "unknown"),
                        "result": str(event.get("data", {}).get("output", "")),
                    }

                elif kind == "on_chain_start":
                    # Track which sub-agent is active
                    name = event.get("name", "")
                    if name in SUB_AGENT_NAMES:
                        yield {
                            "type": "agent_start",
                            "agent": name,
                        }

                elif kind == "on_chain_end":
                    name = event.get("name", "")
                    if name in SUB_AGENT_NAMES:
                        yield {
                            "type": "agent_end",
                            "agent": name,
                        }

            # Signal completion
            yield {
                "type": "done",
                "trace_id": trace_id,
            }

        except Exception as e:
            logger.error(f"Streaming agent execution failed: {e}", exc_info=True)
            yield {
                "type": "error",
                "content": f"处理请求时出现错误: {str(e)}",
                "trace_id": trace_id,
            }

    # ========================================================================
    # Internal helpers
    # ========================================================================

    def _build_messages(
        self,
        chat_history: Optional[list[dict]],
        user_message: str,
    ) -> list:
        """
        Build LangGraph message list from chat history + new message.

        Args:
            chat_history: Previous messages [{role, content}, ...]
            user_message: New user message

        Returns:
            List of LangChain message objects
        """
        messages = []

        # Add history
        for msg in chat_history or []:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            if role == "user":
                messages.append(HumanMessage(content=content))
            elif role == "assistant":
                messages.append(AIMessage(content=content))
            elif role == "tool":
                messages.append(
                    ToolMessage(
                        content=content,
                        tool_call_id=msg.get("tool_call_id", ""),
                    )
                )

        # Add new user message
        messages.append(HumanMessage(content=user_message))

        return messages

    def _extract_final_response(self, result: dict) -> str:
        """Extract the final AI response from workflow result."""
        messages = result.get("messages", [])

        # Walk backwards to find the last AI message
        for msg in reversed(messages):
            if isinstance(msg, AIMessage) and msg.content:
                return msg.content

        return ""

    def _extract_tool_calls_from_messages(self, result: dict) -> list[dict]:
        """Extract tool call info from the message history."""
        tool_calls = []
        messages = result.get("messages", [])

        for i, msg in enumerate(messages):
            if isinstance(msg, ToolMessage):
                # Find the preceding AI message with tool_call
                tool_name = getattr(msg, "name", "unknown")
                tool_calls.append(
                    {
                        "tool": tool_name,
                        "result": msg.content[:500] if msg.content else "",
                    }
                )

        return tool_calls


# ============================================================================
# Learning Tool Functions (LLM-based, uses instructor for structured output)
# ============================================================================


async def process_learning_request(
    agent: SecretaryAgent,
    learning_type: str,
    user_input: str,
) -> dict[str, Any]:
    """
    Process a learning request using instructor for structured output.

    This is separate from the agent workflow — it's a direct LLM call
    for generating structured learning content.

    Args:
        agent: The SecretaryAgent instance
        learning_type: Type of learning (word, sentence, topic, question, idea)
        user_input: The user's input

    Returns:
        Structured response based on learning type
    """
    import instructor
    from openai import AsyncOpenAI

    from app.services.secretary_agent.tools.learning_tools import (
        IdeaPlanResponse,
        QuestionResponse,
        SentenceResponse,
        TopicResponse,
        WordResponse,
    )

    prompt_map = {
        "word": ("learning_tools.yaml", "learn_word", {"word": user_input}),
        "sentence": (
            "learning_tools.yaml",
            "learn_sentence",
            {"sentence": user_input},
        ),
        "topic": (
            "learning_tools.yaml",
            "learn_topic",
            {"topic": user_input},
        ),
        "question": (
            "learning_tools.yaml",
            "answer_question",
            {"question": user_input},
        ),
        "idea": (
            "learning_tools.yaml",
            "plan_idea",
            {"idea": user_input},
        ),
    }

    response_map = {
        "word": WordResponse,
        "sentence": SentenceResponse,
        "topic": TopicResponse,
        "question": QuestionResponse,
        "idea": IdeaPlanResponse,
    }

    if learning_type not in prompt_map:
        raise ValueError(f"Unknown learning type: {learning_type}")

    file, prompt_name, variables = prompt_map[learning_type]
    prompt = get_prompt(file, prompt_name, **variables)
    response_model = response_map[learning_type]

    client = instructor.from_openai(
        AsyncOpenAI(
            api_key=settings.LLM_API_KEY,
            base_url=settings.LLM_BASE_URL,
        )
    )

    response = await client.chat.completions.create(
        model=settings.LLM_MODEL,
        messages=[{"role": "user", "content": prompt}],
        response_model=response_model,
    )

    return response.model_dump()
