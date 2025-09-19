import asyncio
import logging
import os
from enum import Enum

from agno.agent import Agent, RunResponse, RunResponseEvent  # noqa
from agno.models.openrouter import OpenRouter
from edgar import Company, set_identity
from pydantic import BaseModel, Field, field_validator

from valuecell.core.types import BaseAgent
from valuecell.core.agent.decorator import create_wrapped_agent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class QueryType(str, Enum):
    """Query type enumeration"""

    FINANCIAL_DATA = "financial_data"  # Financial data queries (10-K, 8-K, 10-Q)
    FUND_HOLDINGS = "fund_holdings"  # 13F fund holdings queries


class SecRequest(BaseModel):
    """Unified SEC query request model"""

    ticker: str = Field(
        ...,
        description="Stock ticker symbol to analyze (e.g., 'AAPL', 'TSLA'). Only one ticker symbol is allowed per request.",
    )
    query_type: QueryType = Field(
        ...,
        description="Type of SEC data to query: 'financial_data' for 10-K/8-K/10-Q filings, 'fund_holdings' for 13F holdings analysis",
    )

    @field_validator("ticker")
    @classmethod
    def validate_ticker(cls, v):
        if not v or not isinstance(v, str):
            raise ValueError("Ticker must be a non-empty string")
        return v.upper().strip()


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


