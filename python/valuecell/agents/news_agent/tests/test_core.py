from __future__ import annotations

import pytest

from valuecell.core.types import StreamResponse, TaskStatusEvent


@pytest.mark.asyncio
async def test_stream_returns_failed_response_when_agent_raises():
    from valuecell.agents.news_agent.core import NewsAgent

    class FailingAgent:
        async def arun(self, *args, **kwargs):
            if False:
                yield None
            raise RuntimeError("upstream news API unavailable")

    agent = object.__new__(NewsAgent)
    agent.knowledge_news_agent = FailingAgent()

    responses = [
        response
        async for response in agent.stream(
            query="latest market news", conversation_id="conversation", task_id="task"
        )
    ]

    assert len(responses) == 1
    assert isinstance(responses[0], StreamResponse)
    assert responses[0].event == TaskStatusEvent.TASK_FAILED
    assert (
        responses[0].content
        == "Error processing news query: upstream news API unavailable"
    )
