import os
from typing import AsyncGenerator, Dict, Optional

from agno.agent import Agent
from agno.db.in_memory import InMemoryDb
from edgar import set_identity
from loguru import logger

import valuecell.utils.model as model_utils_mod
from valuecell.agents.research_agent.knowledge import get_knowledge
from valuecell.agents.research_agent.prompts import (
    KNOWLEDGE_AGENT_EXPECTED_OUTPUT,
    KNOWLEDGE_AGENT_INSTRUCTION,
)
from valuecell.agents.research_agent.sources import (  # search_crypto_people,; search_crypto_projects,; search_crypto_vcs,
    fetch_ashare_filings,
    fetch_event_sec_filings,
    fetch_periodic_sec_filings,
    web_search,
)
from valuecell.agents.utils.context import build_ctx_from_dep
from valuecell.core.agent import streaming
from valuecell.core.types import BaseAgent, StreamResponse
from valuecell.utils.env import agent_debug_mode_enabled


class ResearchAgent(BaseAgent):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        tools = [
            fetch_periodic_sec_filings,
            fetch_event_sec_filings,
            fetch_ashare_filings,
            web_search,
            # TODO: The RootData tools will cost lots of time, so we disable them for now.
            # search_crypto_projects,
            # search_crypto_vcs,
            # search_crypto_people,
        ]
        # Lazily obtain knowledge; disable search if unavailable
        knowledge = get_knowledge()
        self.knowledge_research_agent = Agent(
            model=model_utils_mod.get_model_for_agent("research_agent"),
            instructions=[KNOWLEDGE_AGENT_INSTRUCTION],
            expected_output=KNOWLEDGE_AGENT_EXPECTED_OUTPUT,
            tools=tools,
            knowledge=knowledge,
            db=InMemoryDb(),
            # context
            search_knowledge=knowledge is not None,
            add_datetime_to_context=True,
            add_history_to_context=True,
            num_history_runs=3,
            read_chat_history=True,
            enable_session_summaries=True,
            # configuration
            debug_mode=agent_debug_mode_enabled(),
        )
        # Configure EDGAR identity only when SEC_EMAIL is present
        sec_email = os.getenv("SEC_EMAIL")
        if sec_email:
            set_identity(sec_email)
        else:
            logger.warning(
                "SEC_EMAIL not set; EDGAR identity is not configured for ResearchAgent."
            )

    async def stream(
        self,
        query: str,
        conversation_id: str,
        task_id: str,
        dependencies: Optional[Dict] = None,
    ) -> AsyncGenerator[StreamResponse, None]:
        response_stream = self.knowledge_research_agent.arun(
            query,
            stream=True,
            stream_intermediate_steps=True,
            session_id=conversation_id,
            add_dependencies_to_context=True,
            dependencies=build_ctx_from_dep(dependencies),
        )
        async for event in response_stream:
            if event.event == "RunContent":
                yield streaming.message_chunk(event.content)
            elif event.event == "ToolCallStarted":
                yield streaming.tool_call_started(
                    event.tool.tool_call_id, event.tool.tool_name
                )
            elif event.event == "ToolCallCompleted":
                yield streaming.tool_call_completed(
                    event.tool.result, event.tool.tool_call_id, event.tool.tool_name
                )
        logger.info("Financial data analysis completed")

        yield streaming.done()
