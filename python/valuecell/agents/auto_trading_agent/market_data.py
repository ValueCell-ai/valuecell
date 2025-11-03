"""Market data and technical indicator retrieval - from a trader's perspective"""

import logging
import os
from datetime import datetime, timezone
from typing import Dict, Optional

import pandas as pd
import yfinance as yf

from .exchanges.okx_exchange import OKXExchange
from .models import TechnicalIndicators

logger = logging.getLogger(__name__)


class MarketDataProvider:
    """
    Fetches and caches market data.

    A trader typically thinks about:
    1. "What's the current price?"
    2. "What are the technical indicators telling me?"
    3. "Is there enough volume for good execution?"
    """

    def __init__(self, cache_ttl_seconds: int = 60):
        """
        Initialize market data provider with optional caching.

        Args:
            cache_ttl_seconds: Time to live for cached data
        """
        self.cache_ttl_seconds = cache_ttl_seconds
        self._cache: Dict[str, tuple] = {}  # {symbol: (data, timestamp)}

    def get_current_price(self, symbol: str) -> Optional[float]:
        """
        Get current market price for a symbol.

        Args:
            symbol: Trading symbol (e.g., BTC-USD)

        Returns:
            Current price or None if fetch fails
        """
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(period="1d", interval="1m")
            if data.empty:
                logger.warning(f"No data available for {symbol}")
                return None
            return float(data["Close"].iloc[-1])
        except Exception as e:
            logger.error(f"Failed to get current price for {symbol}: {e}")
            return None

    def calculate_indicators(
        self, symbol: str, period: str = "5d", interval: str = "1m"
    ) -> Optional[TechnicalIndicators]:
        """
        Calculate all technical indicators for a symbol.

        Args:
            symbol: Trading symbol
            period: Data period (default: 5 days for intraday trading)
            interval: Data interval (default: 1 minute)

        Returns:
            TechnicalIndicators object or None if calculation fails
        """
        try:
            # Fetch data from yfinance
            ticker = yf.Ticker(symbol)
            df = ticker.history(period=period, interval=interval)

            if df.empty or len(df) < 50:
                logger.warning(f"Insufficient data for {symbol}: {len(df)} bars")
                return None

            # Calculate all indicators
            self._calculate_moving_averages(df)
            self._calculate_macd(df)
            self._calculate_rsi(df)
            self._calculate_bollinger_bands(df)

            # Get latest values
            return self._extract_latest_indicators(df, symbol)

        except Exception as e:
            logger.error(f"Failed to calculate indicators for {symbol}: {e}")
            return None

    @staticmethod
    def _calculate_moving_averages(df: pd.DataFrame):
        """Calculate exponential moving averages"""
        df["ema_12"] = df["Close"].ewm(span=12, adjust=False).mean()
        df["ema_26"] = df["Close"].ewm(span=26, adjust=False).mean()
        df["ema_50"] = df["Close"].ewm(span=50, adjust=False).mean()

    @staticmethod
    def _calculate_macd(df: pd.DataFrame):
        """Calculate MACD and signal line"""
        df["ema_12"] = df["Close"].ewm(span=12, adjust=False).mean()
        df["ema_26"] = df["Close"].ewm(span=26, adjust=False).mean()
        df["macd"] = df["ema_12"] - df["ema_26"]
        df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()
        df["macd_histogram"] = df["macd"] - df["macd_signal"]

    @staticmethod
    def _calculate_rsi(df: pd.DataFrame, period: int = 14):
        """Calculate Relative Strength Index"""
        delta = df["Close"].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        # Avoid division by zero: if loss is 0, RSI = 100 (maximum strength)
        rs = gain / loss.replace(0, float("inf"))
        df["rsi"] = 100 - (100 / (1 + rs))

    @staticmethod
    def _calculate_bollinger_bands(
        df: pd.DataFrame, period: int = 20, std_dev: float = 2
    ):
        """Calculate Bollinger Bands"""
        df["bb_middle"] = df["Close"].rolling(window=period).mean()
        bb_std = df["Close"].rolling(window=period).std()
        df["bb_upper"] = df["bb_middle"] + (bb_std * std_dev)
        df["bb_lower"] = df["bb_middle"] - (bb_std * std_dev)

    @staticmethod
    def _extract_latest_indicators(
        df: pd.DataFrame, symbol: str
    ) -> TechnicalIndicators:
        """Extract latest indicator values from dataframe"""
        latest = df.iloc[-1]

        def safe_float(value):
            """Safely convert to float, handling NaN"""
            return float(value) if pd.notna(value) else None

        return TechnicalIndicators(
            symbol=symbol,
            timestamp=datetime.now(timezone.utc),
            close_price=float(latest["Close"]),
            volume=float(latest["Volume"]),
            macd=safe_float(latest.get("macd")),
            macd_signal=safe_float(latest.get("macd_signal")),
            macd_histogram=safe_float(latest.get("macd_histogram")),
            rsi=safe_float(latest.get("rsi")),
            ema_12=safe_float(latest.get("ema_12")),
            ema_26=safe_float(latest.get("ema_26")),
            ema_50=safe_float(latest.get("ema_50")),
            bb_upper=safe_float(latest.get("bb_upper")),
            bb_middle=safe_float(latest.get("bb_middle")),
            bb_lower=safe_float(latest.get("bb_lower")),
        )


