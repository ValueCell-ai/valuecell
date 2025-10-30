import asyncio

from valuecell.agents.news_agent import NewsAgent
from valuecell.core import create_wrapped_agent

if __name__ == "__main__":
    agent = create_wrapped_agent(NewsAgent)
    asyncio.run(agent.serve())
