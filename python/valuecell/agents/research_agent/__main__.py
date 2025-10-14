import asyncio

from valuecell.core.agent.decorator import create_wrapped_agent

from .core import ResearchAgent

if __name__ == "__main__":
    agent = create_wrapped_agent(ResearchAgent)
    asyncio.run(agent.serve())
