import asyncio

from valuecell.core.agent import create_wrapped_agent

from .core import PromptBasedStrategyAgent

if __name__ == "__main__":
    agent = create_wrapped_agent(PromptBasedStrategyAgent)
    asyncio.run(agent.serve())
