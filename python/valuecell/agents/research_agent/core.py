import os
from typing import AsyncGenerator, Iterator

from agno.agent import Agent, RunOutputEvent
from agno.models.google import Gemini
from edgar import set_identity
from loguru import logger

from valuecell.core.agent.responses import streaming
from valuecell.core.types import BaseAgent, StreamResponse

from .knowledge import knowledge

set_identity(os.getenv("SEC_EMAIL") or "your.name@example.com")


class ResearchAgent(BaseAgent):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.knowledge_research_agent = Agent(
            model=Gemini(id="gemini-2.5-flash"),
            knowledge=knowledge,
            search_knowledge=True,
            debug_mode=True,
        )

    async def analyze_from_knowledge(
        self, query: str
    ) -> AsyncGenerator[StreamResponse, None]:
        response_stream: Iterator[RunOutputEvent] = (
            await self.knowledge_research_agent.arun(
                query, stream=True, stream_intermediate_steps=True
            )
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

    async def stream(
        self, query: str, session_id: str, task_id: str
    ) -> AsyncGenerator[StreamResponse, None]:
        pass
