"""Position and cash management module - from a trader's perspective"""

import logging
from datetime import datetime
from typing import Dict, Optional, Tuple

import yfinance as yf

from .models import (
    CashManagement,
    PortfolioValueSnapshot,
    Position,
    PositionHistorySnapshot,
    TradeType,
)

logger = logging.getLogger(__name__)


class PositionManager:
    """
    Manages all trading positions and cash from a trader's perspective.

    A trader typically thinks about:
    1. "How much cash do I have available?"
    2. "What positions am I currently holding?"
    3. "What's my P&L on each position?"
    4. "How much total capital is deployed?"
    """

    def __init__(self, initial_capital: float):
        """
        Initialize position manager with initial capital.

        Args:
            initial_capital: Total capital available for trading
        """
        self.initial_capital = initial_capital

        # Current state
        self._positions: Dict[str, Position] = {}  # symbol -> Position
        self._cash_management = CashManagement(
            total_cash=initial_capital,
            initial_cash=initial_capital,
            available_cash=initial_capital,
            cash_in_trades=0.0,
        )

        # Historical snapshots for analysis
        self._position_history: list[PositionHistorySnapshot] = []
        self._portfolio_history: list[PortfolioValueSnapshot] = []

    # ============ Cash Management Section ============

    def get_cash_status(self) -> CashManagement:
        """Get current cash management status"""
        return self._cash_management.model_copy()

    def get_available_cash(self) -> float:
        """Get available cash for new trades"""
        return self._cash_management.available_cash

    def get_total_cash_deployed(self) -> float:
        """Get total cash currently deployed in positions"""
        return self._cash_management.cash_in_trades

    def allocate_cash(self, amount: float) -> bool:
        """
        Allocate cash for a new position.

        Args:
            amount: Amount to allocate

        Returns:
            True if allocation successful, False if insufficient cash
        """
        if amount > self._cash_management.available_cash:
            logger.warning(
                f"Insufficient cash: requested {amount}, "
                f"available {self._cash_management.available_cash}"
            )
            return False

        self._cash_management.available_cash -= amount
        self._cash_management.cash_in_trades += amount
        return True

    def release_cash(self, amount: float, pnl: float = 0.0):
        """
        Release cash from a closed position (including P&L).

        Args:
            amount: Initial position notional
            pnl: Profit/loss from the position
        """
        self._cash_management.cash_in_trades -= amount
        self._cash_management.total_cash += pnl
        self._cash_management.available_cash = (
            self._cash_management.total_cash - self._cash_management.cash_in_trades
        )

    # ============ Position Management Section ============

    def open_position(self, symbol: str, position: Position) -> bool:
        """
        Open a new position.

        Args:
            symbol: Trading symbol
            position: Position object

        Returns:
            True if position opened successfully
        """
        if symbol in self._positions:
            logger.warning(f"Position already exists for {symbol}")
            return False

        # Allocate cash for this position
        if not self.allocate_cash(position.notional):
            return False

        self._positions[symbol] = position
        logger.info(f"Opened {position.trade_type.value} position on {symbol}")
        return True

    def close_position(self, symbol: str) -> Optional[Position]:
        """
        Close an existing position.

        Args:
            symbol: Trading symbol

        Returns:
            Closed position or None if not found
        """
        if symbol not in self._positions:
            logger.warning(f"No position found for {symbol}")
            return None

        position = self._positions.pop(symbol)
        logger.info(f"Closed {position.trade_type.value} position on {symbol}")
        return position

    def get_position(self, symbol: str) -> Optional[Position]:
        """Get position for a specific symbol"""
        return self._positions.get(symbol)

    def get_all_positions(self) -> Dict[str, Position]:
        """Get all current positions"""
        return self._positions.copy()

    def get_positions_count(self) -> int:
        """Get number of current open positions"""
        return len(self._positions)

    # ============ Portfolio Valuation Section ============

    def calculate_position_pnl(self, position: Position, current_price: float) -> float:
        """
        Calculate unrealized P&L for a position.

        Args:
            position: Position object
            current_price: Current market price

        Returns:
            Unrealized P&L amount
        """
        if position.trade_type == TradeType.LONG:
            # Long: profit when price goes up
            return (current_price - position.entry_price) * abs(position.quantity)
        else:
            # Short: profit when price goes down
            return (position.entry_price - current_price) * abs(position.quantity)

    def calculate_portfolio_value(self) -> Tuple[float, float, float]:
        """
        Calculate total portfolio value with breakdown.

        Returns:
            Tuple of (total_value, positions_value, total_pnl)
        """
        total_value = self._cash_management.total_cash
        positions_value = 0.0
        total_pnl = 0.0

        for symbol, position in self._positions.items():
            try:
                ticker = yf.Ticker(symbol)
                current_price = ticker.history(period="1d", interval="1m")[
                    "Close"
                ].iloc[-1]

                # Calculate unrealized P&L
                pnl = self.calculate_position_pnl(position, current_price)
                total_pnl += pnl

                # Calculate position value
                if position.trade_type == TradeType.LONG:
                    pos_value = abs(position.quantity) * current_price
                else:
                    pos_value = position.notional + pnl

                positions_value += pos_value
                total_value += pnl

            except Exception as e:
                logger.warning(f"Failed to get price for {symbol}: {e}")
                # Fallback to notional
                positions_value += position.notional

        return total_value, positions_value, total_pnl

    def get_portfolio_summary(self) -> Dict:
        """
        Get complete portfolio summary from trader's perspective.

        Returns:
            Dictionary with all portfolio information
        """
        total_value, positions_value, total_pnl = self.calculate_portfolio_value()

        return {
            "cash": {
                "available": self._cash_management.available_cash,
                "deployed": self._cash_management.cash_in_trades,
                "total": self._cash_management.total_cash,
            },
            "positions": {
                "count": self.get_positions_count(),
                "total_value": positions_value,
            },
            "portfolio": {
                "total_value": total_value,
                "total_pnl": total_pnl,
                "pnl_percentage": (total_pnl / self.initial_capital * 100)
                if self.initial_capital > 0
                else 0,
            },
        }

    # ============ History Tracking Section ============

    def snapshot_positions(self, timestamp: datetime):
        """
        Take a snapshot of all positions at a point in time.

        Args:
            timestamp: Snapshot timestamp
        """
        for symbol, position in self._positions.items():
            try:
                ticker = yf.Ticker(symbol)
                current_price = ticker.history(period="1d", interval="1m")[
                    "Close"
                ].iloc[-1]

                unrealized_pnl = self.calculate_position_pnl(position, current_price)

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
                self._position_history.append(snapshot)

            except Exception as e:
                logger.warning(f"Failed to snapshot position for {symbol}: {e}")

    def snapshot_portfolio(self, timestamp: datetime):
        """
        Take a snapshot of the entire portfolio.

        Args:
            timestamp: Snapshot timestamp
        """
        total_value, positions_value, total_pnl = self.calculate_portfolio_value()

        snapshot = PortfolioValueSnapshot(
            timestamp=timestamp,
            total_value=total_value,
            cash=self._cash_management.available_cash,
            cash_in_trades=self._cash_management.cash_in_trades,
            positions_value=positions_value,
            positions_count=self.get_positions_count(),
            total_pnl=total_pnl,
        )
        self._portfolio_history.append(snapshot)

    def get_position_history(self) -> list[PositionHistorySnapshot]:
        """Get all position history snapshots"""
        return self._position_history.copy()

    def get_portfolio_history(self) -> list[PortfolioValueSnapshot]:
        """Get all portfolio history snapshots"""
        return self._portfolio_history.copy()

    def reset(self, initial_capital: float):
        """Reset to initial state"""
        self.initial_capital = initial_capital
        self._positions.clear()
        self._cash_management = CashManagement(
            total_cash=initial_capital,
            initial_cash=initial_capital,
            available_cash=initial_capital,
            cash_in_trades=0.0,
        )
        self._position_history.clear()
        self._portfolio_history.clear()
