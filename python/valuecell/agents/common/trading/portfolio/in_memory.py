from datetime import datetime, timezone
from typing import List, Optional

from valuecell.agents.common.trading.models import (
    Constraints,
    FeatureVector,
    MarketType,
    PortfolioView,
    PositionSnapshot,
    TradeHistoryEntry,
    TradeSide,
    TradeType,
    TradingMode,
)
from valuecell.agents.common.trading.utils import extract_price_map

from .interfaces import BasePortfolioService


class InMemoryPortfolioService(BasePortfolioService):
    """Tracks cash and positions in memory and computes derived metrics.

    Notes:
    - cash reflects running cash balance from trade settlements
    - gross_exposure = sum(abs(qty) * mark_price)
    - net_exposure   = sum(qty * mark_price)
    - equity (total_value) = cash + net_exposure  [correct for both long and short]
    - total_unrealized_pnl = sum((mark_price - avg_price) * qty)
    - total_realized_pnl accumulates realized gains/losses as positions close
    - buying_power: max(0, equity * max_leverage - gross_exposure)
      where max_leverage comes from portfolio.constraints (default 1.0)
    - free_cash: per-position effective margin approximation without explicit margin_used
        free_cash = max(0, equity - sum_i(notional_i / L_i)),
        where L_i is position.leverage if present else constraints.max_leverage (>=1)
    """

    def __init__(
        self,
        initial_capital: float,
        trading_mode: TradingMode,
        market_type: MarketType,
        constraints: Optional[Constraints] = None,
        strategy_id: Optional[str] = None,
    ) -> None:
        # Store owning strategy id on the view so downstream components
        # always see which strategy this portfolio belongs to.
        self._strategy_id = strategy_id
        self._view = PortfolioView(
            strategy_id=strategy_id,
            ts=int(datetime.now(timezone.utc).timestamp() * 1000),
            account_balance=initial_capital,
            positions={},
            gross_exposure=0.0,
            net_exposure=0.0,
            constraints=constraints or None,
            total_value=initial_capital,
            total_unrealized_pnl=0.0,
            total_realized_pnl=0.0,
            buying_power=initial_capital,
            free_cash=initial_capital,
        )
        self._trading_mode = trading_mode
        self._market_type = market_type

    def get_view(self) -> PortfolioView:
        self._view.ts = int(datetime.now(timezone.utc).timestamp() * 1000)
        # Ensure strategy_id is present on each view retrieval
        if self._strategy_id is not None:
            try:
                self._view.strategy_id = self._strategy_id
            except Exception:
                pass
        return self._view

    def apply_trades(
        self, trades: List[TradeHistoryEntry], market_features: List[FeatureVector]
    ) -> None:
        """Apply trades and update portfolio positions and aggregates.

        This method updates:
        - cash (subtract on BUY, add on SELL at trade price)
        - positions with weighted avg price, entry_ts on (re)open, and mark_price
        - per-position notional, unrealized_pnl, unrealized_pnl_pct (and keeps pnl_pct for
          backward compatibility)
        - portfolio aggregates: gross_exposure, net_exposure, total_value (equity), total_unrealized_pnl, buying_power
        """
        # Extract price map from market feature bundle
        price_map = extract_price_map(market_features)
        total_realized = float(self._view.total_realized_pnl or 0.0)

        for trade in trades:
            symbol = trade.instrument.symbol
            # Use execution price for settlement and marking. Fallback sensibly.
            exec_price = None
            try:
                if trade.avg_exec_price is not None:
                    exec_price = float(trade.avg_exec_price)
                elif trade.exit_price is not None:
                    exec_price = float(trade.exit_price)
                elif trade.entry_price is not None:
                    exec_price = float(trade.entry_price)
            except Exception:
                exec_price = None
            price = float(exec_price or price_map.get(symbol, 0.0) or 0.0)
            delta = float(trade.quantity or 0.0)
            quantity_delta = delta if trade.side == TradeSide.BUY else -delta

            position = self._view.positions.get(symbol)
            if position is None:
                position = PositionSnapshot(
                    instrument=trade.instrument,
                    quantity=0.0,
                    avg_price=None,
                    mark_price=price,
                    unrealized_pnl=0.0,
                )
                self._view.positions[symbol] = position

            current_qty = float(position.quantity)
            avg_price = float(position.avg_price or 0.0)
            realized_delta = self._compute_realized_delta(
                trade=trade,
                current_qty=current_qty,
                quantity_delta=quantity_delta,
                avg_price=avg_price,
                fill_price=price,
            )
            new_qty = current_qty + quantity_delta

            # Update mark price to execution reference
            position.mark_price = price

            # Handle position quantity transitions and avg price
            if new_qty == 0.0:
                # Fully closed — do NOT remove the position immediately.
                # Keep a tombstone snapshot so downstream callers (UI / API)
                # that poll holdings immediately after execution can still see
                # the just-closed position. Mark it closed with a timestamp.
                position.quantity = 0.0
                position.mark_price = price
                # preserve avg_price and entry_ts for auditing; record closed_ts
                position.closed_ts = int(datetime.now(timezone.utc).timestamp() * 1000)
                position.unrealized_pnl = 0.0
                position.unrealized_pnl_pct = None
            elif current_qty == 0.0:
                # Opening new position
                position.quantity = new_qty
                position.avg_price = price
                position.entry_ts = (
                    trade.entry_ts
                    or trade.trade_ts
                    or int(datetime.now(timezone.utc).timestamp() * 1000)
                )
                position.closed_ts = None
                position.trade_type = TradeType.LONG if new_qty > 0 else TradeType.SHORT
                # Initialize leverage from trade if provided
                if trade.leverage is not None:
                    position.leverage = float(trade.leverage)
            elif (current_qty > 0 and new_qty > 0) or (current_qty < 0 and new_qty < 0):
                # Same direction
                if abs(new_qty) > abs(current_qty):
                    # Increasing position: weighted average price
                    position.avg_price = (
                        abs(current_qty) * avg_price + abs(quantity_delta) * price
                    ) / abs(new_qty)
                    position.quantity = new_qty
                    # Update leverage as size-weighted average if provided
                    if trade.leverage is not None:
                        prev_lev = float(position.leverage or trade.leverage)
                        position.leverage = (
                            abs(current_qty) * prev_lev
                            + abs(quantity_delta) * float(trade.leverage)
                        ) / abs(new_qty)
                else:
                    # Reducing position: keep avg price, update quantity
                    position.quantity = new_qty
                # entry_ts remains from original opening
            else:
                # Crossing through zero to opposite direction: reset avg price and entry_ts
                position.quantity = new_qty
                position.avg_price = price
                position.entry_ts = (
                    trade.entry_ts
                    or trade.trade_ts
                    or int(datetime.now(timezone.utc).timestamp() * 1000)
                )
                position.trade_type = TradeType.LONG if new_qty > 0 else TradeType.SHORT
                # Reset leverage when flipping direction
                if trade.leverage is not None:
                    position.leverage = float(trade.leverage)

            # Update cash by trade notional at execution price
            notional = price * delta
            # Deduct fees from cash as well. Trade may include fee_cost (in quote ccy).
            fee = trade.fee_cost or 0.0

            if self._market_type == MarketType.SPOT:
                if trade.side == TradeSide.BUY:
                    # buying reduces cash by notional plus fees
                    self._view.account_balance -= notional
                    self._view.account_balance -= fee
                else:
                    # selling increases cash by notional minus fees
                    self._view.account_balance += notional
                    self._view.account_balance -= fee
            else:
                # Derivatives: Cash (Wallet Balance) only changes by Realized PnL and Fees
                # Notional is not deducted from cash.
                # self._view.account_balance -= fee
                self._view.account_balance += realized_delta

            total_realized += realized_delta

            # Recompute per-position derived fields (if position still exists)
            pos = self._view.positions.get(symbol)
            if pos is not None:
                qty = float(pos.quantity)
                mpx = float(pos.mark_price or 0.0)
                apx = float(pos.avg_price or 0.0)
                pos.notional = abs(qty) * mpx if mpx else None
                if apx and mpx:
                    pos.unrealized_pnl = (mpx - apx) * qty
                    denom = abs(qty) * apx
                    pct = (pos.unrealized_pnl / denom) * 100.0 if denom else None
                    # populate both the newer field and keep the legacy alias
                    pos.unrealized_pnl_pct = pct
                    pos.pnl_pct = pct
                else:
                    pos.unrealized_pnl = None
                    pos.unrealized_pnl_pct = None
                    pos.pnl_pct = None

        # Recompute portfolio aggregates
        gross = 0.0
        net = 0.0
        unreal = 0.0
        for pos in self._view.positions.values():
            # Refresh mark price from snapshot if available
            try:
                sym = pos.instrument.symbol
            except Exception:
                sym = None
            if sym and sym in price_map:
                snap_px = float(price_map.get(sym) or 0.0)
                if snap_px > 0:
                    pos.mark_price = snap_px

            mpx = float(pos.mark_price or 0.0)
            qty = float(pos.quantity)
            apx = float(pos.avg_price or 0.0)
            # Recompute unrealized PnL and percent (populate both new and legacy fields)
            if apx and mpx:
                pos.unrealized_pnl = (mpx - apx) * qty
                denom = abs(qty) * apx
                pct = (pos.unrealized_pnl / denom) * 100.0 if denom else None
                pos.unrealized_pnl_pct = pct
                pos.pnl_pct = pct
            else:
                pos.unrealized_pnl = None
                pos.unrealized_pnl_pct = None
                pos.pnl_pct = None
            gross += abs(qty) * mpx
            net += qty * mpx
            if pos.unrealized_pnl is not None:
                unreal += float(pos.unrealized_pnl)

        self._view.gross_exposure = gross
        self._view.net_exposure = net
        self._view.total_unrealized_pnl = unreal
        self._view.total_realized_pnl = total_realized

        if self._market_type == MarketType.SPOT:
            # Equity is cash plus net exposure (market value of assets)
            equity = self._view.account_balance + net
        else:
            # Derivatives: Equity is Wallet Balance + Unrealized PnL
            equity = self._view.account_balance + unreal

        self._view.total_value = equity

        # Approximate buying power using market type policy
        if self._market_type == MarketType.SPOT:
            # Spot: cash-only buying power
            self._view.buying_power = max(0.0, float(self._view.account_balance))
        else:
            # Derivatives: margin-based buying power
            max_lev = (
                float(self._view.constraints.max_leverage)
                if (self._view.constraints and self._view.constraints.max_leverage)
                else 1.0
            )
            buying_power = max(0.0, equity * max_lev - gross)
            self._view.buying_power = buying_power

        # Compute free_cash using per-position effective leverage
        # Equity fallback: already computed as cash + net
        if self._market_type == MarketType.SPOT:
            # No leverage: free cash equals available cash
            self._view.free_cash = max(0.0, float(self._view.account_balance))
        else:
            # Derivatives: estimate required margin as sum(notional_i / L_i)
            required_margin = 0.0
            for pos in self._view.positions.values():
                qty = float(pos.quantity)
                mpx = float(pos.mark_price or 0.0)
                if qty == 0.0 or mpx <= 0.0:
                    continue
                notional_i = abs(qty) * mpx
                lev_i = (
                    float(pos.leverage) if (pos.leverage and pos.leverage > 0) else 1.0
                )
                lev_i = max(1.0, lev_i)
                required_margin += notional_i / lev_i
            self._view.free_cash = max(0.0, equity - required_margin)

    def _compute_realized_delta(
        self,
        *,
        trade: TradeHistoryEntry,
        current_qty: float,
        quantity_delta: float,
        avg_price: float,
        fill_price: float,
    ) -> float:
        """Estimate realized PnL contribution for a trade.

        Prefer explicit realized_pnl on the trade when available; otherwise
        approximate based on position deltas. Fees are allocated proportionally
        to the quantity that actually closes existing exposure.
        """

        if trade.realized_pnl is not None:
            try:
                return float(trade.realized_pnl)
            except Exception:
                return 0.0

        realized = 0.0
        reduction = 0.0

        if current_qty > 0 and quantity_delta < 0:
            reduction = min(abs(quantity_delta), abs(current_qty))
            realized = (fill_price - avg_price) * reduction
        elif current_qty < 0 and quantity_delta > 0:
            reduction = min(abs(quantity_delta), abs(current_qty))
            realized = (avg_price - fill_price) * reduction

        if reduction > 0 and trade.fee_cost:
            executed = abs(quantity_delta)
            allocation = reduction / executed if executed > 0 else 1.0
            realized -= float(trade.fee_cost or 0.0) * allocation

        return realized
