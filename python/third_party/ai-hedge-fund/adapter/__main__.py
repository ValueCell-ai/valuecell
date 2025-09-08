import asyncio
import json

from valuecell.core.agent.decorator import serve
from valuecell.core.agent.types import BaseAgent

from src.main import run_hedge_fund


class AIHedgeFundAgent(BaseAgent):
    async def stream(self, query, session_id, task_id):
        query = json.loads(query)
        result = run_hedge_fund(**query)
        yield {
            "content": json.dumps(result),
            "is_task_complete": True,
        }


if __name__ == "__main__":
    agent = serve(port=10001)(AIHedgeFundAgent)()
    asyncio.run(agent.serve())
