"""Trade recording and history management - from a trader's perspective"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List

from .models import TradeHistoryRecord

logger = logging.getLogger(__name__)


class TradeRecorder:
    """
    Records and analyzes all trading activity.

    A trader typically wants to know:
    1. "What have I traded?"
    2. "What's my win rate?"
    3. "What's my average win/loss?"
    4. "Which symbols are most profitable?"
    """

    def __init__(self):
        """Initialize trade recorder"""
        self._trades: List[TradeHistoryRecord] = []

    def record_trade(self, trade_record: TradeHistoryRecord):
        """
        Record a new trade.

        Args:
            trade_record: TradeHistoryRecord to record
        """
        self._trades.append(trade_record)
        logger.info(
            f"Recorded {trade_record.action} {trade_record.trade_type} on "
            f"{trade_record.symbol} at ${trade_record.price:.2f}"
        )

    def get_all_trades(self) -> List[TradeHistoryRecord]:
        """Get all recorded trades"""
        return self._trades.copy()

    def get_recent_trades(self, limit: int = 10) -> List[TradeHistoryRecord]:
        """Get most recent N trades"""
        return self._trades[-limit:] if self._trades else []

    def get_trades_by_symbol(self, symbol: str) -> List[TradeHistoryRecord]:
        """Get all trades for a specific symbol"""
        return [t for t in self._trades if t.symbol == symbol]

    def get_trades_by_action(self, action: str) -> List[TradeHistoryRecord]:
        """Get all trades of a specific action (opened/closed)"""
        return [t for t in self._trades if t.action == action]

    def get_trades_in_period(
        self, start_time: datetime, end_time: datetime
    ) -> List[TradeHistoryRecord]:
        """Get trades executed in a time period"""
        return [t for t in self._trades if start_time <= t.timestamp <= end_time]

    # ============ Trade Statistics Section ============

    def get_trade_statistics(self) -> Dict:
        """
        Get comprehensive trade statistics.

        Returns:
            Dictionary with various statistics
        """
        if not self._trades:
            return {
                "total_trades": 0,
                "win_trades": 0,
                "loss_trades": 0,
                "win_rate": 0,
                "total_pnl": 0,
                "average_win": 0,
                "average_loss": 0,
                "largest_win": 0,
                "largest_loss": 0,
                "profit_factor": 0,
            }

        # Calculate closed trades (those with P&L)
        closed_trades = [t for t in self._trades if t.pnl is not None]

        if not closed_trades:
            return {
                "total_trades": len(self._trades),
                "win_trades": 0,
                "loss_trades": 0,
                "win_rate": 0,
                "total_pnl": 0,
                "average_win": 0,
                "average_loss": 0,
                "largest_win": 0,
                "largest_loss": 0,
                "profit_factor": 0,
            }

        winning_trades = [t for t in closed_trades if t.pnl > 0]
        losing_trades = [t for t in closed_trades if t.pnl < 0]

        total_pnl = sum(t.pnl for t in closed_trades)
        total_wins = sum(t.pnl for t in winning_trades) if winning_trades else 0
        total_losses = sum(t.pnl for t in losing_trades) if losing_trades else 0

        return {
            "total_trades": len(closed_trades),
            "win_trades": len(winning_trades),
            "loss_trades": len(losing_trades),
            "win_rate": (len(winning_trades) / len(closed_trades) * 100)
            if closed_trades
            else 0,
            "total_pnl": total_pnl,
            "average_win": (total_wins / len(winning_trades)) if winning_trades else 0,
            "average_loss": (total_losses / len(losing_trades)) if losing_trades else 0,
            "largest_win": max(t.pnl for t in winning_trades) if winning_trades else 0,
            "largest_loss": min(t.pnl for t in losing_trades) if losing_trades else 0,
            "profit_factor": (total_wins / abs(total_losses))
            if total_losses != 0
            else (1.0 if total_wins > 0 else 0),
        }

    def get_symbol_statistics(self, symbol: str) -> Dict:
        """
        Get trading statistics for a specific symbol.

        Args:
            symbol: Trading symbol

        Returns:
            Statistics dictionary for that symbol
        """
        symbol_trades = self.get_trades_by_symbol(symbol)
        if not symbol_trades:
            return {"symbol": symbol, "trades": 0}

        closed_trades = [t for t in symbol_trades if t.pnl is not None]
        if not closed_trades:
            return {"symbol": symbol, "trades": len(symbol_trades), "closed": 0}

        winning_trades = [t for t in closed_trades if t.pnl > 0]
        losing_trades = [t for t in closed_trades if t.pnl < 0]

        total_pnl = sum(t.pnl for t in closed_trades)

        return {
            "symbol": symbol,
            "total_trades": len(closed_trades),
            "win_trades": len(winning_trades),
            "loss_trades": len(losing_trades),
            "win_rate": (len(winning_trades) / len(closed_trades) * 100),
            "total_pnl": total_pnl,
            "average_pnl_per_trade": total_pnl / len(closed_trades),
            "largest_win": max(t.pnl for t in winning_trades) if winning_trades else 0,
            "largest_loss": min(t.pnl for t in losing_trades) if losing_trades else 0,
        }

    def get_daily_statistics(self) -> Dict[str, Dict]:
        """
        Get daily P&L breakdown.

        Returns:
            Dictionary mapping dates to daily statistics
        """
        daily_stats = {}

        for trade in self._trades:
            date_key = trade.timestamp.strftime("%Y-%m-%d")
            if date_key not in daily_stats:
                daily_stats[date_key] = {
                    "trades": 0,
                    "pnl": 0,
                    "wins": 0,
                    "losses": 0,
                }

            daily_stats[date_key]["trades"] += 1
            if trade.pnl is not None:
                daily_stats[date_key]["pnl"] += trade.pnl
                if trade.pnl > 0:
                    daily_stats[date_key]["wins"] += 1
                else:
                    daily_stats[date_key]["losses"] += 1

        return daily_stats

    def get_holding_time_statistics(self) -> Dict:
        """
        Get statistics about holding times.

        Returns:
            Statistics about position holding duration
        """
        # Match opens and closes for each symbol
        holding_times = []

        for symbol in set(t.symbol for t in self._trades):
            symbol_trades = sorted(
                self.get_trades_by_symbol(symbol), key=lambda t: t.timestamp
            )

            for i in range(0, len(symbol_trades) - 1, 2):
                if (
                    i + 1 < len(symbol_trades)
                    and symbol_trades[i].action == "opened"
                    and symbol_trades[i + 1].action == "closed"
                ):
                    holding_time = (
                        symbol_trades[i + 1].timestamp - symbol_trades[i].timestamp
                    )
                    holding_times.append(holding_time)

        if not holding_times:
            return {
                "avg_holding_time": timedelta(0),
                "min_holding_time": timedelta(0),
                "max_holding_time": timedelta(0),
            }

        total_holding = sum(holding_times, timedelta())

        return {
            "total_positions": len(holding_times),
            "avg_holding_time": total_holding / len(holding_times),
            "min_holding_time": min(holding_times),
            "max_holding_time": max(holding_times),
        }

    # ============ Trade Analysis Section ============

    def get_best_trades(self, limit: int = 5) -> List[TradeHistoryRecord]:
        """Get the most profitable trades"""
        closed_trades = [t for t in self._trades if t.pnl is not None]
        closed_trades.sort(key=lambda t: t.pnl, reverse=True)
        return closed_trades[:limit]

    def get_worst_trades(self, limit: int = 5) -> List[TradeHistoryRecord]:
        """Get the least profitable trades"""
        closed_trades = [t for t in self._trades if t.pnl is not None]
        closed_trades.sort(key=lambda t: t.pnl)
        return closed_trades[:limit]

    def get_trade_breakdown_by_type(self) -> Dict[str, Dict]:
        """
        Get performance breakdown by trade type (LONG vs SHORT).

        Returns:
            Statistics for each trade type
        """
        closed_trades = [t for t in self._trades if t.pnl is not None]

        breakdown = {"LONG": {}, "SHORT": {}}

        for trade_type in ["LONG", "SHORT"]:
            type_trades = [
                t for t in closed_trades if t.trade_type.upper() == trade_type
            ]

            if not type_trades:
                breakdown[trade_type] = {
                    "trades": 0,
                    "wins": 0,
                    "losses": 0,
                    "total_pnl": 0,
                }
            else:
                winning = [t for t in type_trades if t.pnl > 0]
                losing = [t for t in type_trades if t.pnl < 0]

                breakdown[trade_type] = {
                    "trades": len(type_trades),
                    "wins": len(winning),
                    "losses": len(losing),
                    "win_rate": (len(winning) / len(type_trades) * 100),
                    "total_pnl": sum(t.pnl for t in type_trades),
                    "average_pnl": sum(t.pnl for t in type_trades) / len(type_trades),
                }

        return breakdown

    def reset(self):
        """Clear all trade history"""
        self._trades.clear()
