"""
Learning Sub-Agent (SRP: English, tech topics, articles, Q&A).

This sub-agent handles ALL learning-related requests:
- Learn English words/sentences
- Learn tech topics
- Learn from web articles (bilingual + mindmap)
- Answer questions and plan ideas
- Save and list learning records

ISP: Only gets learning-related tools — no notes, tasks, weather, etc.

Reference: journal_20260206_ai-agent-workflow.md Section 1 (SRP)
"""

import logging
from datetime import datetime
from functools import partial
from typing import Optional
from uuid import UUID

from langchain_core.language_models import BaseChatModel
from langchain_core.tools import StructuredTool
from langgraph.prebuilt import create_react_agent
from sqlalchemy.orm import Session

from app.services.secretary_agent.prompts import get_prompt
from app.services.secretary_agent.tools.article_processor import (
    LearnArticleInput,
    learn_article,
)
from app.services.secretary_agent.tools.save_learning_tool import (
    ListLearningInput,
    SaveLearningInput,
    list_learning,
    save_learning,
)

logger = logging.getLogger("secretary_agent.learning")


def create_learning_tools(
    db: Optional[Session] = None,
    user_id: Optional[int] = None,
    session_id: Optional[UUID] = None,
) -> list[StructuredTool]:
    """
    Create learning-domain tools.

    ISP: Only tools relevant to learning are included.
    DIP: Tools depend on abstract interfaces (db session, user context),
         not on specific implementations.

    Args:
        db: Database session for persistence tools
        user_id: Current user ID for scoped queries
        session_id: Current chat session ID

    Returns:
        List of StructuredTool instances for learning
    """
    tools: list[StructuredTool] = []

    # Save learning record
    tools.append(
        StructuredTool.from_function(
            func=partial(
                save_learning,
                db=db,
                user_id=user_id,
                session_id=session_id,
            ),
            name="save_learning",
            description=(
                "Save a learning record when user explicitly asks to save/remember "
                "learning content. Input types: word, sentence, topic, article, "
                "question, idea. Only use when user explicitly requests to save."
            ),
            args_schema=SaveLearningInput,
        )
    )

    # List learning records
    tools.append(
        StructuredTool.from_function(
            func=partial(
                list_learning,
                db=db,
                user_id=user_id,
            ),
            name="list_learning",
            description=(
                "List user's learning records. "
                "Can filter by type (word, sentence, topic, etc.)."
            ),
            args_schema=ListLearningInput,
        )
    )

    # Learn from web article (async)
    tools.append(
        StructuredTool.from_function(
            coroutine=learn_article,
            name="learn_article",
            description=(
                "Learn from a web article or PDF. Provide a URL and the tool will: "
                "1) Fetch the page (HTML or PDF), "
                "2) Extract main content to text, "
                "3) Translate to bilingual (English + Chinese), "
                "4) Summarize with key points, "
                "5) Generate a PlantUML mindmap, "
                "6) Render the mindmap as PNG. "
                "Works best with: direct article HTML URLs and direct .pdf links. "
                "Limitations: JavaScript-rendered pages and login-required pages may fail; "
                "suggest the user paste the article text or save as PDF and share that link."
            ),
            args_schema=LearnArticleInput,
        )
    )

    return tools


def create_learning_agent(
    llm: BaseChatModel,
    db: Optional[Session] = None,
    user_id: Optional[int] = None,
    session_id: Optional[UUID] = None,
):
    """
    Create the Learning sub-agent with its tools.

    Args:
        llm: The language model instance
        db: Database session
        user_id: Current user ID
        session_id: Current chat session ID

    Returns:
        A compiled LangGraph agent (CompiledStateGraph)
    """
    tools = create_learning_tools(db=db, user_id=user_id, session_id=session_id)

    prompt = get_prompt(
        "sub_agents.yaml",
        "learning_agent",
        current_date=datetime.now().strftime("%Y-%m-%d"),
    )

    agent = create_react_agent(
        model=llm,
        tools=tools,
        prompt=prompt,
        name="learning_agent",
    )

    logger.info(
        f"Created LearningAgent with {len(tools)} tools: " f"{[t.name for t in tools]}"
    )

    return agent
