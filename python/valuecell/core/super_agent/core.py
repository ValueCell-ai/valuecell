import asyncio
from enum import Enum
from typing import Optional

from agno.agent import Agent
from agno.db.in_memory import InMemoryDb
from pydantic import BaseModel, Field

import valuecell.utils.model as model_utils_mod
from valuecell.core.super_agent.prompts import (
    SUPER_AGENT_EXPECTED_OUTPUT,
    SUPER_AGENT_INSTRUCTION,
)
from valuecell.core.types import UserInput
from valuecell.utils.env import agent_debug_mode_enabled


class SuperAgentDecision(str, Enum):
    ANSWER = "answer"
    HANDOFF_TO_PLANNER = "handoff_to_planner"


class SuperAgentOutcome(BaseModel):
    decision: SuperAgentDecision = Field(..., description="Super Agent's decision")
    # Optional enriched result data
    answer_content: Optional[str] = Field(
        None, description="Optional direct answer when decision is 'answer'"
    )
    enriched_query: Optional[str] = Field(
        None, description="Optional concise restatement to forward to Planner"
    )
    reason: Optional[str] = Field(None, description="Brief rationale for the decision")


class SuperAgent:
    """Lightweight Super Agent that triages user intent before planning.

    Minimal stub implementation: returns HANDOFF_TO_PLANNER immediately.
    Future versions can stream content, ask for user input via callback,
    or directly produce tasks/plans.
    """

    name: str = "ValueCellAgent"

    def __init__(self) -> None:
        # Lazy initialize: avoid constructing Agent at startup
        self.agent: Optional[Agent] = None

    def _get_or_init_agent(self) -> Optional[Agent]:
        """Create the underlying agent on first use.

        Returns the initialized Agent or None if initialization fails.
        """
        if self.agent is not None:
            return self.agent

        try:
            model = model_utils_mod.get_model_for_agent("super_agent")
            self.agent = Agent(
                model=model,
                # TODO: enable tools when needed
                # tools=[Crawl4aiTools()],
                markdown=False,
                debug_mode=agent_debug_mode_enabled(),
                instructions=[SUPER_AGENT_INSTRUCTION],
                # output format
                expected_output=SUPER_AGENT_EXPECTED_OUTPUT,
                output_schema=SuperAgentOutcome,
                use_json_mode=model_utils_mod.model_should_use_json_mode(model),
                # context
                db=InMemoryDb(),
                add_datetime_to_context=True,
                add_history_to_context=True,
                num_history_runs=5,
                read_chat_history=True,
                enable_session_summaries=True,
            )
            return self.agent
        except Exception:
            # Swallow to avoid startup failure; will fallback in run()
            self.agent = None
            return None

    async def run(self, user_input: UserInput) -> SuperAgentOutcome:
        """Run super agent triage."""
        await asyncio.sleep(0)
        agent = self._get_or_init_agent()
        if agent is None:
            # Fallback: handoff directly to planner without super agent model
            return SuperAgentOutcome(
                decision=SuperAgentDecision.HANDOFF_TO_PLANNER,
                enriched_query=user_input.query,
                reason="SuperAgent unavailable: missing model/provider configuration",
            )

        response = await agent.arun(
            user_input.query,
            session_id=user_input.meta.conversation_id,
            user_id=user_input.meta.user_id,
            add_history_to_context=True,
        )
        outcome = response.content
        if not isinstance(outcome, SuperAgentOutcome):
            try:
                model = agent.model
                model_description = f"{model.id} (via {model.provider})"
            except Exception:
                model_description = "unknown model/provider"
            answer_content = (
                f"SuperAgent produced a malformed response: `{outcome}`. "
                f"Please check the capabilities of your model `{model_description}` and try again later."
            )
            outcome = SuperAgentOutcome(
                decision=SuperAgentDecision.ANSWER,
                answer_content=answer_content,
            )
        return outcome
