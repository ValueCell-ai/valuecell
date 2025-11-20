from __future__ import annotations

import math
from typing import List, Optional

from loguru import logger

from ...models import (
    ComposeContext,
    ComposeResult,
    InstrumentRef,
    MarketType,
    TradeDecisionAction,
    TradeDecisionItem,
    TradePlanProposal,
    UserRequest,
)
from ..interfaces import BaseComposer


class GridComposer(BaseComposer):
    """Rule-based grid strategy composer.

    Goal: avoid LLM usage by applying simple mean-reversion grid rules to
    produce an `TradePlanProposal`, then reuse the parent normalization and
    risk controls (`_normalize_plan`) to output executable `TradeInstruction`s.

    Key rules:
    - Define grid step with `step_pct` (e.g., 0.5%).
    - With positions: price falling ≥ 1 step vs average adds; rising ≥ 1 step
      reduces (max `max_steps` per cycle).
    - Without positions: use recent change percent (prefer 1s feature) to
      trigger open; spot opens long only, perps can open both directions.
    - Base size is `equity * base_fraction / price`; `_normalize_plan` later
      clamps by filters and buying power.
    """

    def __init__(
        self,
        request: UserRequest,
        *,
        step_pct: float = 0.005,
        max_steps: int = 3,
        base_fraction: float = 0.08,
        default_slippage_bps: int = 25,
        quantity_precision: float = 1e-9,
    ) -> None:
        super().__init__(
            request,
            default_slippage_bps=default_slippage_bps,
            quantity_precision=quantity_precision,
        )
        self._step_pct = float(step_pct)
        self._max_steps = int(max_steps)
        self._base_fraction = float(base_fraction)

    async def compose(self, context: ComposeContext) -> ComposeResult:
        # Prepare buying power/constraints/price map, then generate plan and reuse parent normalization
        equity, allowed_lev, constraints, _projected_gross, price_map = (
            self._init_buying_power_context(context)
        )

        items: List[TradeDecisionItem] = []
        ts = int(context.ts)

        # Pre-fetch micro change percentage from features (prefer 1s, fallback 1m)
        def latest_change_pct(symbol: str) -> Optional[float]:
            best: Optional[float] = None
            best_rank = 999
            for fv in context.features or []:
                try:
                    if str(getattr(fv.instrument, "symbol", "")) != symbol:
                        continue
                    interval = (fv.meta or {}).get("interval")
                    change = fv.values.get("change_pct")
                    if change is None:
                        continue
                    rank = 0 if interval == "1s" else (1 if interval == "1m" else 2)
                    if rank < best_rank:
                        best = float(change)
                        best_rank = rank
                except Exception:
                    continue
            return best

        symbols = list(dict.fromkeys(self._request.trading_config.symbols))
        is_spot = self._request.exchange_config.market_type == MarketType.SPOT

        for symbol in symbols:
            price = float(price_map.get(symbol) or 0.0)
            if price <= 0:
                logger.debug("Skip {} due to missing/invalid price", symbol)
                continue

            pos = context.portfolio.positions.get(symbol)
            qty = float(getattr(pos, "quantity", 0.0) or 0.0)
            avg_px = float(getattr(pos, "avg_price", 0.0) or 0.0)

            # Base order size: equity fraction converted to quantity; parent applies risk controls
            base_qty = max(0.0, (equity * self._base_fraction) / price)
            if base_qty <= 0:
                continue

            # Compute steps from average price when holding; without average, trigger one step
            def steps_from_avg(px: float, avg: float) -> int:
                if avg <= 0:
                    return 1
                move_pct = abs(px / avg - 1.0)
                k = int(math.floor(move_pct / max(self._step_pct, 1e-9)))
                return max(0, min(k, self._max_steps))

            # No position: use latest change to trigger direction (spot long-only)
            if abs(qty) <= self._quantity_precision:
                chg = latest_change_pct(symbol)
                if chg is None:
                    # If no change feature available, skip conservatively
                    continue
                if chg <= -self._step_pct:
                    # Short-term drop → open long
                    items.append(
                        TradeDecisionItem(
                            instrument=InstrumentRef(
                                symbol=symbol,
                                exchange_id=self._request.exchange_config.exchange_id,
                            ),
                            action=TradeDecisionAction.OPEN_LONG,
                            target_qty=base_qty,
                            leverage=(
                                1.0
                                if is_spot
                                else min(
                                    float(
                                        self._request.trading_config.max_leverage or 1.0
                                    ),
                                    float(
                                        constraints.max_leverage
                                        or self._request.trading_config.max_leverage
                                        or 1.0
                                    ),
                                )
                            ),
                            confidence=min(1.0, abs(chg) / (2 * self._step_pct)),
                            rationale=f"Grid open-long: change_pct={chg:.4f} ≤ -step={self._step_pct:.4f}",
                        )
                    )
                elif (not is_spot) and chg >= self._step_pct:
                    # Short-term rise → open short (perpetual only)
                    items.append(
                        TradeDecisionItem(
                            instrument=InstrumentRef(
                                symbol=symbol,
                                exchange_id=self._request.exchange_config.exchange_id,
                            ),
                            action=TradeDecisionAction.OPEN_SHORT,
                            target_qty=base_qty,
                            leverage=min(
                                float(self._request.trading_config.max_leverage or 1.0),
                                float(
                                    constraints.max_leverage
                                    or self._request.trading_config.max_leverage
                                    or 1.0
                                ),
                            ),
                            confidence=min(1.0, abs(chg) / (2 * self._step_pct)),
                            rationale=f"Grid open-short: change_pct={chg:.4f} ≥ step={self._step_pct:.4f}",
                        )
                    )
                # Otherwise NOOP
                continue

            # With position: adjust around average using grid
            k = steps_from_avg(price, avg_px)
            if k <= 0:
                # No grid step triggered → NOOP
                continue

            # Long: add on down, reduce on up
            if qty > 0:
                down = (avg_px > 0) and (price <= avg_px * (1.0 - self._step_pct))
                up = (avg_px > 0) and (price >= avg_px * (1.0 + self._step_pct))
                if down:
                    items.append(
                        TradeDecisionItem(
                            instrument=InstrumentRef(
                                symbol=symbol,
                                exchange_id=self._request.exchange_config.exchange_id,
                            ),
                            action=TradeDecisionAction.OPEN_LONG,
                            target_qty=base_qty * k,
                            leverage=1.0
                            if is_spot
                            else min(
                                float(self._request.trading_config.max_leverage or 1.0),
                                float(
                                    constraints.max_leverage
                                    or self._request.trading_config.max_leverage
                                    or 1.0
                                ),
                            ),
                            confidence=min(1.0, k / float(self._max_steps)),
                            rationale=f"Grid long add: price {price:.4f} ≤ avg {avg_px:.4f} by {k} steps",
                        )
                    )
                elif up:
                    items.append(
                        TradeDecisionItem(
                            instrument=InstrumentRef(
                                symbol=symbol,
                                exchange_id=self._request.exchange_config.exchange_id,
                            ),
                            action=TradeDecisionAction.CLOSE_LONG,
                            target_qty=min(abs(qty), base_qty * k),
                            leverage=1.0,
                            confidence=min(1.0, k / float(self._max_steps)),
                            rationale=f"Grid long reduce: price {price:.4f} ≥ avg {avg_px:.4f} by {k} steps",
                        )
                    )
                continue

            # Short: add on up, cover on down
            if qty < 0:
                up = (avg_px > 0) and (price >= avg_px * (1.0 + self._step_pct))
                down = (avg_px > 0) and (price <= avg_px * (1.0 - self._step_pct))
                if up and (not is_spot):
                    items.append(
                        TradeDecisionItem(
                            instrument=InstrumentRef(
                                symbol=symbol,
                                exchange_id=self._request.exchange_config.exchange_id,
                            ),
                            action=TradeDecisionAction.OPEN_SHORT,
                            target_qty=base_qty * k,
                            leverage=min(
                                float(self._request.trading_config.max_leverage or 1.0),
                                float(
                                    constraints.max_leverage
                                    or self._request.trading_config.max_leverage
                                    or 1.0
                                ),
                            ),
                            confidence=min(1.0, k / float(self._max_steps)),
                            rationale=f"Grid short add: price {price:.4f} ≥ avg {avg_px:.4f} by {k} steps",
                        )
                    )
                elif down:
                    items.append(
                        TradeDecisionItem(
                            instrument=InstrumentRef(
                                symbol=symbol,
                                exchange_id=self._request.exchange_config.exchange_id,
                            ),
                            action=TradeDecisionAction.CLOSE_SHORT,
                            target_qty=min(abs(qty), base_qty * k),
                            leverage=1.0,
                            confidence=min(1.0, k / float(self._max_steps)),
                            rationale=f"Grid short cover: price {price:.4f} ≤ avg {avg_px:.4f} by {k} steps",
                        )
                    )
                continue

        if not items:
            logger.debug(
                "GridComposer produced NOOP plan for compose_id={}", context.compose_id
            )
            return ComposeResult(instructions=[], rationale="Grid NOOP")

        plan = TradePlanProposal(
            ts=ts,
            items=items,
            rationale=f"Grid step={self._step_pct:.4f}, base_fraction={self._base_fraction:.3f}",
        )
        # Reuse parent normalization: quantity filters, buying power, cap_factor, reduceOnly, etc.
        normalized = self._normalize_plan(context, plan)
        return ComposeResult(instructions=normalized, rationale=plan.rationale)
