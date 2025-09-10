"""
Example usage of RemoteConnections with remote agents.

This script demonstrates how to:
1. Load remote agent cards from configuration files
2. Connect to remote agents
3. Get agent information
"""

import asyncio
import logging

from valuecell.core.agent.connect import RemoteConnections

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    """Main example function."""
    # Create RemoteConnections instance
    connections = RemoteConnections()

    # List all available agents (local + remote)
    available_agents = connections.list_available_agents()
    logger.info(f"Available agents: {available_agents}")

    # List only remote agents
    remote_agents = connections.list_remote_agents()
    logger.info(f"Remote agents: {remote_agents}")

    # Get info for each remote agent
    for agent_name in remote_agents:
        agent_info = connections.get_agent_info(agent_name)
        logger.info(f"Agent info for '{agent_name}': {agent_info}")

        # Get raw card data
        card_data = connections.get_remote_agent_card(agent_name)
        logger.info(f"Card data for '{agent_name}': {card_data}")

    # Try to start/connect to a remote agent (if any)
    if remote_agents:
        agent_name = remote_agents[0]
        logger.info(f"Attempting to start remote agent: {agent_name}")
        try:
            agent_url = await connections.start_agent(agent_name)
            logger.info(f"Successfully started {agent_name} at {agent_url}")

            # Get client connection
            client = await connections.get_client(agent_name)
            logger.info(f"Got client for {agent_name}: {client}")

            # Check updated agent info
            updated_info = connections.get_agent_info(agent_name)
            logger.info(f"Updated info for '{agent_name}': {updated_info}")

            async for resp in await client.send_message(
                "analyze apple stock with buffett and damodaran",
                streaming=True,
            ):
                logger.info(f"Response from {agent_name}: {resp}")

        except Exception as e:
            logger.error(f"Failed to start {agent_name}: {e}")


if __name__ == "__main__":
    asyncio.run(main())
