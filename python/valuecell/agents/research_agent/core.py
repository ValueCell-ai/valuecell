import os
from typing import AsyncGenerator, Iterator

from agno.agent import Agent, RunOutputEvent
from agno.models.google import Gemini
from edgar import set_identity
from loguru import logger

from valuecell.agents.research_agent.knowledge import knowledge
from valuecell.agents.research_agent.prompts import KNOWLEDGE_AGENT_INSTRUCTION
from valuecell.agents.research_agent.sources import fetch_sec_filings
from valuecell.core.agent.responses import streaming
from valuecell.core.types import BaseAgent, StreamResponse
from valuecell.utils.env import agent_debug_mode_enabled


class ResearchAgent(BaseAgent):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.knowledge_research_agent = Agent(
            model=Gemini(id="gemini-2.5-flash"),
            tools=[fetch_sec_filings],
            knowledge=knowledge,
            search_knowledge=True,
            instructions=[KNOWLEDGE_AGENT_INSTRUCTION],
            add_datetime_to_context=True,
            debug_mode=agent_debug_mode_enabled(),
        )
        set_identity(os.getenv("SEC_EMAIL"))

    async def stream(
        self, query: str, session_id: str, task_id: str
    ) -> AsyncGenerator[StreamResponse, None]:
        response_stream: Iterator[RunOutputEvent] = self.knowledge_research_agent.arun(
            query, stream=True, stream_intermediate_steps=True
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
        query = "Provide a summary of Apple's 2024 all quarterly report."
        async for response in agent.stream(query, "test_session", "test_task"):
            print(response)

    asyncio.run(main())
