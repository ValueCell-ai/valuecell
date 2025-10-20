import asyncio
from enum import Enum
from typing import Optional

from agno.agent import Agent
from agno.db.in_memory import InMemoryDb
from agno.tools.crawl4ai import Crawl4aiTools
from pydantic import BaseModel

from valuecell.core.coordinate.super_agent_prompts import (
    SUPER_AGENT_EXPECTED_OUTPUT,
    SUPER_AGENT_INSTRUCTION,
)
from valuecell.core.types import UserInput
from valuecell.utils.env import agent_debug_mode_enabled
from valuecell.utils.model import get_model


class SuperAgentDecision(str, Enum):
    ANSWER = "answer"
    HANDOFF_TO_PLANNER = "handoff_to_planner"


class SuperAgentOutcome(BaseModel):
    decision: SuperAgentDecision
    # Optional enriched result data
    answer_content: Optional[str] = None
    enriched_query: Optional[str] = None
    reason: Optional[str] = None


class SuperAgent:
    """Lightweight Super Agent that triages user intent before planning.

    Minimal stub implementation: returns HANDOFF_TO_PLANNER immediately.
    Future versions can stream content, ask for user input via callback,
    or directly produce tasks/plans.
    """

    def __init__(self) -> None:
        self.agent = Agent(
            model=get_model("PLANNER_MODEL_ID"),
            tools=[Crawl4aiTools()],
            markdown=False,
            debug_mode=agent_debug_mode_enabled(),
            instructions=[SUPER_AGENT_INSTRUCTION],
            expected_output=SUPER_AGENT_EXPECTED_OUTPUT,
            # context
            db=InMemoryDb(),
            add_datetime_to_context=True,
            add_history_to_context=True,
            num_history_runs=5,
            read_chat_history=True,
            enable_session_summaries=True,
            use_json_mode=True,
            output_schema=SuperAgentOutcome,
        )

    async def run(self, user_input: UserInput) -> SuperAgentOutcome:
        """Run super agent triage."""
        await asyncio.sleep(0)

        response = await self.agent.arun(
            user_input.query,
            session_id=user_input.meta.conversation_id,
            user_id=user_input.meta.user_id,
            add_history_to_context=True,
        )
        return response.content