class OkxMarketDataProvider(MarketDataProvider):
    """Market data provider that uses OKX APIs for spot/contract prices.

    Falls back to parent implementation for indicators (yfinance) to keep
    indicator availability without extra OKX Kline wiring for now.
    """

    def __init__(self, cache_ttl_seconds: int = 60):
        super().__init__(cache_ttl_seconds=cache_ttl_seconds)
        self._okx = None

    def _ensure_okx(self) -> OKXExchange:
        if self._okx is None:
            api_key = os.getenv("OKX_API_KEY", "")
            api_secret = os.getenv("OKX_API_SECRET", "")
            passphrase = os.getenv("OKX_API_PASSPHRASE", "")
            network = os.getenv("OKX_NETWORK", "paper")
            self._okx = OKXExchange(
                api_key=api_key,
                api_secret=api_secret,
                passphrase=passphrase,
                network=network,
            )
        return self._okx

    def get_current_price(self, symbol: str) -> Optional[float]:
        try:
            okx = self._ensure_okx()
            # Connect lazily on first price call
            if not getattr(okx, "is_connected", False):
                import asyncio

                try:
                    asyncio.get_running_loop()
                    # we're in an async context; run sync via to_thread later
                    # Fallback to parent if connection cannot be ensured here
                except RuntimeError:
                    # No running loop; safe to run connect synchronously
                    asyncio.run(okx.connect())

            # Get price from OKX adapter
            price = None
            try:
                # Try synchronous bridge via asyncio for adapter's async method
                import asyncio

                async def _get():
                    if not okx.is_connected:
                        await okx.connect()
                    return await okx.get_current_price(symbol)

                try:
                    loop = asyncio.get_running_loop()
                    # If running loop exists, schedule and block until done
                    price = loop.run_until_complete(_get())  # type: ignore
                except RuntimeError:
                    # No running loop; we can create one
                    price = asyncio.run(_get())
            except Exception:
                # As a fallback, use parent (yfinance)
                return super().get_current_price(symbol)

            return float(price) if price is not None else None
        except Exception as e:
            logger.error(f"Failed to get OKX price for {symbol}: {e}")
            return super().get_current_price(symbol)


class SignalGenerator:
    """
    Generates trading signals from technical indicators.

    A trader's signal logic:
    1. When to buy? (Entry signals)
    2. When to sell? (Exit signals)
    3. How confident am I?
    """

    from .models import TradeAction, TradeType

    @staticmethod
    def generate_signal(
        indicators: TechnicalIndicators,
    ) -> tuple["SignalGenerator.TradeAction", "SignalGenerator.TradeType"]:
        """
        Generate trading signal based on technical indicators.

        Uses a combination of:
        - MACD for trend direction
        - RSI for momentum/exhaustion
        - Bollinger Bands for volatility and support/resistance

        Args:
            indicators: Technical indicators for analysis

        Returns:
            Tuple of (TradeAction, TradeType)
        """
        from .models import TradeAction, TradeType

        try:
            # Check if we have all required indicators
            if (
                indicators.macd is None
                or indicators.macd_signal is None
                or indicators.rsi is None
            ):
                return (TradeAction.HOLD, TradeType.LONG)

            # Analyze trend direction
            macd_bullish = indicators.macd > indicators.macd_signal
            macd_bearish = indicators.macd < indicators.macd_signal

            # Analyze momentum
            rsi_oversold = indicators.rsi < 30
            rsi_overbought = indicators.rsi > 70

            # Entry signals: Look for mean-reversion opportunities with trend confirmation
            # Long signal: MACD bullish + RSI showing oversold
            if macd_bullish and rsi_oversold:
                return (TradeAction.BUY, TradeType.LONG)

            # Short signal: MACD bearish + RSI showing overbought
            if macd_bearish and rsi_overbought:
                return (TradeAction.BUY, TradeType.SHORT)

            # Exit signals: Close positions when momentum reverses
            # Exit long: MACD turns bearish or RSI gets overbought
            if macd_bearish or rsi_overbought:
                return (TradeAction.SELL, TradeType.LONG)

            # Exit short: MACD turns bullish or RSI gets oversold
            if macd_bullish or rsi_oversold:
                return (TradeAction.SELL, TradeType.SHORT)

            return (TradeAction.HOLD, TradeType.LONG)

        except Exception as e:
            logger.error(f"Failed to generate signal: {e}")
            return (TradeAction.HOLD, TradeType.LONG)

    @staticmethod
    def get_signal_strength(indicators: TechnicalIndicators) -> Dict[str, float]:
        """
        Get quantitative strength of signals.

        Returns:
            Dictionary with various signal strength indicators (0-100)
        """
        strength = {}

        # MACD strength (0-100)
        if indicators.macd is not None and indicators.macd_signal is not None:
            macd_diff = indicators.macd - indicators.macd_signal
            # Normalize to 0-100 scale (assuming typical range)
            strength["macd"] = min(100, max(0, 50 + (macd_diff * 100)))
        else:
            strength["macd"] = 50  # Neutral

        # RSI strength (already 0-100)
        if indicators.rsi is not None:
            strength["rsi"] = indicators.rsi
        else:
            strength["rsi"] = 50  # Neutral

        # Distance from Bollinger Bands (0-100)
        if (
            indicators.bb_lower is not None
            and indicators.bb_upper is not None
            and indicators.bb_middle is not None
        ):
            band_range = indicators.bb_upper - indicators.bb_lower
            if band_range > 0:
                # Distance from middle: 0 = at lower band, 100 = at upper band
                distance = (indicators.close_price - indicators.bb_lower) / band_range
                strength["bollinger"] = min(100, max(0, distance * 100))
            else:
                strength["bollinger"] = 50
        else:
            strength["bollinger"] = 50  # Neutral

        return strength
