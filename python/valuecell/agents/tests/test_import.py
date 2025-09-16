import pytest
from a2a.types import AgentCard
from valuecell.core.agent.connect import RemoteConnections


@pytest.mark.asyncio
async def test_run_hello_world():
    connections = RemoteConnections()
    name = "HelloWorldAgent"
    try:
        available = connections.list_available_agents()
        assert name in available

        agent_card = await connections.start_agent("HelloWorldAgent")
        assert isinstance(agent_card, AgentCard) and agent_card

        client = await connections.get_client("HelloWorldAgent")
        turns = 0
        async for task, event in await client.send_message("Hi there!"):
            assert task is not None
            assert event is None
            turns += 1
        assert turns == 1
    finally:
        await connections.stop_all()
