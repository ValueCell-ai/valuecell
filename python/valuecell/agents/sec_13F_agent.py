import asyncio

from agno.agent import Agent, RunResponse, RunResponseEvent  # noqa
from agno.models.openrouter import OpenRouter
from edgar import Company, set_identity
from pydantic import BaseModel, Field, field_validator

# from valuecell.core.agent.decorator import serve
from valuecell.core.agent.types import BaseAgent
from valuecell.core.agent.decorator import create_wrapped_agent


class Sec13FundRequest(BaseModel):
    ticker: str = Field(
        ...,
        description="Stock ticker symbol to analyze (e.g., 'AAPL', 'TSLA'). Only one ticker symbol is allowed per request.",
    )

    @field_validator("ticker")
    @classmethod
    def validate_tickers(cls, v):
        return v


# @serve(name="sec13fundAgent")
class Sec13FundAgent(BaseAgent):
    """
    A simple agent that uses the SEC API to retrieve information about a company.
    """

    def __init__(self):
        super().__init__()
        # 用于解析查询的Agent
        self.parser_agent = Agent(
            model=OpenRouter(id="openai/gpt-5-mini"),
            response_model=Sec13FundRequest,
            markdown=True,
        )
        # 用于分析的Agent
        self.analysis_agent = Agent(
            model=OpenRouter(id="deepseek/deepseek-chat-v3-0324"),
            markdown=True,
        )

    async def stream(self, query, session_id, task_id):
        run_response = self.parser_agent.run(
            f"Parse the following sec 13 funds request and extract the parameters: {query}"
        )
        sec_13_fund_request = run_response.content
        company_name = sec_13_fund_request.ticker

        set_identity("your.name@example.com")
        # %%
        brk = Company(company_name)
        filings = brk.get_filings(form="13F-HR").head(3)

        # %%
        o = filings[1].obj()
        current = o.infotable.to_json()

        # %%
        o = filings[2].obj()
        pre = o.infotable.to_json()

        analysis_prompt = f"""
        As a professional investment analyst, please conduct an in-depth analysis of the following 13F holdings data:
    
        ## Previous Holdings Data:
        {pre}
    
        ## Current Holdings Data:
        {current}
    
        ## Analysis Requirements:
        Please provide professional analysis from the following perspectives:
    
        ### 1. Holdings Changes Summary
        - New Positions: List newly acquired stocks and potential investment rationale
        - Exits/Reductions: Analyze divested stocks and speculated reasons
        - Position Adjustments: Focus on stocks with position changes exceeding 20%
    
        ### 2. Sector Allocation Analysis
        - Sector Weight Changes: Adjustments in sector allocation percentages
        - Investment Preferences: Changes in sector preferences reflected by capital flows
        - Concentration Changes: Adjustments in portfolio concentration
    
        ### 3. Key Holdings Analysis
        - Specific changes in top 10 holdings
        - Calculate increase/decrease percentages for major positions
        - Analyze possible reasons for significant position adjustments
    
        ### 4. Investment Strategy Insights
        - Investment style adjustments reflected in holdings changes
        - Market trend judgments and responses
        - Changes in risk appetite
    
        ## Output Requirements:
        Please output analysis results in a clear structure, including:
        - 📊 **Key Findings**: 3-5 critical insights
        - 📈 **Important Data**: Specific change data and percentages
        - 🎯 **Investment Insights**: Reference value for investors
        - ⚠️ **Risk Alerts**: Risk points that need attention
    
        Please ensure the analysis is objective and professional, based on factual data, avoiding excessive speculation.
        """

        result = self.analysis_agent.run(analysis_prompt)

        yield {
            "content": result.content,
            "is_task_complete": True,
        }


if __name__ == "__main__":
    agent = create_wrapped_agent(Sec13FundAgent)
    asyncio.run(agent.serve())
