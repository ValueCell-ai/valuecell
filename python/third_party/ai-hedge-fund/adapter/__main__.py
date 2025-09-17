import asyncio
import logging
import os
from datetime import datetime
from typing import List

from agno.agent import Agent
from agno.models.openrouter import OpenRouter
from dateutil.relativedelta import relativedelta
from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field, field_validator
from valuecell.core.agent.decorator import create_wrapped_agent
from valuecell.core.types import BaseAgent

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
    selected_analysts: List[str] = Field(
        default=[],
        description=f"List of analysts to use for analysis. If empty, all analysts will be used. Must be from {allowed_analysts}",
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

    @field_validator("selected_analysts")
    @classmethod
    def validate_analysts(cls, v):
        if v:  # Only validate if not empty
            invalid_analysts = set(v) - allowed_analysts
            if invalid_analysts:
                raise ValueError(
                    f"Invalid analysts: {invalid_analysts}. Allowed: {allowed_analysts}"
                )
        return v


class AIHedgeFundAgent(BaseAgent):
    def __init__(self):
        super().__init__()
        self.agno_agent = Agent(
            model=OpenRouter(
                id=os.getenv("AI_HEDGE_FUND_PARSER_MODEL_ID") or "openai/gpt-4o-mini"
            ),
            response_model=HedgeFundRequest,
            markdown=True,
        )

    async def stream(self, query, session_id, task_id):
        logger.info(
            f"Parsing query: {query}. Task ID: {task_id}, Session ID: {session_id}"
        )
        run_response = self.agno_agent.run(
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
        for stream_type, chunk in run_hedge_fund_stream(
            tickers=hedge_fund_request.tickers,
            start_date=start_date,
            end_date=end_date,
            portfolio=portfolio,
            model_name="openai/gpt-4o-mini",
            model_provider="OpenRouter",
            selected_analysts=hedge_fund_request.selected_analysts,
        ):
            if not isinstance(chunk, str):
                continue
            yield {
                "content": chunk,
                "is_task_complete": False,
            }

        yield {
            "content": "",
            "is_task_complete": True,
        }


def run_hedge_fund_stream(
    tickers: list[str],
    start_date: str,
    end_date: str,
    portfolio: dict,
    selected_analysts: list[str],
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
        yield from _agent.stream(inputs, stream_mode=["custom", "messages"])
    finally:
        # Stop progress tracking
        progress.stop()


if __name__ == "__main__":
    agent = create_wrapped_agent(AIHedgeFundAgent)
    asyncio.run(agent.serve())