class SecAgent(BaseAgent):
    """
    Intelligent SEC analysis agent supporting financial data queries and 13F fund holdings analysis
    """

    def __init__(self):
        super().__init__()
        self.config = Sec13FundAgentConfig()

        try:
            # Query classification agent - for determining query type
            self.classifier_agent = Agent(
                model=OpenRouter(id=self.config.parser_model_id),
                response_model=SecRequest,
                markdown=True,
            )
            # Traditional 13F parsing agent - maintains backward compatibility
            self.parser_agent = Agent(
                model=OpenRouter(id=self.config.parser_model_id),
                response_model=Sec13FundRequest,
                markdown=True,
            )
            # Analysis agent
            self.analysis_agent = Agent(
                model=OpenRouter(id=self.config.analysis_model_id),
                markdown=True,
            )
            logger.info("SEC intelligent analysis agent initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize SEC Agent: {e}")
            raise

    async def _classify_query(self, query: str) -> QueryType:
        """
        Intelligently classify user queries to determine if it's financial data or 13F query
        """
        classification_prompt = f"""
        Please analyze the following user query and determine what type of SEC data the user wants to obtain:

        User query: "{query}"

        Please judge the user's intent based on the query content:
        1. If the user explicitly wants to understand company financial data, financial statements, annual reports, quarterly reports, major events, etc., choose "financial_data"
        2. If the user explicitly wants to understand 13F fund holdings, institutional investor holding changes, fund shareholding situations, etc., choose "fund_holdings"

        Keyword hints:
        - Financial data related: financial statements, annual reports, quarterly reports, 10-K, 8-K, 10-Q, financial condition, revenue, profit, balance sheet, cash flow
        - 13F holdings related: fund holdings, institutional investors, shareholding changes, 13F, fund shareholding, investment portfolio

        Please extract the stock ticker and determine the query type.
        """

        try:
            response = self.classifier_agent.run(classification_prompt)
            return response.content.query_type
        except Exception as e:
            logger.warning(
                f"Query classification failed, defaulting to 13F analysis: {e}"
            )
            # If classification fails, default to 13F analysis (maintains backward compatibility)
            return QueryType.FUND_HOLDINGS

    async def _process_financial_data_query(
        self, ticker: str, session_id: str, task_id: str
    ):
        """
        Process financial data queries (10-K, 8-K, 10-Q)
        """
        try:
            # Set SEC identity
            set_identity(self.config.sec_email)
            company = Company(ticker)
            logger.info(f"Starting financial data query for {ticker}")

            # Get different types of financial filings
            filing_types = ["10-K", "8-K", "10-Q", "4"]
            all_filings_data = {}

            for filing_type in filing_types:
                try:
                    filings = company.get_filings(form=filing_type).head(3)
                    if len(filings) > 0:
                        all_filings_data[filing_type] = []
                        for i, filing in filings.iterrows():
                            filing_info = {
                                "date": filing.filing_date,
                                "accession_number": filing.accession_number,
                                "form": filing.form,
                            }
                            all_filings_data[filing_type].append(filing_info)
                        logger.info(f"Retrieved {len(filings)} {filing_type} filings")
                except Exception as e:
                    logger.warning(f"Failed to retrieve {filing_type} filings: {e}")
                    continue

            if not all_filings_data:
                yield {
                    "content": f"❌ **Insufficient Data**: No financial filings found for company '{ticker}'.",
                    "is_task_complete": True,
                }
                return

            # Generate financial data analysis report
            analysis_prompt = f"""
            As a professional financial analyst, please analyze the following company's SEC financial filings:

            Company ticker: {ticker}
            
            ## Available financial filings:
            {all_filings_data}

            ## Analysis requirements:
            Please provide professional analysis from the following perspectives:

            ### 1. Financial Filing Overview
            - Latest 10-K annual report status
            - Latest 10-Q quarterly report status  
            - Important 8-K event disclosures

            ### 2. Filing Timeline Analysis
            - Time distribution of filing documents
            - Filing frequency and timeliness

            ### 3. Key Financial Events
            - Major events identified from 8-K filings
            - Important information that may affect investment decisions

            ### 4. Investment Recommendations
            - Investment references based on filing documents
            - Risk points that need attention

            ## Output requirements:
            Please output analysis results in a clear structure, including:
            - 📊 **Key Findings**: 3-5 important insights
            - 📈 **Financial Highlights**: Important financial data and trends
            - 🎯 **Investment Reference**: Reference value for investors
            - ⚠️ **Risk Alerts**: Risk points that need attention

            Please ensure the analysis is objective and professional, based on actual data, avoiding excessive speculation.
            """

            result = self.analysis_agent.run(analysis_prompt)
            logger.info("Financial data analysis completed")

            yield {
                "content": result.content,
                "is_task_complete": True,
            }

        except Exception as e:
            logger.error(f"Financial data query failed: {e}")
            yield {
                "content": f"❌ **Financial Data Query Error**: Unable to retrieve financial data for company '{ticker}'.\nError details: {str(e)}",
                "is_task_complete": True,
            }

    async def _process_fund_holdings_query(
        self, ticker: str, session_id: str, task_id: str
    ):
        """
        Process 13F fund holdings queries (original logic)
        """
        try:
            # Set SEC identity
            set_identity(self.config.sec_email)
            company = Company(ticker)
            logger.info(f"Starting 13F holdings data query for {ticker}")

            # Get 13F-HR filings
            filings = company.get_filings(form="13F-HR").head(self.config.max_filings)
            if len(filings) < 2:
                yield {
                    "content": f"❌ **Insufficient Data**: Company '{ticker}' has insufficient 13F-HR filings (at least 2 filings required for comparison analysis).",
                    "is_task_complete": True,
                }
                return
            logger.info(f"Retrieved {len(filings)} 13F filings")

            # %%
            o = filings[1].obj()
            current_filing = o.infotable.to_json()

            # %%
            o = filings[2].obj()
            previous_filing = o.infotable.to_json()




            logger.info("Successfully parsed current and historical holdings data")

            # Generate 13F analysis report
            analysis_prompt = f"""
            As a professional investment analyst, please conduct an in-depth analysis of the following 13F holdings data:

            ## Historical holdings data (earlier period):
            {previous_filing}

            ## Current holdings data (latest period):
            {current_filing}

            ## Analysis requirements:
            Please provide professional analysis from the following perspectives:

            ### 1. Holdings Changes Summary
            - New positions: List newly purchased stocks and possible investment rationale
            - Exits/reductions: Analyze sold stocks and speculated reasons
            - Position adjustments: Focus on stocks with position changes exceeding 20%

            ### 2. Sector Allocation Analysis
            - Sector weight changes: Adjustments in sector allocation percentages
            - Investment preferences: Changes in sector preferences reflected by capital flows
            - Concentration changes: Adjustments in portfolio concentration

            ### 3. Key Holdings Analysis
            - Specific changes in top 10 holdings
            - Calculate increase/decrease percentages for major positions
            - Analyze possible reasons for significant position adjustments

            ### 4. Investment Strategy Insights
            - Investment style adjustments reflected in holdings changes
            - Market trend judgments and responses
            - Changes in risk appetite

            ## Output requirements:
            Please output analysis results in a clear structure, including:
            - 📊 **Key Findings**: 3-5 important insights
            - 📈 **Important Data**: Specific change data and percentages
            - 🎯 **Investment Insights**: Reference value for investors
            - ⚠️ **Risk Alerts**: Risk points that need attention

            Please ensure the analysis is objective and professional, based on actual data, avoiding excessive speculation.
            """

            result = self.analysis_agent.run(analysis_prompt)
            logger.info("13F analysis completed")

            yield {
                "content": result.content,
                "is_task_complete": True,
            }

        except Exception as e:
            logger.error(f"13F query failed: {e}")
            yield {
                "content": f"❌ **13F Query Error**: Unable to retrieve 13F data for company '{ticker}'.\nError details: {str(e)}",
                "is_task_complete": True,
            }

    async def stream(self, query: str, session_id: str, task_id: str):
        """
        Main streaming method with intelligent routing support
        """
        try:
            logger.info(
                f"Processing SEC query request - session: {session_id}, task: {task_id}"
            )

            # 1. Intelligent query classification
            try:
                query_type = await self._classify_query(query)
                logger.info(f"Query classification result: {query_type}")
            except Exception as e:
                logger.error(f"Query classification failed: {e}")
                yield {
                    "content": f"❌ **Classification Error**: Unable to analyze query type.\nError details: {str(e)}",
                    "is_task_complete": True,
                }
                return

            # 2. Extract stock ticker
            try:
                if query_type == QueryType.FINANCIAL_DATA:
                    # Use new classification agent to extract stock ticker
                    classification_prompt = f"""
                    Please extract the stock ticker from the following query: "{query}"
                    Please set query_type to "financial_data" and extract the ticker.
                    """
                    response = self.classifier_agent.run(classification_prompt)
                    ticker = response.content.ticker
                else:
                    # Use original parsing agent (maintains backward compatibility)
                    run_response = self.parser_agent.run(
                        f"Parse the following sec 13 funds request and extract the parameters: {query}"
                    )
                    ticker = run_response.content.ticker

                logger.info(f"Extracted stock ticker: {ticker}")
            except Exception as e:
                logger.error(f"Stock ticker extraction failed: {e}")
                yield {
                    "content": f"❌ **Parse Error**: Unable to parse query parameters. Please ensure you provide a valid stock ticker.\nError details: {str(e)}",
                    "is_task_complete": True,
                }
                return

            # 3. Route to appropriate processing method based on query type
            if query_type == QueryType.FINANCIAL_DATA:
                async for result in self._process_financial_data_query(
                    ticker, session_id, task_id
                ):
                    yield result
            else:  # QueryType.FUND_HOLDINGS
                async for result in self._process_fund_holdings_query(
                    ticker, session_id, task_id
                ):
                    yield result

        except Exception as e:
            logger.error(f"Unexpected error in stream method: {e}")
            yield {
                "content": f"❌ **System Error**: An unexpected error occurred while processing the request.\nError details: {str(e)}",
                "is_task_complete": True,
            }


if __name__ == "__main__":
    agent = create_wrapped_agent(SecAgent)
    asyncio.run(agent.serve())
