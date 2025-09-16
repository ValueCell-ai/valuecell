import asyncio
import logging
import os

from agno.agent import Agent, RunResponse, RunResponseEvent  # noqa
from agno.models.openrouter import OpenRouter
from edgar import Company, set_identity
from pydantic import BaseModel, Field, field_validator

from valuecell.core.agent.types import BaseAgent
from valuecell.core.agent.decorator import create_wrapped_agent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Sec13FundRequest(BaseModel):
    ticker: str = Field(
        ...,
        description="Stock ticker symbol to analyze (e.g., 'AAPL', 'TSLA'). Only one ticker symbol is allowed per request.",
    )

    @field_validator("ticker")
    @classmethod
    def validate_tickers(cls, v):
        if not v or not isinstance(v, str):
            raise ValueError("Ticker must be a non-empty string")
        return v.upper().strip()


class Sec13FundAgentConfig:
    """Configuration management class for SEC 13F Agent"""

    def __init__(self):
        self.sec_email = os.getenv("SEC_EMAIL", "your.name@example.com")
        self.parser_model_id = os.getenv("SEC_PARSER_MODEL_ID", "openai/gpt-4o-mini")
        self.analysis_model_id = os.getenv(
            "SEC_ANALYSIS_MODEL_ID", "deepseek/deepseek-chat-v3-0324"
        )
        self.max_filings = int(os.getenv("SEC_MAX_FILINGS", "5"))
        self.request_timeout = int(os.getenv("SEC_REQUEST_TIMEOUT", "30"))


# @serve(name="sec13fundAgent")
class Sec13FundAgent(BaseAgent):
    """
    A simple agent that uses the SEC API to retrieve information about a company.
    """

    def __init__(self):
        super().__init__()
        self.config = Sec13FundAgentConfig()

        try:
            # Agent for parsing queries
            self.parser_agent = Agent(
                model=OpenRouter(id=self.config.parser_model_id),
                response_model=Sec13FundRequest,
                markdown=True,
            )
            # Agent for analysis
            self.analysis_agent = Agent(
                model=OpenRouter(id=self.config.analysis_model_id),
                markdown=True,
            )
            logger.info("SEC 13F Agent initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize SEC 13F Agent: {e}")
            raise

    async def stream(self, query: str, session_id: str, task_id: str):
        """
        Main method for processing SEC 13F analysis requests
        """
        try:
            # 1. Parse query parameters
            logger.info(
                f"Processing SEC 13F request for session {session_id}, task {task_id}"
            )

            try:
                run_response = self.parser_agent.run(
                    f"Parse the following sec 13 funds request and extract the parameters: {query}"
                )
                sec_13_fund_request = run_response.content
                company_name = sec_13_fund_request.ticker
                logger.info(f"Parsed ticker: {company_name}")
            except Exception as e:
                logger.error(f"Failed to parse query: {e}")
                yield {
                    "content": f"❌ **Parse Error**: Unable to parse query parameters. Please ensure you provide a valid stock ticker.\nError details: {str(e)}",
                    "is_task_complete": True,
                }
                return

            # 2. Set SEC identity and get company data
            try:
                set_identity(self.config.sec_email)
                company = Company(company_name)
                logger.info(f"Created company object for {company_name}")
            except Exception as e:
                logger.error(f"Failed to create company object: {e}")
                yield {
                    "content": f"❌ **Company Query Error**: Unable to find company for ticker '{company_name}'.\nError details: {str(e)}",
                    "is_task_complete": True,
                }
                return

            # 3. Get 13F-HR filings
            try:
                filings = company.get_filings(form="13F-HR").head(
                    self.config.max_filings
                )
                if len(filings) < 2:
                    yield {
                        "content": f"❌ **Insufficient Data**: Company '{company_name}' has insufficient 13F-HR filings (at least 2 filings required for comparison analysis).",
                        "is_task_complete": True,
                    }
                    return
                logger.info(f"Retrieved {len(filings)} filings for {company_name}")
            except Exception as e:
                logger.error(f"Failed to get filings: {e}")
                yield {
                    "content": f"❌ **Filing Retrieval Error**: Unable to retrieve 13F-HR filings for company '{company_name}'.\nError details: {str(e)}",
                    "is_task_complete": True,
                }
                return

            # 4. Parse filing data (fixed data order logic)
            try:
                # Get the latest filing (index 0 is the most recent)
                current_filing = filings.iloc[0].obj()
                current_data = current_filing.infotable.to_json()

                # Get the previous filing (index 1 is the previous period)
                previous_filing = filings.iloc[1].obj()
                previous_data = previous_filing.infotable.to_json()

                logger.info("Successfully parsed current and previous holdings data")
            except Exception as e:
                logger.error(f"Failed to parse filing data: {e}")
                yield {
                    "content": f"❌ **Data Parsing Error**: Unable to parse 13F-HR filing data.\nError details: {str(e)}",
                    "is_task_complete": True,
                }
                return

            # 5. Generate analysis report
            try:
                analysis_prompt = f"""
                As a professional investment analyst, please conduct an in-depth analysis of the following 13F holdings data:
            
                ## Previous Holdings Data (Earlier Period):
                {previous_data}
            
                ## Current Holdings Data (Latest Period):
                {current_data}
            
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
                logger.info("Analysis completed successfully")

                yield {
                    "content": result.content,
                    "is_task_complete": True,
                }

            except Exception as e:
                logger.error(f"Failed to generate analysis: {e}")
                yield {
                    "content": f"❌ **Analysis Generation Error**: Unable to generate analysis report.\nError details: {str(e)}",
                    "is_task_complete": True,
                }
                return

        except Exception as e:
            logger.error(f"Unexpected error in stream method: {e}")
            yield {
                "content": f"❌ **System Error**: An unexpected error occurred while processing the request.\nError details: {str(e)}",
                "is_task_complete": True,
            }


if __name__ == "__main__":
    agent = create_wrapped_agent(Sec13FundAgent)
    asyncio.run(agent.serve())
