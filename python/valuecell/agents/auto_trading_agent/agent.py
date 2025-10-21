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
    ComponentType,
    FilteredCardPushNotificationComponentData,
    FilteredLineChartComponentData,
    StreamResponse,
)

from .constants import (
    DEFAULT_AGENT_MODEL,
    DEFAULT_CHECK_INTERVAL,
)
from .formatters import MessageFormatter
from .models import (
    AutoTradingConfig,
    TradingRequest,
)
from .portfolio_decision_manager import (
    AssetAnalysis,
    PortfolioDecisionManager,
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
        Generate portfolio status report in rich text format

        Returns:
            Formatted portfolio details as markdown string
        """
        if session_id not in self.trading_instances:
            return ""

        if instance_id not in self.trading_instances[session_id]:
            return ""

        instance = self.trading_instances[session_id][instance_id]
        executor: TradingExecutor = instance["executor"]
        config: AutoTradingConfig = instance["config"]

        # Get comprehensive portfolio summary
        portfolio_summary = executor.get_portfolio_summary()

        # Calculate overall statistics
        total_pnl = portfolio_summary["portfolio"]["total_pnl"]
        pnl_pct = portfolio_summary["portfolio"]["pnl_percentage"]
        portfolio_value = portfolio_summary["portfolio"]["total_value"]
        available_cash = portfolio_summary["cash"]["available"]

        # Build rich text output
        output = []

        # Header
        output.append(f"# 📊 Trading Portfolio Status - {instance_id}")
        output.append("\n**Instance Configuration**")
        output.append(f"- Model: `{config.agent_model}`")
        output.append(f"- Symbols: {', '.join(config.crypto_symbols)}")
        output.append(
            f"- Status: {'🟢 Active' if instance['active'] else '🔴 Stopped'}"
        )

        # Portfolio Summary Section
        output.append("\n## 💰 Portfolio Summary")
        output.append("\n**Overall Performance**")
        output.append(f"- Initial Capital: `${config.initial_capital:,.2f}`")
        output.append(f"- Current Value: `${portfolio_value:,.2f}`")

        pnl_emoji = "🟢" if total_pnl >= 0 else "🔴"
        pnl_sign = "+" if total_pnl >= 0 else ""
        output.append(
            f"- Total P&L: {pnl_emoji} **{pnl_sign}${total_pnl:,.2f}** ({pnl_sign}{pnl_pct:.2f}%)"
        )

        output.append("\n**Cash Position**")
        output.append(f"- Available Cash: `${available_cash:,.2f}`")

        # Current Positions Section
        output.append(f"\n## 📈 Current Positions ({len(executor.positions)})")

        if executor.positions:
            output.append(
                "\n| Symbol | Type | Quantity | Avg Price | Current Price | Position Value | Unrealized P&L |"
            )
            output.append(
                "|--------|------|----------|-----------|---------------|----------------|----------------|"
            )

            for symbol, pos in executor.positions.items():
                try:
                    import yfinance as yf

                    ticker = yf.Ticker(symbol)
                    current_price = ticker.history(period="1d", interval="1m")[
                        "Close"
                    ].iloc[-1]

                    # Calculate unrealized P&L
                    if pos.trade_type.value == "long":
                        unrealized_pnl = (current_price - pos.entry_price) * abs(
                            pos.quantity
                        )
                        position_value = abs(pos.quantity) * current_price
                    else:
                        unrealized_pnl = (pos.entry_price - current_price) * abs(
                            pos.quantity
                        )
                        position_value = pos.notional + unrealized_pnl

                    # Format row
                    pnl_emoji = "🟢" if unrealized_pnl >= 0 else "🔴"
                    pnl_sign = "+" if unrealized_pnl >= 0 else ""

                    output.append(
                        f"| **{symbol}** | {pos.trade_type.value.upper()} | "
                        f"{abs(pos.quantity):.4f} | ${pos.entry_price:,.2f} | "
                        f"${current_price:,.2f} | ${position_value:,.2f} | "
                        f"{pnl_emoji} {pnl_sign}${unrealized_pnl:,.2f} |"
                    )

                except Exception as e:
                    logger.warning(f"Failed to get price for {symbol}: {e}")
                    # Fallback display with entry price only
                    output.append(
                        f"| **{symbol}** | {pos.trade_type.value.upper()} | "
                        f"{abs(pos.quantity):.4f} | ${pos.entry_price:,.2f} | "
                        f"N/A | ${pos.notional:,.2f} | N/A |"
                    )
        else:
            output.append("\n*No open positions*")

        component_data = FilteredCardPushNotificationComponentData(
            title=f"{config.agent_model} Portfolio Status",
            data="\n".join(output),
            filters=[config.agent_model],
            table_title="Portfolio Detail",
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

            initial_portfolio_msg = FilteredCardPushNotificationComponentData(
                title=f"{config.agent_model} Portfolio",
                data=f"💰 **Initial Portfolio**\nTotal Value: ${portfolio_value:,.2f}\nAvailable Capital: ${executor.current_capital:,.2f}\n",
                filters=[config.agent_model],
                table_title="Portfolio Detail",
                create_time=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
            )
            yield streaming.component_generator(
                initial_portfolio_msg.model_dump_json(),
                ComponentType.FILTERED_CARD_PUSH_NOTIFICATION,
            )

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

                    # Phase 1: Collect analysis for all symbols
                    yield streaming.message_chunk(
                        "📊 **Phase 1: Analyzing all assets...**\n\n"
                    )

                    # Initialize portfolio manager with LLM client for AI-powered decisions
                    llm_client = None
                    if ai_signal_generator and ai_signal_generator.llm_client:
                        llm_client = ai_signal_generator.llm_client

                    portfolio_manager = PortfolioDecisionManager(config, llm_client)

                    for symbol in config.crypto_symbols:
                        # Calculate indicators
                        indicators = TechnicalAnalyzer.calculate_indicators(symbol)

                        if indicators is None:
                            logger.warning(f"Skipping {symbol} - insufficient data")
                            yield streaming.message_chunk(
                                f"⚠️ Skipping {symbol} - insufficient data\n\n"
                            )
                            continue

                        # Generate technical signal
                        technical_action, technical_trade_type = (
                            TechnicalAnalyzer.generate_signal(indicators)
                        )

                        # Generate AI signal if enabled
                        ai_action, ai_trade_type, ai_reasoning, ai_confidence = (
                            None,
                            None,
                            None,
                            None,
                        )

                        if ai_signal_generator:
                            ai_signal = await ai_signal_generator.get_signal(indicators)
                            if ai_signal:
                                (
                                    ai_action,
                                    ai_trade_type,
                                    ai_reasoning,
                                    ai_confidence,
                                ) = ai_signal
                                logger.info(
                                    f"AI signal for {symbol}: {ai_action.value} {ai_trade_type.value} "
                                    f"(confidence: {ai_confidence}%)"
                                )

                        # Create asset analysis
                        asset_analysis = AssetAnalysis(
                            symbol=symbol,
                            indicators=indicators,
                            technical_action=technical_action,
                            technical_trade_type=technical_trade_type,
                            ai_action=ai_action,
                            ai_trade_type=ai_trade_type,
                            ai_reasoning=ai_reasoning,
                            ai_confidence=ai_confidence,
                        )

                        # Add to portfolio manager
                        portfolio_manager.add_asset_analysis(asset_analysis)

                        # Display individual asset analysis
                        yield streaming.message_chunk(
                            MessageFormatter.format_market_analysis_notification(
                                symbol,
                                indicators,
                                asset_analysis.recommended_action,
                                asset_analysis.recommended_trade_type,
                                executor.positions,
                                ai_reasoning,
                            )
                        )

                    # Phase 2: Make portfolio-level decision
                    yield streaming.message_chunk(
                        "\n" + "=" * 50 + "\n"
                        "🎯 **Phase 2: Portfolio Decision Making...**\n"
                        + "=" * 50
                        + "\n\n"
                    )

                    # Get portfolio summary
                    portfolio_summary = portfolio_manager.get_portfolio_summary()
                    yield streaming.message_chunk(portfolio_summary + "\n")

                    # Make coordinated decision (async call for AI analysis)
                    portfolio_decision = (
                        await portfolio_manager.make_portfolio_decision(
                            current_positions=executor.positions,
                            available_cash=executor.get_current_capital(),
                            total_portfolio_value=executor.get_portfolio_value(),
                        )
                    )

                    # Display decision reasoning
                    portfolio_decision_msg = FilteredCardPushNotificationComponentData(
                        title=f"{config.agent_model} Analysis",
                        data=f"💰 **Portfolio Decision Reasoning**\n{portfolio_decision.reasoning}\n",
                        filters=[config.agent_model],
                        table_title="Market Analysis",
                        create_time=datetime.now(timezone.utc).strftime(
                            "%Y-%m-%d %H:%M:%S"
                        ),
                    )
                    yield streaming.component_generator(
                        portfolio_decision_msg.model_dump_json(),
                        ComponentType.FILTERED_CARD_PUSH_NOTIFICATION,
                    )

                    # Phase 3: Execute approved trades
                    if portfolio_decision.trades_to_execute:
                        yield streaming.message_chunk(
                            "\n" + "=" * 50 + "\n"
                            f"⚡ **Phase 3: Executing {len(portfolio_decision.trades_to_execute)} trade(s)...**\n"
                            + "=" * 50
                            + "\n\n"
                        )

                        for (
                            symbol,
                            action,
                            trade_type,
                        ) in portfolio_decision.trades_to_execute:
                            # Get indicators for this symbol
                            asset_analysis = portfolio_manager.asset_analyses.get(
                                symbol
                            )
                            if not asset_analysis:
                                continue

                            # Execute trade
                            trade_details = executor.execute_trade(
                                symbol, action, trade_type, asset_analysis.indicators
                            )

                            if trade_details:
                                # Send trade notification
                                trade_message_text = (
                                    MessageFormatter.format_trade_notification(
                                        trade_details, config.agent_model
                                    )
                                )
                                trade_message = FilteredCardPushNotificationComponentData(
                                    title=f"{config.agent_model} Trade",
                                    data=f"💰 **Trade Executed:**\n{trade_message_text}\n",
                                    filters=[config.agent_model],
                                    table_title="Trade Detail",
                                    create_time=datetime.now(timezone.utc).strftime(
                                        "%Y-%m-%d %H:%M:%S"
                                    ),
                                )
                                yield streaming.component_generator(
                                    trade_message.model_dump_json(),
                                    ComponentType.FILTERED_CARD_PUSH_NOTIFICATION,
                                )
                            else:
                                trade_message = FilteredCardPushNotificationComponentData(
                                    title=f"{config.agent_model} Trade",
                                    data=f"💰 **Trade Failed:** Could not execute {action.value} "
                                    f"{trade_type.value} on {symbol}\n",
                                    filters=[config.agent_model],
                                    table_title="Trade Detail",
                                    create_time=datetime.now(timezone.utc).strftime(
                                        "%Y-%m-%d %H:%M:%S"
                                    ),
                                )
                                yield streaming.component_generator(
                                    trade_message.model_dump_json(),
                                    ComponentType.FILTERED_CARD_PUSH_NOTIFICATION,
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

                    component_data = self._get_instance_status_component_data(
                        session_id, instance_id
                    )
                    if component_data:
                        yield streaming.component_generator(
                            component_data,
                            ComponentType.FILTERED_CARD_PUSH_NOTIFICATION,
                        )

                    chart_data = self._get_session_portfolio_chart_data(session_id)
                    if chart_data:
                        yield streaming.component_generator(
                            chart_data, ComponentType.FILTERED_LINE_CHART
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
