"""Technical analysis and signal generation"""

import json
import logging
from datetime import datetime, timezone
from typing import Optional

import pandas as pd
import yfinance as yf
from agno.agent import Agent

from .models import TechnicalIndicators, TradeAction, TradeType

logger = logging.getLogger(__name__)


class TechnicalAnalyzer:
    """Technical analysis and indicator calculation"""

    @staticmethod
    def calculate_indicators(
        symbol: str, period: str = "5d", interval: str = "1m"
    ) -> Optional[TechnicalIndicators]:
        """
        Calculate technical indicators using yfinance data

        Args:
            symbol: Trading symbol (e.g., BTC-USD)
            period: Data period
            interval: Data interval

        Returns:
            TechnicalIndicators object or None if calculation fails
        """
        try:
            # Fetch data from yfinance
            ticker = yf.Ticker(symbol)
            df = ticker.history(period=period, interval=interval)

            if df.empty or len(df) < 50:
                logger.warning(f"Insufficient data for {symbol}")
                return None

            # Calculate EMAs
            df["ema_12"] = df["Close"].ewm(span=12, adjust=False).mean()
            df["ema_26"] = df["Close"].ewm(span=26, adjust=False).mean()
            df["ema_50"] = df["Close"].ewm(span=50, adjust=False).mean()

            # Calculate MACD
            df["macd"] = df["ema_12"] - df["ema_26"]
            df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()
            df["macd_histogram"] = df["macd"] - df["macd_signal"]

            # Calculate RSI
            delta = df["Close"].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            df["rsi"] = 100 - (100 / (1 + rs))

            # Calculate Bollinger Bands
            df["bb_middle"] = df["Close"].rolling(window=20).mean()
            bb_std = df["Close"].rolling(window=20).std()
            df["bb_upper"] = df["bb_middle"] + (bb_std * 2)
            df["bb_lower"] = df["bb_middle"] - (bb_std * 2)

            # Get the latest values
            latest = df.iloc[-1]

            return TechnicalIndicators(
                symbol=symbol,
                timestamp=datetime.now(timezone.utc),
                close_price=float(latest["Close"]),
                volume=float(latest["Volume"]),
                macd=float(latest["macd"]) if not pd.isna(latest["macd"]) else None,
                macd_signal=float(latest["macd_signal"])
                if not pd.isna(latest["macd_signal"])
                else None,
                macd_histogram=float(latest["macd_histogram"])
                if not pd.isna(latest["macd_histogram"])
                else None,
                rsi=float(latest["rsi"]) if not pd.isna(latest["rsi"]) else None,
                ema_12=float(latest["ema_12"])
                if not pd.isna(latest["ema_12"])
                else None,
                ema_26=float(latest["ema_26"])
                if not pd.isna(latest["ema_26"])
                else None,
                ema_50=float(latest["ema_50"])
                if not pd.isna(latest["ema_50"])
                else None,
                bb_upper=float(latest["bb_upper"])
                if not pd.isna(latest["bb_upper"])
                else None,
                bb_middle=float(latest["bb_middle"])
                if not pd.isna(latest["bb_middle"])
                else None,
                bb_lower=float(latest["bb_lower"])
                if not pd.isna(latest["bb_lower"])
                else None,
            )

        except Exception as e:
            logger.error(f"Failed to calculate indicators for {symbol}: {e}")
            return None

    @staticmethod
    def generate_signal(
        indicators: TechnicalIndicators,
    ) -> tuple[TradeAction, TradeType]:
        """
        Generate trading signal based on technical indicators

        Args:
            indicators: Technical indicators for analysis

        Returns:
            Tuple of (TradeAction, TradeType)
        """
        try:
            # Check if we have all required indicators
            if (
                indicators.macd is None
                or indicators.macd_signal is None
                or indicators.rsi is None
            ):
                return (TradeAction.HOLD, TradeType.LONG)

            # MACD Strategy
            macd_bullish = indicators.macd > indicators.macd_signal
            macd_bearish = indicators.macd < indicators.macd_signal

            # RSI Strategy
            rsi_oversold = indicators.rsi < 30
            rsi_overbought = indicators.rsi > 70

            # Bollinger Bands Strategy
            bb_lower_breach = (
                indicators.bb_lower is not None
                and indicators.close_price < indicators.bb_lower
            )
            bb_upper_breach = (
                indicators.bb_upper is not None
                and indicators.close_price > indicators.bb_upper
            )

            # Combined Signal Logic
            # Long signal: MACD bullish + RSI oversold or price below lower BB
            if macd_bullish and (rsi_oversold or bb_lower_breach):
                return (TradeAction.BUY, TradeType.LONG)

            # Short signal: MACD bearish + RSI overbought or price above upper BB
            if macd_bearish and (rsi_overbought or bb_upper_breach):
                return (TradeAction.BUY, TradeType.SHORT)

            # Exit long position: MACD turns bearish or RSI overbought
            if macd_bearish or rsi_overbought:
                return (TradeAction.SELL, TradeType.LONG)

            # Exit short position: MACD turns bullish or RSI oversold
            if macd_bullish or rsi_oversold:
                return (TradeAction.SELL, TradeType.SHORT)

            return (TradeAction.HOLD, TradeType.LONG)

        except Exception as e:
            logger.error(f"Failed to generate signal: {e}")
            return (TradeAction.HOLD, TradeType.LONG)


