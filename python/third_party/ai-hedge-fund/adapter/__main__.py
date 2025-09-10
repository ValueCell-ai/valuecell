import asyncio
import json
from datetime import datetime
from typing import List

from agno.agent import Agent
from agno.models.openrouter import OpenRouter
from dateutil.relativedelta import relativedelta
from pydantic import BaseModel, Field, field_validator
from valuecell.core.agent.decorator import create_wrapped_agent
from valuecell.core.agent.types import BaseAgent

from src.main import run_hedge_fund
from src.utils.analysts import ANALYST_ORDER

allowed_analysts = set(
    key for display_name, key in sorted(ANALYST_ORDER, key=lambda x: x[1])
)
allowed_tickers = {"AAPL", "GOOGL", "MSFT", "NVDA", "TSLA"}


class HedgeFundRequest(BaseModel):
    tickers: List[str] = Field(
        ...,
        description=f"List of stock tickers to analyze. Must be from: {allowed_tickers}",
    )
    selected_analysts: List[str] = Field(
        default=[],
        description=f"List of analysts to use for analysis. If empty, all analysts will be used. Must be from {allowed_analysts}",
    )

    @field_validator("tickers")
    @classmethod
    def validate_tickers(cls, v):
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
            model=OpenRouter(id="openai/gpt-4o-mini"),
            response_model=HedgeFundRequest,
            markdown=True,
        )

    async def stream(self, query, session_id, task_id):
        run_response = self.agno_agent.run(
            f"Parse the following hedge fund analysis request and extract the parameters: {query}"
        )
        hedge_fund_request = run_response.content

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

        result = run_hedge_fund(
            tickers=hedge_fund_request.tickers,
            start_date=start_date,
            end_date=end_date,
            portfolio=portfolio,
            model_name="openai/gpt-4o-mini",
            model_provider="OpenRouter",
            selected_analysts=hedge_fund_request.selected_analysts,
        )

        yield {
            "content": json.dumps(result),
            "is_task_complete": True,
        }


if __name__ == "__main__":
    agent = create_wrapped_agent(AIHedgeFundAgent)
    asyncio.run(agent.serve())
