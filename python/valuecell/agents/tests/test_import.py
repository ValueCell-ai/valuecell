import pytest
from valuecell.core.agent.connect import RemoteConnections


@pytest.mark.asyncio
async def test_run_hello_world():
    connections = RemoteConnections()
    name = "HelloWorldAgent"
    try:
        available = connections.list_available_agents()
        assert name in available

        url = await connections.start_agent("HelloWorldAgent")
        assert isinstance(url, str) and url

        client = await connections.get_client("HelloWorldAgent")
        task, event = await client.send_message("Hi there!")
        assert task is not None
        assert event is None
    finally:
        await connections.stop_all()
