import os

from agno.agent import Agent
from agno.db.in_memory import InMemoryDb
from edgar import set_identity
from loguru import logger

from valuecell.agents.research_agent.prompts import (
    KNOWLEDGE_AGENT_EXPECTED_OUTPUT,
    KNOWLEDGE_AGENT_INSTRUCTION,
)
from valuecell.agents.research_agent.sources import (
    fetch_ashare_filings,
    fetch_event_sec_filings,
    fetch_periodic_sec_filings,
)
from valuecell.utils.env import agent_debug_mode_enabled

research_agent: None | Agent = None


def build_research_agent() -> Agent:
    import valuecell.utils.model as model_utils_mod
    from valuecell.agents.research_agent.knowledge import get_knowledge

    tools = [
        fetch_periodic_sec_filings,
        fetch_event_sec_filings,
        fetch_ashare_filings,
    ]
    # Configure EDGAR identity only when SEC_EMAIL is present
    sec_email = os.getenv("SEC_EMAIL")
    if sec_email:
        set_identity(sec_email)
    else:
        logger.warning(
            "SEC_EMAIL not set; EDGAR identity is not configured for ResearchAgent."
        )

    # Lazily obtain knowledge; disable search if unavailable
    knowledge = get_knowledge()
    return Agent(
        model=model_utils_mod.get_model_for_agent("research_agent"),
        instructions=[KNOWLEDGE_AGENT_INSTRUCTION],
        expected_output=KNOWLEDGE_AGENT_EXPECTED_OUTPUT,
        tools=tools,
        knowledge=knowledge,
        db=InMemoryDb(),
        # context
        search_knowledge=knowledge is not None,
        add_datetime_to_context=True,
        # configuration
        # debug_mode=agent_debug_mode_enabled(),
    )


def get_research_agent() -> Agent:
    """Lazily create and cache the ResearchAgent instance."""
    global research_agent
    if research_agent is None:
        research_agent = build_research_agent()
    return research_agent


async def research(query: str) -> str:
    """
    Perform asynchronous research using the cached ResearchAgent.

    The ResearchAgent is configured with a set of research tools
    (SEC/ASHARE filings fetchers, web search, and crypto-related search
    functions), an optional knowledge source, and an in-memory DB for
    short-lived context. The agent may call multiple tools internally and
    composes their outputs into a single human-readable string.

    The returned value is the agent's aggregated textual answer. Callers
    should treat the response as plain text suitable for display or further
    downstream natural-language processing.

    :param query: The natural-language research query or prompt to submit to
        the ResearchAgent (for example, "Summarize recent SEC filings for
        AAPL").
    :type query: str
    :return: A string containing the agent's aggregated research result.
    :rtype: str
    :raises RuntimeError: If the underlying agent fails or returns an
        unexpected error while executing the query.
    """
    agent = get_research_agent()
    result = await agent.arun(query)
    return result.content
