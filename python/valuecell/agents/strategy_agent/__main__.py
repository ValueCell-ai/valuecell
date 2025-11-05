import asyncio

from valuecell.core.agent import create_wrapped_agent

from .agent import StrategyAgent

if __name__ == "__main__":
    agent = create_wrapped_agent(StrategyAgent)
    asyncio.run(agent.serve())
