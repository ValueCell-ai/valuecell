import asyncio
import logging

from pydantic import BaseModel, Field
from valuecell.core.coordinate.orchestrator import get_default_orchestrator
from valuecell.core.types import UserInput, UserInputMetadata

logger = logging.getLogger(__name__)

AGENT_ANALYST_MAP = {
    "aswath_damodaran_agent": ("Aswath Damodaran", "aswath_damodaran"),
    "ben_graham_agent": ("Ben Graham", "ben_graham"),
    "bill_ackman_agent": ("Bill Ackman", "bill_ackman"),
    "cathie_wood_agent": ("Cathie Wood", "cathie_wood"),
    "charlie_munger_agent": ("Charlie Munger", "charlie_munger"),
    "michael_burry_agent": ("Michael Burry", "michael_burry"),
    "mohnish_pabrai_agent": ("Mohnish Pabrai", "mohnish_pabrai"),
    "peter_lynch_agent": ("Peter Lynch", "peter_lynch"),
    "phil_fisher_agent": ("Phil Fisher", "phil_fisher"),
    "rakesh_jhunjhunwala_agent": ("Rakesh Jhunjhunwala", "rakesh_jhunjhunwala"),
    "stanley_druckenmiller_agent": ("Stanley Druckenmiller", "stanley_druckenmiller"),
    "warren_buffett_agent": ("Warren Buffett", "warren_buffett"),
    "technical_analyst_agent": ("Technical Analyst", "technical_analyst"),
    "fundamentals_analyst_agent": ("Fundamentals Analyst", "fundamentals_analyst"),
    "sentiment_analyst_agent": ("Sentiment Analyst", "sentiment_analyst"),
    "valuation_analyst_agent": ("Valuation Analyst", "valuation_analyst"),
}


class UserInputRaw(BaseModel):
    agent_name: str = Field(..., description="The name of the agent to use.")
    query: str = Field(..., description="The user's query for the agent.")


def _parse_user_input(raw: UserInputRaw) -> UserInput:
    meta = UserInputMetadata(
        session_id=f"{raw.agent_name}_session",
        user_id="default_user",
    )
    query = raw.query
    selected_analyst = AGENT_ANALYST_MAP.get(raw.agent_name)
    if selected_analyst:
        query += f"\n\n **Hint**: Use {selected_analyst[0]} ({selected_analyst[1]}) in your analysis."
    return UserInput(desired_agent_name="AIHedgeFundAgent", query=query, meta=meta)


async def analyze_with_ai_hedge_fund():
    raw = UserInputRaw(
        agent_name="warren_buffett_agent",
        query="What is your analysis of the stock AAPL?",
    )
    user_input = _parse_user_input(raw)
    orchestrator = get_default_orchestrator()
    async for message_chunk in orchestrator.process_user_input(user_input):
        logger.info(f"Got message_chunk={message_chunk}")


if __name__ == "__main__":
    asyncio.run(analyze_with_ai_hedge_fund())
