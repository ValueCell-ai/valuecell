"""Main auto trading agent implementation with multi-instance support"""

import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Dict, Optional

from agno.agent import Agent
from agno.models.openrouter import OpenRouter

from valuecell.core.agent.responses import streaming
from valuecell.core.types import (
    BaseAgent,
    FilteredCardPushNotificationComponentData,
    FilteredLineChartComponentData,
    StreamResponse,
)

from .constants import (
    DEFAULT_AGENT_MODEL,
    DEFAULT_CHECK_INTERVAL,
    PORTFOLIO_COMPONENT_TYPE,
    TRADING_COMPONENT_TYPE,
)
from .formatters import MessageFormatter
from .models import (
    AutoTradingConfig,
    TradeAction,
    TradingRequest,
)
from .technical_analysis import AISignalGenerator, TechnicalAnalyzer
from .trading_executor import TradingExecutor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AutoTradingAgent(BaseAgent):
    """
    Automated crypto trading agent with technical analysis and position management.
    Supports multiple trading instances per session with independent configurations.
    """

    def __init__(self):
        super().__init__()

        # Configuration
        self.parser_model_id = os.getenv("TRADING_PARSER_MODEL_ID", DEFAULT_AGENT_MODEL)

        # Multi-instance state management
        # Structure: {session_id: {instance_id: TradingInstanceData}}
        self.trading_instances: Dict[str, Dict[str, Dict[str, Any]]] = {}

        try:
            # Parser agent for natural language query parsing
            self.parser_agent = Agent(
                model=OpenRouter(id=self.parser_model_id),
                output_schema=TradingRequest,
                markdown=True,
            )
            logger.info("Auto Trading Agent initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Auto Trading Agent: {e}")
            raise

    def _generate_instance_id(self, task_id: str) -> str:
        """Generate unique instance ID"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"trade_{timestamp}_{task_id[:8]}"

    async def _parse_trading_request(self, query: str) -> TradingRequest:
        """
        Parse natural language query to extract trading parameters

        Args:
            query: User's natural language query

        Returns:
            TradingRequest object with parsed parameters
        """
        try:
            parse_prompt = f"""
            Parse the following user query and extract auto trading configuration parameters:
            
            User query: "{query}"
            
            Please identify:
            1. crypto_symbols: List of cryptocurrency symbols to trade (e.g., BTC-USD, ETH-USD, SOL-USD)
               - If user mentions "Bitcoin", extract as "BTC-USD"
               - If user mentions "Ethereum", extract as "ETH-USD"
               - If user mentions "Solana", extract as "SOL-USD"
               - Always use format: SYMBOL-USD
            2. initial_capital: Initial trading capital in USD (default: 100000 if not specified)
            3. use_ai_signals: Whether to use AI-enhanced signals (default: true)
            4. agent_model: Model ID for trading decisions (default: DEFAULT_AGENT_MODEL)
            
            Examples:
            - "Trade Bitcoin and Ethereum with $50000" -> {{"crypto_symbols": ["BTC-USD", "ETH-USD"], "initial_capital": 50000, "use_ai_signals": true}}
            - "Start auto trading BTC-USD" -> {{"crypto_symbols": ["BTC-USD"], "initial_capital": 100000, "use_ai_signals": true}}
            - "Trade BTC with AI signals" -> {{"crypto_symbols": ["BTC-USD"], "initial_capital": 100000, "use_ai_signals": true}}
            - "Trade BTC with AI signals using DeepSeek model" -> {{"crypto_symbols": ["BTC-USD"], "initial_capital": 100000, "use_ai_signals": true, "agent_model": "deepseek/deepseek-v3.1-terminus"}}
            - "Trade Bitcoin, SOL, Eth and DOGE with 100000 capital, using x-ai/grok-4 model" -> {{"crypto_symbols": ["BTC-USD", "SOL-USD", "ETH-USD", "DOGE-USD"], "initial_capital": 100000, "use_ai_signals": true, "agent_model": "x-ai/grok-4"}}
            """

            response = await self.parser_agent.arun(parse_prompt)
            trading_request = response.content

            logger.info(f"Parsed trading request: {trading_request}")
            return trading_request

        except Exception as e:
            logger.error(f"Failed to parse trading request: {e}")
            raise ValueError(
                f"Could not parse trading configuration from query: {query}"
            )

    def _initialize_ai_signal_generator(
        self, config: AutoTradingConfig
    ) -> Optional[AISignalGenerator]:
        """Initialize AI signal generator if configured"""
        if not config.use_ai_signals:
            return None

        try:
            api_key = config.openrouter_api_key or os.getenv("OPENROUTER_API_KEY")
            if not api_key:
                logger.warning("OpenRouter API key not provided, AI signals disabled")
                return None

            llm_client = OpenRouter(
                id=config.agent_model,
                api_key=api_key,
            )
            return AISignalGenerator(llm_client)

        except Exception as e:
            logger.error(f"Failed to initialize AI signal generator: {e}")
            return None

    def _get_instance_status_component_data(
        self, session_id: str, instance_id: str
    ) -> str:
        """
        Generate FilteredCardPushNotificationComponentData for an instance

        Returns:
            JSON string of FilteredCardPushNotificationComponentData
        """
        if session_id not in self.trading_instances:
            return ""

        if instance_id not in self.trading_instances[session_id]:
            return ""

        instance = self.trading_instances[session_id][instance_id]
        executor: TradingExecutor = instance["executor"]
        config: AutoTradingConfig = instance["config"]

        # Prepare current positions data
        positions_data = []
        for symbol, pos in executor.positions.items():
            try:
                import yfinance as yf

                ticker = yf.Ticker(symbol)
                current_price = ticker.history(period="1d", interval="1m")[
                    "Close"
                ].iloc[-1]

                if pos.trade_type.value == "long":
                    unrealized_pnl = (current_price - pos.entry_price) * abs(
                        pos.quantity
                    )
                else:
                    unrealized_pnl = (pos.entry_price - current_price) * abs(
                        pos.quantity
                    )

                positions_data.append(
                    {
                        "Symbol": symbol,
                        "Type": pos.trade_type.value.upper(),
                        "Entry Price": f"${pos.entry_price:,.2f}",
                        "Current Price": f"${current_price:,.2f}",
                        "Quantity": f"{abs(pos.quantity):.4f}",
                        "Unrealized P&L": f"${unrealized_pnl:,.2f}",
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to get price for {symbol}: {e}")

        # Recent trade history (last 5 trades)
        trade_history = executor.get_trade_history()
        recent_trades = trade_history[-5:] if trade_history else []
        trades_data = []
        for trade in recent_trades:
            pnl_str = f"${trade.pnl:,.2f}" if trade.pnl is not None else "N/A"
            trades_data.append(
                {
                    "Time": trade.timestamp.strftime("%H:%M:%S"),
                    "Symbol": trade.symbol,
                    "Action": trade.action.upper(),
                    "Type": trade.trade_type.upper(),
                    "Price": f"${trade.price:,.2f}",
                    "P&L": pnl_str,
                }
            )

        # Portfolio summary
        portfolio_value = executor.get_portfolio_value()
        total_pnl = portfolio_value - config.initial_capital
        pnl_pct = (total_pnl / config.initial_capital) * 100

        component_data = FilteredCardPushNotificationComponentData(
            title=f"Trading Instance: {instance_id}",
            data=json.dumps(
                {
                    "summary": {
                        "Instance ID": instance_id,
                        "Model": config.agent_model,
                        "Symbols": ", ".join(config.crypto_symbols),
                        "Initial Capital": f"${config.initial_capital:,.2f}",
                        "Current Value": f"${portfolio_value:,.2f}",
                        "Total P&L": f"${total_pnl:,.2f} ({pnl_pct:+.2f}%)",
                        "Available Cash": f"${executor.current_capital:,.2f}",
                        "Open Positions": len(executor.positions),
                        "Total Trades": len(trade_history),
                        "Check Count": instance["check_count"],
                        "Status": "🟢 Active" if instance["active"] else "🔴 Stopped",
                    },
                    "current_positions": positions_data,
                    "recent_trades": trades_data,
                }
            ),
            filters=[config.agent_model],
            table_title="Instance Details",
            create_time=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
        )

        return component_data.model_dump_json()

    def _get_session_portfolio_chart_data(self, session_id: str) -> str:
        """
        Generate FilteredLineChartComponentData for all instances in a session

        Data format:
        [
            ['Time', 'model1', 'model2', 'model3'],
            ['2025-10-21 10:00:00', 100000, 50000, 30000],
            ['2025-10-21 10:01:00', 100234, 50123, 30045],
            ...
        ]

        Returns:
            JSON string of FilteredLineChartComponentData
        """
        if session_id not in self.trading_instances:
            return ""

        # Collect portfolio value history from all instances
        # Group by timestamp and model
        timestamp_data = {}  # {timestamp_str: {model_id: value}}
        model_ids = []

        for instance_id, instance in self.trading_instances[session_id].items():
            executor: TradingExecutor = instance["executor"]
            config: AutoTradingConfig = instance["config"]
            model_id = config.agent_model

            if model_id not in model_ids:
                model_ids.append(model_id)

            portfolio_history = executor.get_portfolio_history()

            for snapshot in portfolio_history:
                # Format timestamp as string
                timestamp_str = snapshot.timestamp.strftime("%Y-%m-%d %H:%M:%S")

                if timestamp_str not in timestamp_data:
                    timestamp_data[timestamp_str] = {}

                timestamp_data[timestamp_str][model_id] = snapshot.total_value

        if not timestamp_data:
            return ""

        # Build data array
        # First row: ['Time', 'model1', 'model2', ...]
        data_array = [["Time"] + model_ids]

        # Data rows: ['timestamp', value1, value2, ...]
        for timestamp_str in sorted(timestamp_data.keys()):
            row = [timestamp_str]
            for model_id in model_ids:
                # Use 0 if no data for this model at this timestamp
                value = timestamp_data[timestamp_str].get(model_id, 0)
                row.append(value)
            data_array.append(row)

        component_data = FilteredLineChartComponentData(
            title=f"Portfolio Value History - Session {session_id[:8]}",
            data=json.dumps(data_array),
            create_time=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
        )

        return component_data.model_dump_json()

    async def _handle_stop_command(
        self, session_id: str, query: str
    ) -> AsyncGenerator[StreamResponse, None]:
        """Handle stop command for trading instances"""
        query_lower = query.lower().strip()

        # Check if specific instance_id is provided
        instance_id = None
        if "instance_id:" in query_lower or "instance:" in query_lower:
            # Extract instance_id
            parts = query.split(":")
            if len(parts) >= 2:
                instance_id = parts[1].strip()

        if session_id not in self.trading_instances:
            yield streaming.message_chunk(
                "⚠️ No active trading instances found in this session.\n"
            )
            return

        if instance_id:
            # Stop specific instance
            if instance_id in self.trading_instances[session_id]:
                self.trading_instances[session_id][instance_id]["active"] = False
                executor = self.trading_instances[session_id][instance_id]["executor"]
                portfolio_value = executor.get_portfolio_value()

                yield streaming.message_chunk(
                    f"🛑 **Trading Instance Stopped**\n\n"
                    f"Instance ID: `{instance_id}`\n"
                    f"Final Portfolio Value: ${portfolio_value:,.2f}\n"
                    f"Open Positions: {len(executor.positions)}\n\n"
                )
            else:
                yield streaming.message_chunk(
                    f"⚠️ Instance ID '{instance_id}' not found.\n"
                )
        else:
            # Stop all instances in this session
            count = 0
            for inst_id in self.trading_instances[session_id]:
                self.trading_instances[session_id][inst_id]["active"] = False
                count += 1

            yield streaming.message_chunk(
                f"🛑 **All Trading Instances Stopped**\n\n"
                f"Stopped {count} instance(s) in session: {session_id[:8]}\n\n"
            )

    async def _handle_status_command(
        self, session_id: str
    ) -> AsyncGenerator[StreamResponse, None]:
        """Handle status query command"""
        if (
            session_id not in self.trading_instances
            or not self.trading_instances[session_id]
        ):
            yield streaming.message_chunk(
                "⚠️ No trading instances found in this session.\n"
            )
            return

        status_message = f"📊 **Session Status** - {session_id[:8]}\n\n"
        status_message += (
            f"**Total Instances:** {len(self.trading_instances[session_id])}\n\n"
        )

        for instance_id, instance in self.trading_instances[session_id].items():
            executor: TradingExecutor = instance["executor"]
            config: AutoTradingConfig = instance["config"]

            status = "🟢 Active" if instance["active"] else "🔴 Stopped"
            portfolio_value = executor.get_portfolio_value()
            total_pnl = portfolio_value - config.initial_capital

            status_message += (
                f"**Instance:** `{instance_id}`  {status}\n"
                f"- Model: {config.agent_model}\n"
                f"- Symbols: {', '.join(config.crypto_symbols)}\n"
                f"- Portfolio Value: ${portfolio_value:,.2f}\n"
                f"- P&L: ${total_pnl:,.2f}\n"
                f"- Open Positions: {len(executor.positions)}\n"
                f"- Total Trades: {len(executor.get_trade_history())}\n"
                f"- Checks: {instance['check_count']}\n\n"
            )

        yield streaming.message_chunk(status_message)

        # Send session-level portfolio chart
        chart_data = self._get_session_portfolio_chart_data(session_id)
        if chart_data:
            yield streaming.component_generator(chart_data, "line_chart")

    async def stream(
        self,
        query: str,
        session_id: str,
        task_id: str,
        dependencies: Optional[Dict] = None,
    ) -> AsyncGenerator[StreamResponse, None]:
        """
        Process trading requests and manage multiple trading instances per session.

        Args:
            query: User's natural language query
            session_id: Session ID
            task_id: Task ID
            dependencies: Optional dependencies

        Yields:
            StreamResponse: Trading setup, execution updates, and data visualizations
        """
        try:
            logger.info(
                f"Processing auto trading request - session: {session_id}, task: {task_id}"
            )

            query_lower = query.lower().strip()

            # Handle stop commands
            if any(
                cmd in query_lower for cmd in ["stop", "pause", "halt", "停止", "暂停"]
            ):
                async for response in self._handle_stop_command(session_id, query):
                    yield response
                return

            # Handle status query commands
            if any(cmd in query_lower for cmd in ["status", "summary", "状态", "摘要"]):
                async for response in self._handle_status_command(session_id):
                    yield response
                return

            # Parse natural language query to extract trading configuration
            yield streaming.message_chunk("🔍 **Parsing trading request...**\n\n")

            try:
                trading_request = await self._parse_trading_request(query)
                logger.info(f"Parsed request: {trading_request}")
            except Exception as e:
                logger.error(f"Failed to parse trading request: {e}")
                yield streaming.failed(
                    "**Parse Error**: Could not parse trading configuration from your query. "
                    "Please specify cryptocurrency symbols (e.g., 'Trade Bitcoin and Ethereum')."
                )
                return

            # Generate unique instance ID
            instance_id = self._generate_instance_id(task_id)

            # Create full configuration
            config = AutoTradingConfig(
                initial_capital=trading_request.initial_capital or 100000,
                crypto_symbols=trading_request.crypto_symbols,
                use_ai_signals=trading_request.use_ai_signals or False,
                agent_model=trading_request.agent_model or DEFAULT_AGENT_MODEL,
            )

            # Initialize executor
            executor = TradingExecutor(config)

            # Initialize AI signal generator if enabled
            ai_signal_generator = self._initialize_ai_signal_generator(config)

            # Initialize session structure if needed
            if session_id not in self.trading_instances:
                self.trading_instances[session_id] = {}

            # Store instance
            self.trading_instances[session_id][instance_id] = {
                "instance_id": instance_id,
                "config": config,
                "executor": executor,
                "ai_signal_generator": ai_signal_generator,
                "active": True,
                "created_at": datetime.now(),
                "check_count": 0,
                "last_check": None,
            }

            # Display configuration
            ai_status = "✅ Enabled" if config.use_ai_signals else "❌ Disabled"
            config_message = (
                f"✅ **Trading Instance Created**\n\n"
                f"**Instance ID:** `{instance_id}`\n"
                f"**Session ID:** `{session_id[:8]}`\n"
                f"**Active Instances in Session:** {len(self.trading_instances[session_id])}\n\n"
                f"**Configuration:**\n"
                f"- Trading Symbols: {', '.join(config.crypto_symbols)}\n"
                f"- Initial Capital: ${config.initial_capital:,.2f}\n"
                f"- Check Interval: {config.check_interval}s (1 minute)\n"
                f"- Risk Per Trade: {config.risk_per_trade * 100:.1f}%\n"
                f"- Max Positions: {config.max_positions}\n"
                f"- Analysis Model: {config.agent_model}\n"
                f"- AI Signals: {ai_status}\n\n"
                f"🚀 **Starting continuous trading...**\n"
                f"This instance will run continuously until stopped.\n\n"
            )

            yield streaming.message_chunk(config_message)

            # Get instance reference
            instance = self.trading_instances[session_id][instance_id]

            # Send initial portfolio snapshot
            portfolio_value = executor.get_portfolio_value()
            executor.snapshot_portfolio(datetime.now())

            initial_portfolio_msg = (
                f"💰 **Initial Portfolio**\n"
                f"Total Value: ${portfolio_value:,.2f}\n"
                f"Available Capital: ${executor.current_capital:,.2f}\n\n"
            )
            yield streaming.message_chunk(initial_portfolio_msg)

            # Set check interval
            check_interval = DEFAULT_CHECK_INTERVAL

            # Main trading loop
            yield streaming.message_chunk("📈 **Starting monitoring loop...**\n\n")

            while instance["active"]:
                try:
                    # Update check info
                    instance["check_count"] += 1
                    instance["last_check"] = datetime.now()
                    check_count = instance["check_count"]

                    logger.info(
                        f"Trading check #{check_count} for instance {instance_id}"
                    )

                    yield streaming.message_chunk(
                        f"\n{'=' * 50}\n"
                        f"🔄 **Check #{check_count}** - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                        f"Instance: `{instance_id}`\n"
                        f"{'=' * 50}\n\n"
                    )

                    # Analyze each symbol
                    for symbol in config.crypto_symbols:
                        # Calculate indicators
                        indicators = TechnicalAnalyzer.calculate_indicators(symbol)

                        if indicators is None:
                            logger.warning(f"Skipping {symbol} - insufficient data")
                            yield streaming.message_chunk(
                                f"⚠️ Skipping {symbol} - insufficient data\n\n"
                            )
                            continue

                        # Generate trading signal (AI-enhanced if enabled)
                        action, trade_type = None, None
                        ai_reasoning = None

                        if ai_signal_generator:
                            ai_signal = await ai_signal_generator.get_signal(indicators)
                            if ai_signal:
                                action, trade_type, ai_reasoning = ai_signal
                                logger.info(
                                    f"Using AI signal for {symbol}: {action.value} {trade_type.value}"
                                )

                        # Fall back to technical signal if no AI signal
                        if action is None:
                            action, trade_type = TechnicalAnalyzer.generate_signal(
                                indicators
                            )

                        # Send market analysis
                        analysis_message = (
                            MessageFormatter.format_market_analysis_notification(
                                symbol,
                                indicators,
                                action,
                                trade_type,
                                executor.positions,
                                ai_reasoning,
                            )
                        )
                        yield streaming.message_chunk(analysis_message + "\n\n")

                        # Execute trade if action is not HOLD
                        if action != TradeAction.HOLD:
                            trade_details = executor.execute_trade(
                                symbol, action, trade_type, indicators
                            )

                            if trade_details:
                                # Send trade notification
                                trade_message = (
                                    MessageFormatter.format_trade_notification(
                                        trade_details, config.agent_model
                                    )
                                )
                                yield streaming.message_chunk(
                                    f"💼 **Trade Executed**\n{trade_message}\n\n"
                                )

                    # Take snapshots
                    timestamp = datetime.now()
                    executor.snapshot_positions(timestamp)
                    executor.snapshot_portfolio(timestamp)

                    # Send portfolio update
                    portfolio_value = executor.get_portfolio_value()
                    total_pnl = portfolio_value - config.initial_capital

                    portfolio_msg = (
                        f"💰 **Portfolio Update**\n"
                        f"Time: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n"
                        f"Total Value: ${portfolio_value:,.2f}\n"
                        f"P&L: ${total_pnl:,.2f}\n"
                        f"Open Positions: {len(executor.positions)}\n"
                        f"Available Capital: ${executor.current_capital:,.2f}\n"
                    )

                    if executor.positions:
                        portfolio_msg += "\n**Open Positions:**\n"
                        for symbol, pos in executor.positions.items():
                            try:
                                import yfinance as yf

                                ticker = yf.Ticker(symbol)
                                current_price = ticker.history(
                                    period="1d", interval="1m"
                                )["Close"].iloc[-1]
                                if pos.trade_type.value == "long":
                                    current_pnl = (
                                        current_price - pos.entry_price
                                    ) * abs(pos.quantity)
                                else:
                                    current_pnl = (
                                        pos.entry_price - current_price
                                    ) * abs(pos.quantity)
                                pnl_emoji = "🟢" if current_pnl >= 0 else "🔴"
                                portfolio_msg += f"- {symbol}: {pos.trade_type.value.upper()} @ ${pos.entry_price:,.2f} {pnl_emoji} P&L: ${current_pnl:,.2f}\n"
                            except Exception as e:
                                logger.warning(
                                    f"Failed to calculate P&L for {symbol}: {e}"
                                )
                                portfolio_msg += f"- {symbol}: {pos.trade_type.value.upper()} @ ${pos.entry_price:,.2f}\n"

                    yield streaming.message_chunk(portfolio_msg + "\n")

                    # Send instance status component every 5 checks
                    if check_count % 5 == 0:
                        component_data = self._get_instance_status_component_data(
                            session_id, instance_id
                        )
                        if component_data:
                            yield streaming.component_generator(
                                component_data, TRADING_COMPONENT_TYPE
                            )

                    # Send session portfolio chart every 10 checks
                    if check_count % 10 == 0:
                        chart_data = self._get_session_portfolio_chart_data(session_id)
                        if chart_data:
                            yield streaming.component_generator(
                                chart_data, PORTFOLIO_COMPONENT_TYPE
                            )

                    # Wait for next check interval
                    logger.info(f"Waiting {check_interval}s until next check...")
                    yield streaming.message_chunk(
                        f"⏳ Waiting {check_interval} seconds until next check...\n\n"
                    )
                    await asyncio.sleep(check_interval)

                except Exception as e:
                    logger.error(f"Error during trading cycle: {e}")
                    yield streaming.message_chunk(
                        f"⚠️ **Error during trading cycle**: {str(e)}\n"
                        f"Continuing with next check...\n\n"
                    )
                    await asyncio.sleep(check_interval)

        except Exception as e:
            logger.error(f"Critical error in stream method: {e}")
            yield streaming.failed(f"Critical error: {str(e)}")
        finally:
            # Mark instance as inactive but keep data for history
            if session_id in self.trading_instances:
                if instance_id in self.trading_instances[session_id]:
                    self.trading_instances[session_id][instance_id]["active"] = False
                    logger.info(f"Stopped instance: {instance_id}")
