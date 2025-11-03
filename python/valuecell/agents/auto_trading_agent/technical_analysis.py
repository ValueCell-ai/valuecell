"""Technical analysis and signal generation (refactored)"""

import json
import logging
from typing import Optional

from agno.agent import Agent

from .market_data import MarketDataProvider, SignalGenerator
from .models import TechnicalIndicators, TradeAction, TradeType

logger = logging.getLogger(__name__)


class TechnicalAnalyzer:
    """
    Static interface for technical analysis (backward compatible).

    Now delegates to MarketDataProvider internally.
    """

    _market_data_provider = MarketDataProvider()

    @staticmethod
    def set_provider(provider: MarketDataProvider) -> None:
        """Override the default market data provider."""
        TechnicalAnalyzer._market_data_provider = provider

    @staticmethod
    def calculate_indicators(
        symbol: str, period: str = "5d", interval: str = "1m"
    ) -> Optional[TechnicalIndicators]:
        """
        Calculate technical indicators using yfinance data.

        Args:
            symbol: Trading symbol (e.g., BTC-USD)
            period: Data period
            interval: Data interval

        Returns:
            TechnicalIndicators object or None if calculation fails
        """
        return TechnicalAnalyzer._market_data_provider.calculate_indicators(
            symbol, period, interval
        )

    @staticmethod
    def generate_signal(
        indicators: TechnicalIndicators,
    ) -> tuple[TradeAction, TradeType]:
        """
        Generate trading signal based on technical indicators.

        Args:
            indicators: Technical indicators for analysis

        Returns:
            Tuple of (TradeAction, TradeType)
        """
        return SignalGenerator.generate_signal(indicators)


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
    ) -> Optional[tuple[TradeAction, TradeType, str, float]]:
        """
        Get AI-enhanced trading signal using OpenRouter model

        Args:
            indicators: Technical indicators for analysis

        Returns:
            Tuple of (TradeAction, TradeType, reasoning, confidence) or None if AI not available
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
            confidence = float(result.get("confidence", 75.0))

            logger.info(
                f"AI Signal for {indicators.symbol}: {action.value} {trade_type.value} "
                f"(confidence: {confidence}%) - {reasoning}"
            )

            return (action, trade_type, reasoning, confidence)

        except Exception as e:
            logger.error(f"Failed to get AI trading signal: {e}")
            return None