class AISignalGenerator:
    """AI-enhanced signal generation using LLM"""

    def __init__(self, llm_client):
        """
        Initialize AI signal generator

        Args:
            llm_client: OpenRouter client instance
        """
        self.llm_client = llm_client

    async def get_signal(
        self, indicators: TechnicalIndicators
    ) -> Optional[tuple[TradeAction, TradeType, str]]:
        """
        Get AI-enhanced trading signal using OpenRouter model

        Args:
            indicators: Technical indicators for analysis

        Returns:
            Tuple of (TradeAction, TradeType, reasoning) or None if AI not available
        """
        if not self.llm_client:
            return None

        try:
            # Create analysis prompt with proper formatting
            macd_str = (
                f"{indicators.macd:.4f}" if indicators.macd is not None else "N/A"
            )
            macd_signal_str = (
                f"{indicators.macd_signal:.4f}"
                if indicators.macd_signal is not None
                else "N/A"
            )
            macd_histogram_str = (
                f"{indicators.macd_histogram:.4f}"
                if indicators.macd_histogram is not None
                else "N/A"
            )
            rsi_str = f"{indicators.rsi:.2f}" if indicators.rsi is not None else "N/A"
            ema_12_str = (
                f"${indicators.ema_12:,.2f}" if indicators.ema_12 is not None else "N/A"
            )
            ema_26_str = (
                f"${indicators.ema_26:,.2f}" if indicators.ema_26 is not None else "N/A"
            )
            ema_50_str = (
                f"${indicators.ema_50:,.2f}" if indicators.ema_50 is not None else "N/A"
            )
            bb_upper_str = (
                f"${indicators.bb_upper:,.2f}"
                if indicators.bb_upper is not None
                else "N/A"
            )
            bb_middle_str = (
                f"${indicators.bb_middle:,.2f}"
                if indicators.bb_middle is not None
                else "N/A"
            )
            bb_lower_str = (
                f"${indicators.bb_lower:,.2f}"
                if indicators.bb_lower is not None
                else "N/A"
            )

            prompt = f"""You are an expert crypto trading analyst. Analyze the following technical indicators for {indicators.symbol} and provide a trading recommendation.

Current Market Data:
- Symbol: {indicators.symbol}
- Price: ${indicators.close_price:,.2f}
- Volume: {indicators.volume:,.0f}

Technical Indicators:
- MACD: {macd_str}
- MACD Signal: {macd_signal_str}
- MACD Histogram: {macd_histogram_str}
- RSI: {rsi_str}
- EMA 12: {ema_12_str}
- EMA 26: {ema_26_str}
- EMA 50: {ema_50_str}
- BB Upper: {bb_upper_str}
- BB Middle: {bb_middle_str}
- BB Lower: {bb_lower_str}

Based on these indicators, provide:
1. Action: BUY, SELL, or HOLD
2. Type: LONG or SHORT (if BUY)
3. Confidence: 0-100%
4. Reasoning: Brief explanation (1-2 sentences)

Format your response as JSON:
{{"action": "BUY|SELL|HOLD", "type": "LONG|SHORT", "confidence": 0-100, "reasoning": "explanation"}}"""

            agent = Agent(model=self.llm_client, markdown=False)
            response = await agent.arun(prompt)

            # Parse response
            content = response.content.strip()
            # Extract JSON from markdown code blocks if present
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            result = json.loads(content)

            action = TradeAction(result["action"].lower())
            trade_type = (
                TradeType(result["type"].lower()) if result["type"] else TradeType.LONG
            )
            reasoning = result["reasoning"]

            logger.info(
                f"AI Signal for {indicators.symbol}: {action.value} {trade_type.value} - {reasoning}"
            )

            return (action, trade_type, reasoning)

        except Exception as e:
            logger.error(f"Failed to get AI trading signal: {e}")
            return None
