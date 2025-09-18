import asyncio
from valuecell.core.agent.connect import RemoteConnections


async def main():
    # Create connection manager
    connections = RemoteConnections()

    # List all available Agents
    available = connections.list_available_agents()
    print(f"Available Agents: {available}")

    # Start Agent
    calc_url = await connections.start_agent("SecAgent")
    print(f"Calculator Agent started at: {calc_url}")

    # Get client and send message
    client = await connections.get_client("SecAgent")
    async for task, event in await client.send_message(
        "伯克希尔最近持仓变化", streaming=True
    ):
        print(f"接收到Task: {task}")

    print(f"Calculation result: {task.status}")

    # Clean up resources
    await connections.stop_all()


if __name__ == "__main__":
    asyncio.run(main())
