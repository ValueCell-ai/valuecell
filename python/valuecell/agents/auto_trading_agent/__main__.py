"""Main entry point for auto trading agent"""

import asyncio

from valuecell.core.agent.decorator import create_wrapped_agent

from .agent import AutoTradingAgent

if __name__ == "__main__":
    agent = create_wrapped_agent(AutoTradingAgent)
    asyncio.run(agent.serve())
