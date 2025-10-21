"""Trading execution and position management"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import yfinance as yf

from .models import (
    AutoTradingConfig,
    PortfolioValueSnapshot,
    Position,
    PositionHistorySnapshot,
    TechnicalIndicators,
    TradeAction,
    TradeHistoryRecord,
    TradeType,
)

logger = logging.getLogger(__name__)


class TradingExecutor:
    """Handles trade execution and position management"""

    def __init__(self, config: AutoTradingConfig):
        """
        Initialize trading executor

        Args:
            config: Auto trading configuration
        """
        self.config = config
        self.current_capital = config.initial_capital
        self.initial_capital = config.initial_capital
        self.positions: Dict[str, Position] = {}

        # Historical tracking
        self.trade_history: List[TradeHistoryRecord] = []
        self.position_history: List[PositionHistorySnapshot] = []
        self.portfolio_history: List[PortfolioValueSnapshot] = []

    def execute_trade(
        self,
        symbol: str,
        action: TradeAction,
        trade_type: TradeType,
        indicators: TechnicalIndicators,
    ) -> Optional[Dict[str, Any]]:
        """
        Execute a trade and update positions

        Args:
            symbol: Trading symbol
            action: Trade action (buy/sell)
            trade_type: Trade type (long/short)
            indicators: Current technical indicators

        Returns:
            Trade execution details or None
        """
        try:
            current_price = indicators.close_price
            timestamp = datetime.now(timezone.utc)

            if action == TradeAction.BUY:
                return self._open_position(symbol, trade_type, current_price, timestamp)

            elif action == TradeAction.SELL:
                return self._close_position(
                    symbol, trade_type, current_price, timestamp
                )

            return None

        except Exception as e:
            logger.error(f"Failed to execute trade for {symbol}: {e}")
            return None

    def _open_position(
        self,
        symbol: str,
        trade_type: TradeType,
        current_price: float,
        timestamp: datetime,
    ) -> Optional[Dict[str, Any]]:
        """Open a new position"""
        # Check if we can open a new position
        if len(self.positions) >= self.config.max_positions:
            logger.info(f"Max positions reached, cannot buy {symbol}")
            return None

        # Calculate position size based on risk management
        risk_amount = self.current_capital * self.config.risk_per_trade
        quantity = risk_amount / current_price
        notional = quantity * current_price

        # Check if we have enough capital
        if notional > self.current_capital:
            logger.warning(f"Insufficient capital for {symbol} trade")
            return None

        # Create position
        position = Position(
            symbol=symbol,
            entry_price=current_price,
            quantity=quantity if trade_type == TradeType.LONG else -quantity,
            entry_time=timestamp,
            trade_type=trade_type,
            notional=notional,
        )

        self.positions[symbol] = position
        self.current_capital -= notional

        # Record trade history
        portfolio_value = self.get_portfolio_value()
        trade_record = TradeHistoryRecord(
            timestamp=timestamp,
            symbol=symbol,
            action="opened",
            trade_type=trade_type.value,
            price=current_price,
            quantity=abs(position.quantity),
            notional=notional,
            pnl=None,
            portfolio_value_after=portfolio_value,
        )
        self.trade_history.append(trade_record)

        return {
            "action": "opened",
            "trade_type": trade_type.value,
            "symbol": symbol,
            "entry_price": current_price,
            "quantity": position.quantity,
            "notional": notional,
            "timestamp": timestamp,
        }

    def _close_position(
        self,
        symbol: str,
        trade_type: TradeType,
        current_price: float,
        timestamp: datetime,
    ) -> Optional[Dict[str, Any]]:
        """Close an existing position"""
        # Check if we have a position to close
        if symbol not in self.positions:
            return None

        position = self.positions[symbol]

        # Check if trade type matches
        if position.trade_type != trade_type:
            return None

        # Calculate P&L
        exit_price = current_price
        exit_notional = abs(position.quantity) * exit_price
        holding_time = timestamp - position.entry_time

        if trade_type == TradeType.LONG:
            pnl = exit_notional - position.notional
        else:  # SHORT
            pnl = position.notional - exit_notional

        # Update capital
        self.current_capital += position.notional + pnl

        # Remove position
        del self.positions[symbol]

        # Record trade history
        portfolio_value = self.get_portfolio_value()
        trade_record = TradeHistoryRecord(
            timestamp=timestamp,
            symbol=symbol,
            action="closed",
            trade_type=trade_type.value,
            price=exit_price,
            quantity=abs(position.quantity),
            notional=exit_notional,
            pnl=pnl,
            portfolio_value_after=portfolio_value,
        )
        self.trade_history.append(trade_record)

        return {
            "action": "closed",
            "trade_type": trade_type.value,
            "symbol": symbol,
            "entry_price": position.entry_price,
            "exit_price": exit_price,
            "quantity": position.quantity,
            "entry_notional": position.notional,
            "exit_notional": exit_notional,
            "pnl": pnl,
            "holding_time": holding_time,
            "timestamp": timestamp,
        }

    def get_portfolio_value(self) -> float:
        """
        Calculate current portfolio value (cash + open positions)

        Returns:
            Total portfolio value
        """
        try:
            total_value = self.current_capital

            # Add value of open positions
            for symbol, position in self.positions.items():
                try:
                    ticker = yf.Ticker(symbol)
                    current_price = ticker.history(period="1d", interval="1m")[
                        "Close"
                    ].iloc[-1]

                    if position.trade_type == TradeType.LONG:
                        position_value = abs(position.quantity) * current_price
                    else:  # SHORT
                        # For short: initial_notional + (entry_price - current_price) * quantity
                        position_value = position.notional + (
                            position.entry_price - current_price
                        ) * abs(position.quantity)

                    total_value += position_value

                except Exception as e:
                    logger.warning(f"Failed to get price for {symbol}: {e}")
                    # Use entry notional as fallback
                    total_value += position.notional

            return total_value

        except Exception as e:
            logger.error(f"Failed to calculate portfolio value: {e}")
            return self.current_capital

    def get_portfolio_summary(self) -> Dict[str, Any]:
        """Get portfolio summary"""
        return {
            "capital": self.current_capital,
            "portfolio_value": self.get_portfolio_value(),
            "positions": len(self.positions),
            "position_details": [
                {
                    "symbol": pos.symbol,
                    "quantity": pos.quantity,
                    "entry_price": pos.entry_price,
                    "trade_type": pos.trade_type.value,
                }
                for pos in self.positions.values()
            ],
        }

    def reset(self, initial_capital: float):
        """Reset executor state"""
        self.current_capital = initial_capital
        self.initial_capital = initial_capital
        self.positions = {}
        self.trade_history = []
        self.position_history = []
        self.portfolio_history = []

    def snapshot_positions(self, timestamp: datetime):
        """
        Take a snapshot of all current positions

        Args:
            timestamp: Snapshot timestamp
        """
        for symbol, position in self.positions.items():
            try:
                # Get current price
                ticker = yf.Ticker(symbol)
                current_price = ticker.history(period="1d", interval="1m")[
                    "Close"
                ].iloc[-1]

                # Calculate unrealized P&L
                if position.trade_type == TradeType.LONG:
                    unrealized_pnl = (current_price - position.entry_price) * abs(
                        position.quantity
                    )
                else:
                    unrealized_pnl = (position.entry_price - current_price) * abs(
                        position.quantity
                    )

                # Create snapshot
                snapshot = PositionHistorySnapshot(
                    timestamp=timestamp,
                    symbol=symbol,
                    quantity=position.quantity,
                    entry_price=position.entry_price,
                    current_price=current_price,
                    trade_type=position.trade_type.value,
                    unrealized_pnl=unrealized_pnl,
                    notional=position.notional,
                )
                self.position_history.append(snapshot)

            except Exception as e:
                logger.warning(f"Failed to snapshot position for {symbol}: {e}")

    def snapshot_portfolio(self, timestamp: datetime):
        """
        Take a snapshot of the entire portfolio

        Args:
            timestamp: Snapshot timestamp
        """
        portfolio_value = self.get_portfolio_value()
        positions_value = portfolio_value - self.current_capital

        # Calculate total unrealized P&L
        total_pnl = 0.0
        for symbol, position in self.positions.items():
            try:
                ticker = yf.Ticker(symbol)
                current_price = ticker.history(period="1d", interval="1m")[
                    "Close"
                ].iloc[-1]

                if position.trade_type == TradeType.LONG:
                    total_pnl += (current_price - position.entry_price) * abs(
                        position.quantity
                    )
                else:
                    total_pnl += (position.entry_price - current_price) * abs(
                        position.quantity
                    )
            except Exception as e:
                logger.warning(f"Failed to calculate P&L for {symbol}: {e}")

        snapshot = PortfolioValueSnapshot(
            timestamp=timestamp,
            total_value=portfolio_value,
            cash=self.current_capital,
            positions_value=positions_value,
            positions_count=len(self.positions),
            total_pnl=total_pnl,
        )
        self.portfolio_history.append(snapshot)

    def get_trade_history(self) -> List[TradeHistoryRecord]:
        """Get all trade history"""
        return self.trade_history

    def get_position_history(self) -> List[PositionHistorySnapshot]:
        """Get all position snapshots"""
        return self.position_history

    def get_portfolio_history(self) -> List[PortfolioValueSnapshot]:
        """Get all portfolio snapshots"""
        return self.portfolio_history
