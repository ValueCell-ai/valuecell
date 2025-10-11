import asyncio
import logging
import os
from datetime import datetime
from typing import AsyncGenerator, List, Optional
import argparse

from agno.agent import Agent
from agno.models.openrouter import OpenRouter
from dateutil.relativedelta import relativedelta
from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field, field_validator
from valuecell.core.agent.decorator import create_wrapped_agent
from valuecell.core import BaseAgent, StreamResponse, streaming

from src.main import create_workflow
from src.utils.analysts import ANALYST_ORDER
from src.utils.progress import progress

allowed_analysts = set(
    key for display_name, key in sorted(ANALYST_ORDER, key=lambda x: x[1])
)
allowed_tickers = {"AAPL", "GOOGL", "MSFT", "NVDA", "TSLA"}

logger = logging.getLogger(__name__)


class HedgeFundRequest(BaseModel):
    tickers: List[str] = Field(
        ...,
        description=f"List of stock tickers to analyze. Must be from: {allowed_tickers}. Otherwise, empty.",
    )

    @field_validator("tickers")
    @classmethod
    def validate_tickers(cls, v):
        if not v:
            raise ValueError("No valid tickers are recognized.")
        invalid_tickers = set(v) - allowed_tickers
        if invalid_tickers:
            raise ValueError(
                f"Invalid tickers: {invalid_tickers}. Allowed: {allowed_tickers}"
            )
        return v


class AIHedgeFundAgent(BaseAgent):
    def __init__(self, analyst: Optional[List[str]] = None):
        super().__init__()
        self.agno_agent = Agent(
            model=OpenRouter(
                id=os.getenv("AI_HEDGE_FUND_PARSER_MODEL_ID") or "openai/gpt-4o-mini"
            ),
            output_schema=HedgeFundRequest,
            markdown=True,
        )
        self.analyst = analyst

    async def stream(
        self, query, session_id, task_id
    ) -> AsyncGenerator[StreamResponse, None]:
        logger.info(
            f"Parsing query: {query}. Task ID: {task_id}, Session ID: {session_id}"
        )
        run_response = await self.agno_agent.arun(
            f"Parse the following hedge fund analysis request and extract the parameters: {query}"
        )
        hedge_fund_request = run_response.content
        if not isinstance(hedge_fund_request, HedgeFundRequest):
            logger.error(f"Unable to parse query: {query}")
            raise ValueError(
                f"Unable to parse your query. Please provide allowed tickers: {allowed_tickers}"
            )

        end_date = datetime.now().strftime("%Y-%m-%d")
        end_date_obj = datetime.strptime(end_date, "%Y-%m-%d")
        start_date = (end_date_obj - relativedelta(months=3)).strftime("%Y-%m-%d")

        initial_cash = 10000.00
        portfolio = {
            "cash": initial_cash,
            "margin_requirement": 0,
            "margin_used": 0.0,
            "positions": {
                ticker: {
                    "long": 0,
                    "short": 0,
                    "long_cost_basis": 0.0,
                    "short_cost_basis": 0.0,
                    "short_margin_used": 0.0,
                }
                for ticker in hedge_fund_request.tickers
            },
            "realized_gains": {
                ticker: {
                    "long": 0.0,
                    "short": 0.0,
                }
                for ticker in hedge_fund_request.tickers
            },
        }

        logger.info(f"Start analyzing. Task ID: {task_id}, Session ID: {session_id}")
        async for _, chunk in run_hedge_fund_stream(
            tickers=hedge_fund_request.tickers,
            start_date=start_date,
            end_date=end_date,
            portfolio=portfolio,
            model_name="openai/gpt-4o-mini",
            model_provider="OpenRouter",
            selected_analysts=self.analyst,
        ):
            if not isinstance(chunk, str):
                continue
            yield streaming.message_chunk(chunk)
        yield streaming.done()


async def run_hedge_fund_stream(
    tickers: list[str],
    start_date: str,
    end_date: str,
    portfolio: dict,
    selected_analysts: Optional[List[str]],
    show_reasoning: bool = False,
    model_name: str = "gpt-4.1",
    model_provider: str = "OpenAI",
):
    # Start progress tracking
    progress.start()

    try:
        # Create a new workflow if analysts are customized
        workflow = create_workflow(selected_analysts)
        _agent = workflow.compile()

        inputs = {
            "messages": [
                HumanMessage(
                    content="Make trading decisions based on the provided data.",
                )
            ],
            "data": {
                "tickers": tickers,
                "portfolio": portfolio,
                "start_date": start_date,
                "end_date": end_date,
                "analyst_signals": {},
            },
            "metadata": {
                "show_reasoning": show_reasoning,
                "model_name": model_name,
                "model_provider": model_provider,
            },
        }
        async for res in _agent.astream(inputs, stream_mode=["custom", "messages"]):
            yield res
    finally:
        # Stop progress tracking
        progress.stop()


if __name__ == "__main__":
    # Parse CLI arguments to determine selected analyst
    parser = argparse.ArgumentParser(
        description="Serve AI Hedge Fund Agent with an optional selected analyst"
    )
    parser.add_argument(
        "--analyst",
        type=str,
        choices=sorted(allowed_analysts),
        help=(
            "Single analyst key. Allowed: "
            + ", ".join(sorted(allowed_analysts))
            + ". If omitted, all analysts are used."
        ),
    )
    args = parser.parse_args()

    selected: Optional[List[str]] = None
    if args.analyst:
        selected = [args.analyst.strip()]

    if selected is not None:
        invalid = set(selected) - allowed_analysts
        if invalid:
            allowed_str = ", ".join(sorted(allowed_analysts))
            raise SystemExit(
                f"Invalid analyst key(s): {sorted(invalid)}. Allowed: {allowed_str}"
            )

    # Determine agent class to wrap (to match agent card and port)
    AgentClass = AIHedgeFundAgent
    agent_name_override = None

    def _to_pascal_agent_name(analyst_key: str) -> str:
        return "".join(part.capitalize() for part in analyst_key.split("_")) + "Agent"

    if selected and len(selected) == 1:
        # Infer agent name from single analyst key
        agent_name_override = _to_pascal_agent_name(selected[0])

    if agent_name_override:
        # Dynamically create a subclass with the desired class name so create_wrapped_agent finds the right agent card
        AgentClass = type(agent_name_override, (AIHedgeFundAgent,), {})

    # Create wrapped agent and inject selected analysts before serving
    agent = create_wrapped_agent(AgentClass)
    agent.analyst = selected  # Use None for all analysts
    asyncio.run(agent.serve())
