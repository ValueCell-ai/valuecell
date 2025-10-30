"""Formatting utilities for notifications and messages"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from ...utils.i18n_utils import convert_timezone, get_current_timezone
from .models import Position, TechnicalIndicators, TradeAction, TradeType

logger = logging.getLogger(__name__)


class MessageFormatter:
    """Formats various messages and notifications"""

    @staticmethod
    def _convert_and_format_timestamp(
        dt: datetime, format_str: str = "%m/%d, %I:%M %p", include_tz: bool = False
    ) -> str:
        """
        Convert timestamp to user's timezone and format it.

        Args:
            dt: DateTime to convert and format
            format_str: Format string for strftime
            include_tz: Whether to include timezone abbreviation

        Returns:
            Formatted timestamp string
        """
        try:
            # Get user's configured timezone
            user_tz = get_current_timezone()

            # Convert from UTC to user's timezone
            # Assume input is UTC if no timezone info
            if dt.tzinfo is None:
                dt = datetime(
                    dt.year,
                    dt.month,
                    dt.day,
                    dt.hour,
                    dt.minute,
                    dt.second,
                    tzinfo=timezone.utc,
                )

            converted_dt = convert_timezone(dt, "UTC", user_tz)

            # Format the datetime
            formatted = converted_dt.strftime(format_str)

            # Optionally append timezone info
            if include_tz:
                formatted += f" ({user_tz})"

            return formatted
        except Exception as e:
            logger.warning(f"Failed to convert timezone: {e}, using UTC")
            # Fallback to UTC format
            if dt.tzinfo is None:
                dt = datetime(
                    dt.year,
                    dt.month,
                    dt.day,
                    dt.hour,
                    dt.minute,
                    dt.second,
                    tzinfo=timezone.utc,
                )
            return dt.strftime(format_str)

    @staticmethod
    def format_trade_notification(
        trade_details: Dict[str, Any], agent_name: str = "AutoTrading"
    ) -> str:
        """
        Format trade details into a notification message

        Args:
            trade_details: Trade execution details
            agent_name: Name of the agent

        Returns:
            Formatted notification message
        """
        try:
            symbol = trade_details["symbol"]
            action = trade_details["action"]
            trade_type = trade_details["trade_type"]
            timestamp = trade_details["timestamp"]

            # Convert timestamp to user's timezone
            formatted_time = MessageFormatter._convert_and_format_timestamp(timestamp)

            if action == "opened":
                message = (
                    f"**{agent_name}** opened a **{trade_type}** position on **{symbol}**!\n\n"
                    f"📅 {formatted_time}\n\n"
                    f"**Price:** `${trade_details['entry_price']:,.2f}`\n\n"
                    f"**Quantity:** `{trade_details['quantity']:.4f}`\n\n"
                    f"**Notional:** `${trade_details['notional']:,.2f}`"
                )
            else:  # closed
                hours = int(trade_details["holding_time"].total_seconds() // 3600)
                minutes = int(
                    (trade_details["holding_time"].total_seconds() % 3600) // 60
                )
                pnl = trade_details["pnl"]
                pnl_sign = "+" if pnl >= 0 else ""
                pnl_emoji = "🟢" if pnl >= 0 else "🔴"

                message = (
                    f"**{agent_name}** completed a **{trade_type}** trade on **{symbol}**!\n\n"
                    f"📅 {formatted_time}\n\n"
                    f"**Price:** `${trade_details['entry_price']:,.2f}` → `${trade_details['exit_price']:,.2f}`\n\n"
                    f"**Quantity:** `{trade_details['quantity']:.4f}`\n\n"
                    f"**Notional:** `${trade_details['entry_notional']:,.2f}` → `${trade_details['exit_notional']:,.2f}`\n\n"
                    f"**Holding time:** `{hours}H {minutes}M`\n\n"
                    f"**Net P&L:** {pnl_emoji} **{pnl_sign}${pnl:,.2f}**"
                )

            return message

        except Exception as e:
            logger.error(f"Failed to format trade notification: {e}")
            return "Trade executed"

    @staticmethod
    def format_portfolio_notification(
        portfolio_value: float,
        positions_count: int,
        current_capital: float,
        agent_model: str,
        session_id: str,
        portfolio_history: list,
    ) -> tuple[str, Optional[str]]:
        """
        Format portfolio value notification for chart rendering

        Args:
            portfolio_value: Current portfolio value
            positions_count: Number of open positions
            current_capital: Available capital
            agent_model: Agent model name
            session_id: Current session ID
            portfolio_history: Historical portfolio data

        Returns:
            Tuple of (display message, chart data JSON)
        """
        try:
            timestamp = datetime.now(timezone.utc)

            # Append to history
            portfolio_history.append(
                {"timestamp": timestamp.isoformat(), "value": portfolio_value}
            )

            # Create chart data payload
            chart_data = {
                "id": f"AutoTradingAgent-{agent_model}",
                "filters": [
                    {"dimension": "Time", "gte": timestamp.isoformat()},
                    {"dimension": "Model", "=": agent_model},
                ],
                "data": {"Portfolio": portfolio_value},
            }

            # Convert timestamp to user's timezone for display
            formatted_time = MessageFormatter._convert_and_format_timestamp(
                timestamp, format_str="%m/%d, %I:%M %p", include_tz=True
            )

            display_message = (
                f"💰 Portfolio Update\n"
                f"Time: {formatted_time}\n"
                f"Total Value: ${portfolio_value:,.2f}\n"
                f"Open Positions: {positions_count}\n"
                f"Available Capital: ${current_capital:,.2f}"
            )

            return display_message, json.dumps(chart_data)

        except Exception as e:
            logger.error(f"Failed to format portfolio notification: {e}")
            return "Portfolio update failed", None

    @staticmethod
    def format_market_analysis_notification(
        symbol: str,
        indicators: TechnicalIndicators,
        action: TradeAction,
        trade_type: TradeType,
        positions: Dict[str, Position],
        ai_reasoning: Optional[str] = None,
    ) -> str:
        """
        Format market analysis notification including HOLD decisions

        Args:
            symbol: Trading symbol
            indicators: Technical indicators
            action: Recommended action
            trade_type: Trade type
            positions: Current positions dictionary
            ai_reasoning: AI reasoning if available

        Returns:
            Formatted analysis message
        """
        try:
            timestamp = datetime.now(timezone.utc)

            # Convert timestamp to user's timezone for display
            formatted_time = MessageFormatter._convert_and_format_timestamp(
                timestamp, format_str="%m/%d, %I:%M %p", include_tz=True
            )

            # Format action with emoji
            action_emoji = {
                TradeAction.BUY: "🟢",
                TradeAction.SELL: "🔴",
                TradeAction.HOLD: "⏸️",
            }

            message = (
                f"📊 **Market Analysis - {symbol}**\n"
                f"Time: {formatted_time}\n\n"
                f"**Current Price:** ${indicators.close_price:,.2f}\n"
                f"**Decision:** {action_emoji.get(action, '')} {action.value.upper()}"
            )

            if action != TradeAction.HOLD:
                message += f" ({trade_type.value.upper()})"

            message += "\n\n**Technical Indicators:**\n"

            # Add MACD
            if indicators.macd is not None and indicators.macd_signal is not None:
                macd_signal = (
                    "🟢 Bullish"
                    if indicators.macd > indicators.macd_signal
                    else "🔴 Bearish"
                )
                message += f"- MACD: {indicators.macd:.4f} / Signal: {indicators.macd_signal:.4f} ({macd_signal})\n"

            # Add RSI
            if indicators.rsi is not None:
                rsi_signal = (
                    "🟢 Oversold"
                    if indicators.rsi < 30
                    else ("🔴 Overbought" if indicators.rsi > 70 else "⚪ Neutral")
                )
                message += f"- RSI: {indicators.rsi:.2f} ({rsi_signal})\n"

            # Add EMAs
            if indicators.ema_12 is not None and indicators.ema_26 is not None:
                ema_signal = (
                    "🟢 Bullish"
                    if indicators.ema_12 > indicators.ema_26
                    else "🔴 Bearish"
                )
                message += f"- EMA 12/26: ${indicators.ema_12:,.2f} / ${indicators.ema_26:,.2f} ({ema_signal})\n"

            # Add Bollinger Bands
            if indicators.bb_upper is not None and indicators.bb_lower is not None:
                if indicators.close_price > indicators.bb_upper:
                    bb_signal = "🔴 Above Upper Band"
                elif indicators.close_price < indicators.bb_lower:
                    bb_signal = "🟢 Below Lower Band"
                else:
                    bb_signal = "⚪ Within Bands"
                message += f"- Bollinger Bands: ${indicators.bb_lower:,.2f} - ${indicators.bb_upper:,.2f} ({bb_signal})\n"

            # Add AI reasoning if available
            if ai_reasoning:
                message += f"\n**AI Analysis:**\n{ai_reasoning}\n"

            # Add current position info if exists
            if symbol in positions:
                pos = positions[symbol]
                current_pnl = 0
                if pos.trade_type == TradeType.LONG:
                    current_pnl = (indicators.close_price - pos.entry_price) * abs(
                        pos.quantity
                    )
                else:
                    current_pnl = (pos.entry_price - indicators.close_price) * abs(
                        pos.quantity
                    )

                pnl_emoji = "🟢" if current_pnl >= 0 else "🔴"
                message += (
                    f"\n**Current Position:**\n"
                    f"- Type: {pos.trade_type.value.upper()}\n"
                    f"- Entry: ${pos.entry_price:,.2f}\n"
                    f"- Quantity: {abs(pos.quantity):.4f}\n"
                    f"- Unrealized P&L: {pnl_emoji} ${current_pnl:,.2f}\n"
                )
            else:
                message += f"\n**Current Position:** No open position for {symbol}\n\n"

            return message

        except Exception as e:
            logger.error(f"Failed to format market analysis notification: {e}")
            return f"Market analysis for {symbol}"
