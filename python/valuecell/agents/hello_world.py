from valuecell.core.agent.decorator import serve
from valuecell.core.agent.types import BaseAgent


@serve()
class HelloWorldAgent(BaseAgent):
    """
    A simple Hello World Agent that responds with a greeting message.
    """

    async def stream(self, query, session_id, task_id):
        return {
            "content": f"Hello! You said: {query}",
            "is_task_complete": True,
        }
