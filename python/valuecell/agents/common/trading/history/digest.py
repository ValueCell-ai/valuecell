from datetime import datetime, timezone
from typing import Dict, List

import numpy as np

from valuecell.agents.common.trading.models import (
    HistoryRecord,
    InstrumentRef,
    TradeDigest,
    TradeDigestEntry,
)

from .interfaces import BaseDigestBuilder

# Risk-free rate for Sharpe Ratio calculation (annualized, 3% for this example)
RISK_FREE_RATE = 0.03

# Number of seconds per year (365 days * 24 hours * 3600 seconds/hour)
SECONDS_PER_YEAR = 365 * 24 * 3600


class RollingDigestBuilder(BaseDigestBuilder):
    """Builds a lightweight digest from recent execution records."""

    def __init__(self, window: int = 50) -> None:
        self._window = max(window, 1)

    def build(self, records: List[HistoryRecord]) -> TradeDigest:
        recent = records[-self._window :]
        by_instrument: Dict[str, TradeDigestEntry] = {}
        stats: Dict[str, Dict[str, float | int]] = {}

        for record in recent:
            if record.kind != "execution":
                continue
            trades = record.payload.get("trades", [])
            for trade_dict in trades:
                instrument_dict = trade_dict.get("instrument") or {}
                symbol = instrument_dict.get("symbol")
                if not symbol:
                    continue
                entry = by_instrument.get(symbol)
                if entry is None:
                    entry = TradeDigestEntry(
                        instrument=InstrumentRef(**instrument_dict),
                        trade_count=0,
                        realized_pnl=0.0,
                    )
                    by_instrument[symbol] = entry
                    stats[symbol] = {
                        "wins": 0,
                        "losses": 0,
                        "holding_ms_sum": 0,
                        "holding_ms_count": 0,
                    }
                entry.trade_count += 1
                realized = float(trade_dict.get("realized_pnl") or 0.0)
                entry.realized_pnl += realized
                entry.last_trade_ts = trade_dict.get("trade_ts") or entry.last_trade_ts

                # Win/loss counting: prefer closed trades (with exit fields). Fallback to realized only if it's a close.
                try:
                    outcome_pnl = None
                    has_exit = (
                        trade_dict.get("exit_ts") is not None
                        or trade_dict.get("exit_price") is not None
                        or trade_dict.get("notional_exit") is not None
                    )
                    if has_exit:
                        # Try compute PnL sign from entry/exit where possible (more robust for partial closes)
                        etype = (trade_dict.get("type") or "").upper()
                        entry_px = trade_dict.get("entry_price")
                        exit_px = trade_dict.get("exit_price")
                        notional_exit = trade_dict.get("notional_exit")
                        close_qty = None
                        if exit_px and notional_exit:
                            try:
                                if float(exit_px) > 0:
                                    close_qty = float(notional_exit) / float(exit_px)
                            except Exception:
                                close_qty = None
                        if close_qty is None:
                            # Fallback to recorded quantity
                            q = trade_dict.get("quantity")
                            close_qty = float(q) if q is not None else None
                        if entry_px and exit_px and close_qty and close_qty > 0:
                            if etype == "LONG":
                                outcome_pnl = (
                                    float(exit_px) - float(entry_px)
                                ) * float(close_qty)
                            elif etype == "SHORT":
                                outcome_pnl = (
                                    float(entry_px) - float(exit_px)
                                ) * float(close_qty)
                        if outcome_pnl is None:
                            # Fallback to realized if available
                            outcome_pnl = (
                                realized
                                if trade_dict.get("realized_pnl") is not None
                                else None
                            )
                    else:
                        # No exit fields: avoid counting pure opens (which may carry fee-only negative realized)
                        outcome_pnl = None

                    if outcome_pnl is not None:
                        if outcome_pnl > 0:
                            stats[symbol]["wins"] = int(stats[symbol]["wins"]) + 1
                        elif outcome_pnl < 0:
                            stats[symbol]["losses"] = int(stats[symbol]["losses"]) + 1
                except Exception:
                    pass

                # Holding time aggregation when present
                try:
                    hms = trade_dict.get("holding_ms")
                    if hms is not None:
                        stats[symbol]["holding_ms_sum"] = int(
                            stats[symbol]["holding_ms_sum"]
                        ) + int(hms)
                        stats[symbol]["holding_ms_count"] = (
                            int(stats[symbol]["holding_ms_count"]) + 1
                        )
                except Exception:
                    pass

        timestamp = (
            recent[-1].ts
            if recent
            else int(datetime.now(timezone.utc).timestamp() * 1000)
        )

        # Finalize derived stats (win_rate, avg_holding_ms)
        for symbol, entry in by_instrument.items():
            st = stats.get(symbol) or {}
            wins = int(st.get("wins", 0) or 0)
            losses = int(st.get("losses", 0) or 0)
            denom = wins + losses
            if denom > 0:
                try:
                    entry.win_rate = float(wins) / float(denom)
                except Exception:
                    entry.win_rate = None
            hsum = int(st.get("holding_ms_sum", 0) or 0)
            hcnt = int(st.get("holding_ms_count", 0) or 0)
            if hcnt > 0:
                try:
                    entry.avg_holding_ms = int(hsum / hcnt)
                except Exception:
                    entry.avg_holding_ms = None

        # Calculate Sharpe Ratio from equity curve
        sharpe_ratio = self._calculate_sharpe_ratio(recent)

        return TradeDigest(
            ts=timestamp, by_instrument=by_instrument, sharpe_ratio=sharpe_ratio
        )

    def _calculate_sharpe_ratio(self, records: List[HistoryRecord]) -> float | None:
        """Calculate Sharpe Ratio from equity curve in history records.

        Extracts portfolio equity from compose records and computes risk-adjusted
        return as: (mean_return - risk_free_rate) / std_dev_returns.

        Args:
            records: Recent history records (should include compose records)

        Returns:
            Sharpe Ratio (float) or None if insufficient data
        """
        if len(records) < 2:
            return None

        # Extract equity values and timestamps from compose records
        equities: List[float] = []
        timestamps: List[int] = []
        for record in records:
            if record.kind == "compose":
                payload = record.payload or {}
                summary = payload.get("summary") or {}
                # StrategySummary may have total_value in different representations
                # Try to extract equity (total portfolio value)
                equity = None
                # Attempt 1: summary is already a dict with total_value
                if isinstance(summary, dict):
                    equity = summary.get("total_value")
                # Attempt 2: summary might be serialized; check for equity-like fields
                if equity is None and isinstance(summary, dict):
                    # Fallback: try to compute from realized + unrealized + initial
                    # For now, we'll rely on total_value being present
                    pass
                if equity is not None:
                    try:
                        eq_val = float(equity)
                        if eq_val > 0:
                            equities.append(eq_val)
                            timestamps.append(record.ts)
                    except (ValueError, TypeError):
                        pass

        if len(equities) < 2 or len(timestamps) < 2:
            return None

        # Calculate average period in seconds
        intervals = []
        for i in range(1, len(timestamps)):
            interval = (
                timestamps[i] - timestamps[i - 1]
            ) / 1000.0  # Convert ms to seconds
            if interval > 0:
                intervals.append(interval)
        if not intervals:
            return None
        avg_period_seconds = sum(intervals) / len(intervals)

        # Calculate periods per year
        periods_per_year = SECONDS_PER_YEAR / avg_period_seconds

        # Calculate period returns
        returns: List[float] = []
        for i in range(1, len(equities)):
            if equities[i - 1] > 0:
                period_return = (equities[i] - equities[i - 1]) / equities[i - 1]
                returns.append(period_return)

        if len(returns) < 2:
            return None

        # Compute mean and standard deviation
        returns_arr = np.array(returns)
        mean_return = float(np.mean(returns_arr))
        std_return = float(np.std(returns_arr, ddof=1))  # Sample std deviation

        # Sharpe Ratio
        if std_return > 0:
            # Adjust risk-free rate per period based on actual check interval
            period_rf = RISK_FREE_RATE / periods_per_year
            sharpe_ratio = (mean_return - period_rf) / std_return
            return float(sharpe_ratio)

        # If std is zero, no volatility -> undefined Sharpe
        return None
