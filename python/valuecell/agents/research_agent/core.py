import os
from typing import AsyncGenerator, Dict, Iterator, Optional

from agno.agent import Agent, RunOutputEvent
from agno.db.in_memory import InMemoryDb
from agno.models.google import Gemini
from agno.models.openrouter import OpenRouter
from edgar import set_identity
from loguru import logger

from valuecell.agents.research_agent.knowledge import knowledge
from valuecell.agents.research_agent.prompts import (
    KNOWLEDGE_AGENT_EXPECTED_OUTPUT,
    KNOWLEDGE_AGENT_INSTRUCTION,
)
from valuecell.agents.research_agent.sources import (
    fetch_event_sec_filings,
    fetch_periodic_sec_filings,
)
from valuecell.core.agent.responses import streaming
from valuecell.core.types import BaseAgent, StreamResponse
from valuecell.utils.env import agent_debug_mode_enabled


def _get_model_based_on_env() -> str:
    model_id = os.getenv("RESEARCH_AGENT_MODEL_ID")
    if os.getenv("GOOGLE_API_KEY"):
        return Gemini(id=model_id or "gemini-2.5-flash")
    return OpenRouter(id=model_id or "google/gemini-2.5-flash")


class ResearchAgent(BaseAgent):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.knowledge_research_agent = Agent(
            model=_get_model_based_on_env(),
            instructions=[KNOWLEDGE_AGENT_INSTRUCTION],
            expected_output=KNOWLEDGE_AGENT_EXPECTED_OUTPUT,
            tools=[fetch_periodic_sec_filings, fetch_event_sec_filings],
            knowledge=knowledge,
            db=InMemoryDb(),
            # context
            search_knowledge=True,
            add_datetime_to_context=True,
            add_history_to_context=True,
            num_history_runs=3,
            read_chat_history=True,
            enable_session_summaries=True,
            # configuration
            debug_mode=agent_debug_mode_enabled(),
        )
        set_identity(os.getenv("SEC_EMAIL"))

    async def stream(
        self,
        query: str,
        conversation_id: str,
        task_id: str,
        dependencies: Optional[Dict] = None,
    ) -> AsyncGenerator[StreamResponse, None]:
        response_stream: Iterator[RunOutputEvent] = self.knowledge_research_agent.arun(
            query,
            stream=True,
            stream_intermediate_steps=True,
            session_id=conversation_id,
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


if __name__ == "__main__":
    import asyncio

    async def main():
        agent = ResearchAgent()
        query = "Provide a summary of Apple's 2024 all quarterly and annual reports."
        async for response in agent.stream(query, "test_session", "test_task"):
            print(response)

    asyncio.run(main())
