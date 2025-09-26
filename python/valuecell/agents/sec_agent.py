import asyncio
import hashlib
import logging
import os
from datetime import datetime
from enum import Enum
from typing import AsyncGenerator, Dict, Iterator

from agno.agent import Agent, RunResponseEvent
from agno.models.openrouter import OpenRouter
from edgar import Company, set_identity
from pydantic import BaseModel, Field, field_validator

from valuecell.core.agent.decorator import create_wrapped_agent
from valuecell.core.agent.responses import notification, streaming
from valuecell.core.types import BaseAgent, StreamResponse

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
            "SEC_ANALYSIS_MODEL_ID", "google/gemini-2.5-pro"
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

        # Monitoring state management
        self.monitoring_sessions: Dict[str, Dict] = {}  # session_id -> monitoring_info
        self.filing_cache: Dict[str, Dict] = {}  # ticker -> filing_hashes

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
                model=OpenRouter(id=self.config.analysis_model_id, max_tokens=None),
                markdown=True,
            )
            logger.info("SEC intelligent analysis agent initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize SEC Agent: {e}")
            raise

    async def _extract_ticker_from_query(self, query: str) -> str:
        """Extract ticker symbol from user query using AI"""
        try:
            extraction_prompt = f"""
            Extract the stock ticker symbol from the following query: "{query}"
            
            Rules:
            - Return only the ticker symbol (e.g., "AAPL", "TSLA", "MSFT")
            - If multiple tickers are mentioned, return the first one
            - If no ticker is found, return "UNKNOWN"
            - The ticker should be in uppercase
            
            Query: {query}
            """

            response = await self.analysis_agent.arun(extraction_prompt)
            ticker = response.content.strip().upper()

            # Basic validation
            if ticker == "UNKNOWN" or len(ticker) > 10:
                raise ValueError(f"Invalid ticker extracted: {ticker}")

            logger.info(f"Extracted ticker: {ticker} from query: {query}")
            return ticker

        except Exception as e:
            logger.error(f"Failed to extract ticker from query: {e}")
            raise ValueError(f"Could not extract valid ticker from query: {query}")

    async def _get_sec_filings(self, ticker: str) -> Dict[str, str]:
        """Get current SEC filings for a ticker and return their hashes"""
        try:
            set_identity(self.config.sec_email)
            company = Company(ticker)

            filings_data = {}
            filing_types = ["10-K", "8-K", "10-Q", "13F-HR"]

            for filing_type in filing_types:
                try:
                    # Get the most recent filing of this type
                    filing = company.get_filings(form=filing_type).latest()
                    if filing:
                        # Create a hash of the filing content/metadata
                        filing_content = f"{filing.accession_number}_{filing.filing_date}_{filing.form}"
                        filing_hash = hashlib.md5(filing_content.encode()).hexdigest()
                        filings_data[filing_type] = filing_hash
                        logger.info(
                            f"Found {filing_type} filing for {ticker}: {filing.accession_number}"
                        )
                    else:
                        filings_data[filing_type] = None
                        logger.info(f"No {filing_type} filing found for {ticker}")
                except Exception as e:
                    logger.warning(f"Error getting {filing_type} for {ticker}: {e}")
                    filings_data[filing_type] = None

            return filings_data

        except Exception as e:
            logger.error(f"Failed to get SEC filings for {ticker}: {e}")
            return {}

    async def _detect_filing_changes(
        self, ticker: str, current_filings: Dict[str, str]
    ) -> Dict[str, bool]:
        """Detect changes in SEC filings compared to cached versions"""
        changes = {}

        if ticker not in self.filing_cache:
            # First time checking this ticker
            self.filing_cache[ticker] = current_filings.copy()
            # Consider all existing filings as "new" for first check
            for filing_type, filing_hash in current_filings.items():
                changes[filing_type] = filing_hash is not None
        else:
            # Compare with cached versions
            cached_filings = self.filing_cache[ticker]
            for filing_type, current_hash in current_filings.items():
                cached_hash = cached_filings.get(filing_type)
                changes[filing_type] = (
                    current_hash != cached_hash and current_hash is not None
                )

            # Update cache
            self.filing_cache[ticker] = current_filings.copy()

        return changes

    async def _generate_filing_summary(
        self, ticker: str, changed_filings: Dict[str, bool]
    ) -> str:
        """Generate AI summary of filing changes"""
        try:
            changed_types = [
                filing_type
                for filing_type, changed in changed_filings.items()
                if changed
            ]

            if not changed_types:
                return f"No new filings detected for {ticker}."

            summary_prompt = f"""
            New SEC filings have been detected for {ticker}. The following filing types have been updated:
            {", ".join(changed_types)}
            
            Please provide a brief summary of what these filing types typically contain and their significance for investors:
            
            - 10-K: Annual report with comprehensive business overview
            - 8-K: Current report for material events
            - 10-Q: Quarterly financial report
            - 13F-HR: Institutional investment holdings report
            
            Focus on explaining what investors should pay attention to with these new {ticker} filings.
            Keep the summary concise but informative (2-3 paragraphs maximum).
            """

            response = await self.analysis_agent.arun(summary_prompt)
            return response.content

        except Exception as e:
            logger.error(f"Failed to generate filing summary: {e}")
            return f"New filings detected for {ticker}: {', '.join(changed_types)}, but summary generation failed."

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
            response = await self.classifier_agent.arun(classification_prompt)
            return response.content.query_type
        except Exception as e:
            logger.warning(
                f"Query classification failed, defaulting to 13F analysis: {e}"
            )
            # If classification fails, default to 13F analysis (maintains backward compatibility)
            return QueryType.FUND_HOLDINGS

    async def _process_financial_data_query(self, ticker: str):
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
                yield streaming.failed(
                    f"**Insufficient Data**: No financial filings found for company '{ticker}'."
                )
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
            -  **Key Findings**: 3-5 important insights
            -  **Financial Highlights**: Important financial data and trends
            -  **Investment Reference**: Reference value for investors
            -  **Risk Alerts**: Risk points that need attention

            Please ensure the analysis is objective and professional, based on actual data, avoiding excessive speculation.
            """

            response_stream: Iterator[
                RunResponseEvent
            ] = await self.analysis_agent.arun(
                analysis_prompt, stream=True, stream_intermediate_steps=True
            )
            async for event in response_stream:
                if event.event == "RunResponseContent":
                    yield streaming.message_chunk(event.content)
                elif event.event == "ToolCallStarted":
                    yield streaming.tool_call_started(
                        event.tool.tool_call_id, event.tool.tool_name
                    )
                elif event.event == "ToolCallCompleted":
                    yield streaming.tool_call_completed(
                        event.tool.result, event.tool.tool_call_id, event.tool.tool_name
                    )
            logger.info("Financial data analysis completed")

            yield streaming.done()
        except Exception as e:
            yield streaming.failed(f"Financial data query failed: {e}")

    async def _process_fund_holdings_query(self, ticker: str):
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
                yield streaming.failed(
                    f"**Insufficient Data**: Company '{ticker}' has insufficient 13F-HR filings (at least 2 filings required for comparison analysis)."
                )
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
            -  **Key Findings**: 3-5 important insights
            -  **Important Data**: Specific change data and percentages
            -  **Investment Insights**: Reference value for investors
            -  **Risk Alerts**: Risk points that need attention

            Please ensure the analysis is objective and professional, based on actual data, avoiding excessive speculation.
            """

            response_stream: Iterator[
                RunResponseEvent
            ] = await self.analysis_agent.arun(
                analysis_prompt, stream=True, stream_intermediate_steps=True
            )
            async for event in response_stream:
                if event.event == "RunResponseContent":
                    yield streaming.message_chunk(event.content)
                elif event.event == "ToolCallStarted":
                    yield streaming.tool_call_started(
                        event.tool.tool_call_id, event.tool.tool_name
                    )
                elif event.event == "ToolCallCompleted":
                    yield streaming.tool_call_completed(
                        event.tool.result, event.tool.tool_call_id, event.tool.tool_name
                    )
            logger.info("Financial data analysis completed")

            streaming.done()
            logger.info("13F analysis completed")
        except Exception as e:
            yield streaming.failed(f"13F query failed: {e}")

    async def stream(
        self, query: str, session_id: str, task_id: str
    ) -> AsyncGenerator[StreamResponse, None]:
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
                yield streaming.failed(
                    "**Classification Error**: Unable to analyze query type."
                )
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
                yield streaming.failed(
                    "**Parse Error**: Unable to parse query parameters. Please ensure you provide a valid stock ticker."
                )
                return

            # 3. Route to appropriate processing method based on query type
            if query_type == QueryType.FINANCIAL_DATA:
                async for result in self._process_financial_data_query(ticker):
                    yield result
            else:  # QueryType.FUND_HOLDINGS
                async for result in self._process_fund_holdings_query(ticker):
                    yield result

        except Exception as e:
            logger.error(f"Unexpected error in stream method: {e}")
            yield streaming.failed(f"Unexpected error: {e}")

    async def notify(self, query: str, session_id: str, task_id: str):
        """
        Main notify method with continuous SEC filing monitoring
        """
        try:
            logger.info(
                f"Starting SEC filing monitoring - session: {session_id}, task: {task_id}"
            )

            # 1. Extract ticker from query
            try:
                ticker = await self._extract_ticker_from_query(query)
                logger.info(f"Extracted ticker: {ticker}")
            except Exception as e:
                logger.error(f"Ticker extraction failed: {e}")
                yield notification.failed(
                    "**Parse Error**: Unable to parse query parameters. Please ensure you provide a valid stock ticker."
                )
                return

            # 2. Initialize monitoring session
            self.monitoring_sessions[session_id] = {
                "ticker": ticker,
                "start_time": datetime.now(),
                "check_count": 0,
                "last_check": None,
            }

            check_interval = 30  # Check every 30 seconds (can be configured)

            while session_id in self.monitoring_sessions:
                try:
                    # Get current filings
                    current_filings = await self._get_sec_filings(ticker)

                    if current_filings:
                        # Detect changes
                        changes = await self._detect_filing_changes(
                            ticker, current_filings
                        )

                        # Update monitoring session
                        self.monitoring_sessions[session_id]["check_count"] += 1
                        self.monitoring_sessions[session_id]["last_check"] = (
                            datetime.now()
                        )

                        # Check if there are any changes
                        if any(changes.values()):
                            # Generate summary of changes
                            summary = await self._generate_filing_summary(
                                ticker, changes
                            )

                            yield notification.component_generator(summary, "sec_feed")

                    # Wait before next check
                    await asyncio.sleep(check_interval)

                except Exception as e:
                    logger.error(f"Error during monitoring check: {e}")
                    yield notification.failed(str(e))
                    await asyncio.sleep(check_interval)

        except Exception as e:
            logger.error(f"Unexpected error in notify method: {e}")
            yield notification.failed(str(e))
        finally:
            # Clean up monitoring session
            if session_id in self.monitoring_sessions:
                del self.monitoring_sessions[session_id]

    def stop_monitoring(self, session_id: str) -> bool:
        """Stop monitoring for a specific session"""
        if session_id in self.monitoring_sessions:
            del self.monitoring_sessions[session_id]
            logger.info(f"Stopped monitoring for session: {session_id}")
            return True
        return False

    def get_monitoring_status(self, session_id: str) -> Dict:
        """Get current monitoring status for a session"""
        return self.monitoring_sessions.get(session_id, {})


if __name__ == "__main__":
    agent = create_wrapped_agent(SecAgent)
    asyncio.run(agent.serve())
