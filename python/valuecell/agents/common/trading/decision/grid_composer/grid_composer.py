from __future__ import annotations

import math
from typing import List, Optional

from loguru import logger

from valuecell.agents.common.trading.constants import (
    FEATURE_GROUP_BY_KEY,
    FEATURE_GROUP_BY_MARKET_SNAPSHOT,
)

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
from .llm_param_advisor import GridParamAdvisor


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
        use_llm_params: bool = False,
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
        self._use_llm_params = bool(use_llm_params)
        self._llm_params_applied = False
        # Optional grid zone and discretization
        self._grid_lower_pct: Optional[float] = None
        self._grid_upper_pct: Optional[float] = None
        self._grid_count: Optional[int] = None
        # Dynamic LLM advice refresh control
        self._last_llm_advice_ts: Optional[int] = None
        self._llm_advice_refresh_sec: int = 300
        self._llm_advice_rationale: Optional[str] = None

    async def compose(self, context: ComposeContext) -> ComposeResult:
        ts = int(context.ts)
        # 0) Refresh interval is internal (no user-configurable grid_* fields)

        # 1) User grid overrides removed — parameters decided by the model only

        # 2) Refresh LLM advice periodically (always enabled)
        try:
            source_is_llm = True
            should_refresh = (
                (self._last_llm_advice_ts is None)
                or (
                    (ts - int(self._last_llm_advice_ts))
                    >= int(self._llm_advice_refresh_sec)
                )
                or (not self._llm_params_applied)
            )
            if source_is_llm and should_refresh:
                advisor = GridParamAdvisor(self._request)
                advice = await advisor.advise(context)
                if advice:
                    # Apply advised params with sanity clamps — model decides dynamically
                    self._step_pct = max(1e-6, float(advice.grid_step_pct))
                    self._max_steps = max(1, int(advice.grid_max_steps))
                    self._base_fraction = max(1e-6, float(advice.grid_base_fraction))
                    # Optional zone and grid discretization
                    if getattr(advice, "grid_lower_pct", None) is not None:
                        self._grid_lower_pct = max(0.0, float(advice.grid_lower_pct))
                    if getattr(advice, "grid_upper_pct", None) is not None:
                        self._grid_upper_pct = max(0.0, float(advice.grid_upper_pct))
                    if getattr(advice, "grid_count", None) is not None:
                        self._grid_count = max(1, int(advice.grid_count))
                        total_span = (self._grid_lower_pct or 0.0) + (
                            self._grid_upper_pct or 0.0
                        )
                        if total_span > 0.0:
                            self._step_pct = max(
                                1e-6, total_span / float(self._grid_count)
                            )
                            self._max_steps = max(1, int(self._grid_count))
                    # Capture advisor rationale when available
                    try:
                        self._llm_advice_rationale = getattr(
                            advice, "advisor_rationale", None
                        )
                    except Exception:
                        self._llm_advice_rationale = None
                    self._llm_params_applied = True
                    self._last_llm_advice_ts = ts
                    logger.info(
                        "Applied dynamic LLM grid params: step_pct={}, max_steps={}, base_fraction={}, lower={}, upper={}, count={}",
                        self._step_pct,
                        self._max_steps,
                        self._base_fraction,
                        self._grid_lower_pct,
                        self._grid_upper_pct,
                        self._grid_count,
                    )
        except Exception:
            # Non-fatal; continue with configured defaults
            pass

        # Prepare buying power/constraints/price map, then generate plan and reuse parent normalization
        equity, allowed_lev, constraints, _projected_gross, price_map = (
            self._init_buying_power_context(context)
        )

        items: List[TradeDecisionItem] = []

        # Pre-fetch micro change percentage from features (prefer 1s, fallback 1m)
        def latest_change_pct(
            symbol: str, *, allow_market_snapshot: bool = True
        ) -> Optional[float]:
            best: Optional[float] = None
            best_rank = 999
            for fv in context.features or []:
                try:
                    if str(getattr(fv.instrument, "symbol", "")) != symbol:
                        continue

                    meta = fv.meta or {}
                    interval = meta.get("interval")
                    group_key = meta.get(FEATURE_GROUP_BY_KEY)

                    # 1) Primary: candle features provide bare `change_pct` with interval
                    change = fv.values.get("change_pct")
                    used_market_snapshot = False

                    # 2) Fallback: market snapshot provides `price.change_pct`
                    if change is None:
                        if not allow_market_snapshot:
                            # Skip market snapshot-based percent change when disallowed
                            pass
                        else:
                            change = fv.values.get("price.change_pct")
                            used_market_snapshot = change is not None

                    # 3) Last resort: infer from price.last/close vs price.open
                    if change is None:
                        # Only allow price-based inference for candle intervals when snapshot disallowed
                        if allow_market_snapshot or (interval in ("1s", "1m")):
                            last_px = fv.values.get("price.last") or fv.values.get(
                                "price.close"
                            )
                            open_px = fv.values.get("price.open")
                            if last_px is not None and open_px is not None:
                                try:
                                    o = float(open_px)
                                    last_price = float(last_px)
                                    if o > 0:
                                        change = last_price / o - 1.0
                                        used_market_snapshot = (
                                            group_key
                                            == FEATURE_GROUP_BY_MARKET_SNAPSHOT
                                        )
                                except Exception:
                                    # ignore parse errors
                                    pass

                    if change is None:
                        continue

                    # Ranking preference:
                    # - 1s candle features are best
                    # - Market snapshot next (often closest to real-time)
                    # - 1m candle features then
                    # - Anything else last
                    if interval == "1s":
                        rank = 0
                    elif (
                        group_key == FEATURE_GROUP_BY_MARKET_SNAPSHOT
                    ) or used_market_snapshot:
                        rank = 1
                    elif interval == "1m":
                        rank = 2
                    else:
                        rank = 3

                    if rank < best_rank:
                        best = float(change)
                        best_rank = rank
                except Exception:
                    continue
            return best

        def snapshot_price_debug(symbol: str) -> str:
            keys = (
                "price.last",
                "price.close",
                "price.open",
                "price.bid",
                "price.ask",
                "price.mark",
                "funding.mark_price",
            )
            found: List[str] = []
            for fv in context.features or []:
                try:
                    if str(getattr(fv.instrument, "symbol", "")) != symbol:
                        continue
                    meta = fv.meta or {}
                    group_key = meta.get(FEATURE_GROUP_BY_KEY)
                    if group_key != FEATURE_GROUP_BY_MARKET_SNAPSHOT:
                        continue
                    for k in keys:
                        val = fv.values.get(k)
                        if val is not None:
                            try:
                                num = float(val)
                                found.append(f"{k}={num:.4f}")
                            except Exception:
                                found.append(f"{k}=<invalid>")
                except Exception:
                    continue
            return ", ".join(found) if found else "no snapshot price keys present"

        symbols = list(dict.fromkeys(self._request.trading_config.symbols))
        is_spot = self._request.exchange_config.market_type == MarketType.SPOT
        noop_reasons: List[str] = []

        for symbol in symbols:
            price = float(price_map.get(symbol) or 0.0)
            if price <= 0:
                logger.debug("Skip {} due to missing/invalid price", symbol)
                debug_info = snapshot_price_debug(symbol)
                noop_reasons.append(
                    f"{symbol}: missing or invalid price ({debug_info})"
                )
                continue

            pos = context.portfolio.positions.get(symbol)
            qty = float(getattr(pos, "quantity", 0.0) or 0.0)
            avg_px = float(getattr(pos, "avg_price", 0.0) or 0.0)

            # Base order size: equity fraction converted to quantity; parent applies risk controls
            base_qty = max(0.0, (equity * self._base_fraction) / price)
            if base_qty <= 0:
                noop_reasons.append(
                    f"{symbol}: base_qty=0 (equity={equity:.4f}, base_fraction={self._base_fraction:.4f}, price={price:.4f})"
                )
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
                chg = latest_change_pct(symbol, allow_market_snapshot=False)
                if chg is None:
                    # If no micro-interval change feature available, skip conservatively
                    noop_reasons.append(
                        f"{symbol}: 1s/1m candle change_pct unavailable; prefer NOOP"
                    )
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
                # Otherwise NOOP: thresholds not met (or short not allowed in spot)
                if is_spot and chg >= self._step_pct:
                    noop_reasons.append(
                        f"{symbol}: spot market — change_pct={chg:.4f} ≥ step={self._step_pct:.4f}, short open disabled"
                    )
                else:
                    noop_reasons.append(
                        f"{symbol}: no position — change_pct={chg:.4f} within [−{self._step_pct:.4f}, {self._step_pct:.4f}]"
                    )
                continue

            # With position: adjust around average using grid
            k = steps_from_avg(price, avg_px)
            if k <= 0:
                # No grid step triggered → NOOP
                if avg_px > 0:
                    move_pct = abs(price / avg_px - 1.0)
                    noop_reasons.append(
                        f"{symbol}: move_pct={move_pct:.4f} < step={self._step_pct:.4f} (around avg)"
                    )
                else:
                    noop_reasons.append(
                        f"{symbol}: missing avg_price; cannot evaluate grid steps"
                    )
                continue

            # Optional: enforce configured grid zone around average
            if (avg_px > 0) and (
                (self._grid_lower_pct is not None) or (self._grid_upper_pct is not None)
            ):
                lower_bound = avg_px * (1.0 - float(self._grid_lower_pct or 0.0))
                upper_bound = avg_px * (1.0 + float(self._grid_upper_pct or 0.0))
                if (price < lower_bound) or (price > upper_bound):
                    noop_reasons.append(
                        f"{symbol}: price {price:.4f} outside grid zone [{lower_bound:.4f}, {upper_bound:.4f}]"
                    )
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
                else:
                    if avg_px > 0:
                        lower = avg_px * (1.0 - self._step_pct)
                        upper = avg_px * (1.0 + self._step_pct)
                        noop_reasons.append(
                            f"{symbol}: short position — price {price:.4f} within grid [{lower:.4f}, {upper:.4f}]"
                        )
                    else:
                        noop_reasons.append(
                            f"{symbol}: short position — missing avg_price"
                        )
                continue

        # Build common rationale fragments for transparency
        # Grid parameters always come from the model now
        src = "LLM"
        zone_desc = None
        if (self._grid_lower_pct is not None) or (self._grid_upper_pct is not None):
            zone_desc = f"zone=[-{float(self._grid_lower_pct or 0.0):.4f}, +{float(self._grid_upper_pct or 0.0):.4f}]"
        count_desc = (
            f", count={int(self._grid_count)}" if self._grid_count is not None else ""
        )
        params_desc = f"params(source={src}, step_pct={self._step_pct:.4f}, max_steps={self._max_steps}, base_fraction={self._base_fraction:.4f}"
        if zone_desc:
            params_desc += f", {zone_desc}{count_desc}"
        params_desc += ")"
        # Include available buying power and free_cash for transparency when composing rationale
        try:
            if self._request.exchange_config.market_type == MarketType.SPOT:
                available_bp = max(0.0, float(equity))
            else:
                available_bp = max(
                    0.0,
                    float(equity) * float(allowed_lev) - float(_projected_gross or 0.0),
                )
        except Exception:
            available_bp = None

        free_cash_val = getattr(context.portfolio, "free_cash", None)
        bp_detail = (
            f", available_bp={float(available_bp):.4f}"
            if available_bp is not None
            else ""
        )
        fc_detail = (
            f", free_cash={float(free_cash_val):.4f}"
            if free_cash_val is not None
            else ""
        )
        bp_desc = f"normalization=filters+leverage_cap+buying_power(equity={float(equity):.4f}, allowed_lev={float(allowed_lev):.2f}{bp_detail}{fc_detail})"
        advisor_desc = (
            f"; advisor_rationale={self._llm_advice_rationale}"
            if self._llm_advice_rationale
            else ""
        )

        if not items:
            logger.debug(
                "GridComposer produced NOOP plan for compose_id={}", context.compose_id
            )
            # Compose a concise rationale summarizing why no actions were emitted
            summary = "; ".join(noop_reasons) if noop_reasons else "no triggers hit"
            rationale = f"Grid NOOP — reasons: {summary}. {params_desc}; {bp_desc}{advisor_desc}"
            return ComposeResult(instructions=[], rationale=rationale)

        plan = TradePlanProposal(
            ts=ts,
            items=items,
            rationale=f"Grid plan — {params_desc}; {bp_desc}{advisor_desc}",
        )
        # Reuse parent normalization: quantity filters, buying power, cap_factor, reduceOnly, etc.
        normalized = self._normalize_plan(context, plan)
        return ComposeResult(instructions=normalized, rationale=plan.rationale)
