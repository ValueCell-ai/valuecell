from __future__ import annotations

from typing import AsyncGenerator, Dict, Optional

from valuecell.core.agent.responses import streaming
from valuecell.core.types import BaseAgent, StreamResponse


class StrategyAgent(BaseAgent):
    """Minimal StrategyAgent entry for system integration.

    This is a placeholder agent that streams a short greeting and completes.
    It can be extended to wire the Strategy Agent decision loop
    (data -> features -> composer -> execution -> history/digest).
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def stream(
        self,
        query: str,
        conversation_id: str,
        task_id: str,
        dependencies: Optional[Dict] = None,
    ) -> AsyncGenerator[StreamResponse, None]:
        # Minimal streaming lifecycle: one message and done
        yield streaming.message_chunk(
            "StrategyAgent is online. Decision pipeline will be wired here."
        )
        yield streaming.done()
