from __future__ import annotations

import math
from typing import List, Optional, Tuple

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
        # Apply stability: do not change params frequently unless market clearly shifts
        self._market_change_threshold_pct: float = (
            0.01  # 1% absolute change triggers update
        )
        # Minimum grid zone bounds (relative to avg price) to ensure clear trading window
        self._min_grid_zone_pct: float = 0.10  # at least ±10%
        # Limit per-update grid_count change to avoid oscillation
        self._max_grid_count_delta: int = 2

    def _max_abs_change_pct(self, context: ComposeContext) -> Optional[float]:
        symbols = list(self._request.trading_config.symbols or [])
        max_abs: Optional[float] = None
        for fv in context.features or []:
            try:
                sym = str(getattr(fv.instrument, "symbol", ""))
                if sym not in symbols:
                    continue
                change = fv.values.get("change_pct")
                if change is None:
                    change = fv.values.get("price.change_pct")
                if change is None:
                    last_px = fv.values.get("price.last") or fv.values.get(
                        "price.close"
                    )
                    open_px = fv.values.get("price.open")
                    if last_px is not None and open_px is not None:
                        try:
                            change = (float(last_px) - float(open_px)) / float(open_px)
                        except Exception:
                            change = None
                if change is None:
                    continue
                val = abs(float(change))
                if (max_abs is None) or (val > max_abs):
                    max_abs = val
            except Exception:
                continue
        return max_abs

    def _has_clear_market_change(self, context: ComposeContext) -> bool:
        try:
            max_abs = self._max_abs_change_pct(context)
            if max_abs is None:
                return False
            return max_abs >= float(self._market_change_threshold_pct)
        except Exception:
            return False

    def _zone_suffix(self, context: ComposeContext) -> str:
        """Return a concise zone description suffix for rationales.
        Prefer price ranges based on positions' avg_price; fall back to pct.
        """
        if (self._grid_lower_pct is None) and (self._grid_upper_pct is None):
            return ""
        try:
            zone_entries = []
            positions = getattr(context.portfolio, "positions", None) or {}
            for sym, pos in positions.items():
                avg_px = getattr(pos, "avg_price", None)
                if avg_px is None or float(avg_px) <= 0.0:
                    continue
                lower_bound = float(avg_px) * (1.0 - float(self._grid_lower_pct or 0.0))
                upper_bound = float(avg_px) * (1.0 + float(self._grid_upper_pct or 0.0))
                zone_entries.append(f"{sym}=[{lower_bound:.4f}, {upper_bound:.4f}]")
            if zone_entries:
                return " — zone_prices(" + "; ".join(zone_entries) + ")"
        except Exception:
            pass
        return f" — zone_pct=[-{float(self._grid_lower_pct or 0.0):.4f}, +{float(self._grid_upper_pct or 0.0):.4f}]"

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
                prev_params = {
                    "grid_step_pct": self._step_pct,
                    "grid_max_steps": self._max_steps,
                    "grid_base_fraction": self._base_fraction,
                    "grid_lower_pct": self._grid_lower_pct,
                    "grid_upper_pct": self._grid_upper_pct,
                    "grid_count": self._grid_count,
                }
                advisor = GridParamAdvisor(self._request, prev_params=prev_params)
                advice = await advisor.advise(context)
                if advice:
                    # Decide whether to apply new params based on market change
                    apply_new = (
                        not self._llm_params_applied
                    ) or self._has_clear_market_change(context)
                    if apply_new:
                        # Apply advised params with sanity clamps — model decides dynamically
                        self._step_pct = max(1e-6, float(advice.grid_step_pct))
                        self._max_steps = max(1, int(advice.grid_max_steps))
                        self._base_fraction = max(
                            1e-6, float(advice.grid_base_fraction)
                        )
                        # Optional zone and grid discretization with minimum ±10% bounds
                        if getattr(advice, "grid_lower_pct", None) is not None:
                            proposed_lower = max(0.0, float(advice.grid_lower_pct))
                        else:
                            proposed_lower = self._min_grid_zone_pct
                        if getattr(advice, "grid_upper_pct", None) is not None:
                            proposed_upper = max(0.0, float(advice.grid_upper_pct))
                        else:
                            proposed_upper = self._min_grid_zone_pct
                        # Enforce minimum zone widths
                        self._grid_lower_pct = max(
                            self._min_grid_zone_pct, proposed_lower
                        )
                        self._grid_upper_pct = max(
                            self._min_grid_zone_pct, proposed_upper
                        )
                        if getattr(advice, "grid_count", None) is not None:
                            proposed_count = max(1, int(advice.grid_count))
                            if self._grid_count is not None:
                                # Clamp change to avoid abrupt jumps (±self._max_grid_count_delta)
                                lower_bound = max(
                                    1,
                                    int(self._grid_count)
                                    - int(self._max_grid_count_delta),
                                )
                                upper_bound = int(self._grid_count) + int(
                                    self._max_grid_count_delta
                                )
                                self._grid_count = max(
                                    lower_bound, min(upper_bound, proposed_count)
                                )
                            else:
                                self._grid_count = proposed_count
                            total_span = (self._grid_lower_pct or 0.0) + (
                                self._grid_upper_pct or 0.0
                            )
                            if total_span > 0.0:
                                self._step_pct = max(
                                    1e-6, total_span / float(self._grid_count)
                                )
                                self._max_steps = max(1, int(self._grid_count))
                        self._llm_params_applied = True
                        logger.info(
                            "Applied dynamic LLM grid params: step_pct={}, max_steps={}, base_fraction={}, lower={}, upper={}, count={}",
                            self._step_pct,
                            self._max_steps,
                            self._base_fraction,
                            self._grid_lower_pct,
                            self._grid_upper_pct,
                            self._grid_count,
                        )
                    else:
                        logger.info(
                            "Suppressed grid param update due to stable market (threshold={}): keeping step_pct={}, max_steps={}, base_fraction={}",
                            self._market_change_threshold_pct,
                            self._step_pct,
                            self._max_steps,
                            self._base_fraction,
                        )
                    # Capture advisor rationale when available
                    try:
                        self._llm_advice_rationale = getattr(
                            advice, "advisor_rationale", None
                        )
                    except Exception:
                        self._llm_advice_rationale = None
                    self._last_llm_advice_ts = ts
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

        # Resolve previous and current price pair for the symbol using best available feature
        def resolve_prev_curr_prices(symbol: str) -> Optional[Tuple[float, float]]:
            best_pair: Optional[Tuple[float, float]] = None
            best_rank = 999
            for fv in context.features or []:
                try:
                    if str(getattr(fv.instrument, "symbol", "")) != symbol:
                        continue
                    meta = fv.meta or {}
                    interval = meta.get("interval")
                    group_key = meta.get(FEATURE_GROUP_BY_KEY)
                    open_px = fv.values.get("price.open")
                    last_px = fv.values.get("price.last") or fv.values.get(
                        "price.close"
                    )
                    if open_px is None or last_px is None:
                        continue
                    try:
                        o = float(open_px)
                        last_price = float(last_px)
                        if o <= 0 or last_price <= 0:
                            continue
                    except Exception:
                        continue
                    if interval == "1s":
                        rank = 0
                    elif group_key == FEATURE_GROUP_BY_MARKET_SNAPSHOT:
                        rank = 1
                    elif interval == "1m":
                        rank = 2
                    else:
                        rank = 3
                    if rank < best_rank:
                        best_pair = (o, last_price)
                        best_rank = rank
                except Exception:
                    continue
            return best_pair

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

            # Base order size per grid: equity fraction converted to quantity; parent applies risk controls
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

            # No position: open when current price crosses a grid step from previous price
            if abs(qty) <= self._quantity_precision:
                pair = resolve_prev_curr_prices(symbol)
                if pair is None:
                    noop_reasons.append(
                        f"{symbol}: prev/curr price unavailable; prefer NOOP"
                    )
                    continue
                prev_px, curr_px = pair
                # Compute grid indices around a reference (use curr_px as temporary anchor)
                # For initial opens, direction follows price movement across a step
                moved_down = curr_px <= prev_px * (1.0 - self._step_pct)
                moved_up = curr_px >= prev_px * (1.0 + self._step_pct)
                if moved_down:
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
                            confidence=1.0,
                            rationale=f"Grid open-long: crossed down ≥1 step from prev {prev_px:.4f} to {curr_px:.4f}{self._zone_suffix(context)}",
                        )
                    )
                elif (not is_spot) and moved_up:
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
                            confidence=1.0,
                            rationale=f"Grid open-short: crossed up ≥1 step from prev {prev_px:.4f} to {curr_px:.4f}{self._zone_suffix(context)}",
                        )
                    )
                else:
                    noop_reasons.append(
                        f"{symbol}: no position — no grid step crossed (prev={prev_px:.4f}, curr={curr_px:.4f})"
                    )
                continue

            # With position: adjust strictly when crossing grid lines from previous to current price
            pair = resolve_prev_curr_prices(symbol)
            if pair is None or avg_px <= 0:
                noop_reasons.append(
                    f"{symbol}: missing prev/curr or avg price; cannot evaluate grid crossing"
                )
                continue
            prev_px, curr_px = pair

            # Compute integer grid indices relative to avg price
            def grid_index(px: float) -> int:
                return int(math.floor((px / avg_px - 1.0) / max(self._step_pct, 1e-9)))

            gi_prev = grid_index(prev_px)
            gi_curr = grid_index(curr_px)
            delta_idx = gi_curr - gi_prev
            if delta_idx == 0:
                lower = avg_px * (1.0 - self._step_pct)
                upper = avg_px * (1.0 + self._step_pct)
                noop_reasons.append(
                    f"{symbol}: position — no grid index change (prev={prev_px:.4f}, curr={curr_px:.4f}) within [{lower:.4f}, {upper:.4f}]"
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
                # Cap per-cycle applied steps by max_steps to avoid oversized reactions
                applied_steps = min(abs(delta_idx), int(self._max_steps))
                if delta_idx < 0:
                    items.append(
                        TradeDecisionItem(
                            instrument=InstrumentRef(
                                symbol=symbol,
                                exchange_id=self._request.exchange_config.exchange_id,
                            ),
                            action=TradeDecisionAction.OPEN_LONG,
                            # per-crossing sizing: one base per grid crossed
                            target_qty=base_qty * applied_steps,
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
                            confidence=min(1.0, applied_steps / float(self._max_steps)),
                            rationale=f"Grid long add: crossed {abs(delta_idx)} grid(s) down, applying {applied_steps} (prev={prev_px:.4f} → curr={curr_px:.4f}) around avg {avg_px:.4f}{self._zone_suffix(context)}",
                        )
                    )
                elif delta_idx > 0:
                    items.append(
                        TradeDecisionItem(
                            instrument=InstrumentRef(
                                symbol=symbol,
                                exchange_id=self._request.exchange_config.exchange_id,
                            ),
                            action=TradeDecisionAction.CLOSE_LONG,
                            target_qty=min(abs(qty), base_qty * applied_steps),
                            leverage=1.0,
                            confidence=min(1.0, applied_steps / float(self._max_steps)),
                            rationale=f"Grid long reduce: crossed {abs(delta_idx)} grid(s) up, applying {applied_steps} (prev={prev_px:.4f} → curr={curr_px:.4f}) around avg {avg_px:.4f}{self._zone_suffix(context)}",
                        )
                    )
                continue

            # Short: add on up, cover on down
            if qty < 0:
                applied_steps = min(abs(delta_idx), int(self._max_steps))
                if delta_idx > 0 and (not is_spot):
                    items.append(
                        TradeDecisionItem(
                            instrument=InstrumentRef(
                                symbol=symbol,
                                exchange_id=self._request.exchange_config.exchange_id,
                            ),
                            action=TradeDecisionAction.OPEN_SHORT,
                            target_qty=base_qty * applied_steps,
                            leverage=min(
                                float(self._request.trading_config.max_leverage or 1.0),
                                float(
                                    constraints.max_leverage
                                    or self._request.trading_config.max_leverage
                                    or 1.0
                                ),
                            ),
                            confidence=min(1.0, applied_steps / float(self._max_steps)),
                            rationale=f"Grid short add: crossed {abs(delta_idx)} grid(s) up, applying {applied_steps} (prev={prev_px:.4f} → curr={curr_px:.4f}) around avg {avg_px:.4f}{self._zone_suffix(context)}",
                        )
                    )
                elif delta_idx < 0:
                    items.append(
                        TradeDecisionItem(
                            instrument=InstrumentRef(
                                symbol=symbol,
                                exchange_id=self._request.exchange_config.exchange_id,
                            ),
                            action=TradeDecisionAction.CLOSE_SHORT,
                            target_qty=min(abs(qty), base_qty * applied_steps),
                            leverage=1.0,
                            confidence=min(1.0, applied_steps / float(self._max_steps)),
                            rationale=f"Grid short cover: crossed {abs(delta_idx)} grid(s) down, applying {applied_steps} (prev={prev_px:.4f} → curr={curr_px:.4f}) around avg {avg_px:.4f}{self._zone_suffix(context)}",
                        )
                    )
                else:
                    if avg_px > 0:
                        lower = avg_px * (1.0 - self._step_pct)
                        upper = avg_px * (1.0 + self._step_pct)
                        noop_reasons.append(
                            f"{symbol}: short position — no grid index change (prev={prev_px:.4f}, curr={curr_px:.4f}) within [{lower:.4f}, {upper:.4f}]"
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
            # Prefer price-based zone display using current positions' avg_price
            try:
                zone_entries = []
                for sym, pos in (context.portfolio.positions or {}).items():
                    avg_px = getattr(pos, "avg_price", None)
                    if avg_px is None or float(avg_px) <= 0.0:
                        continue
                    lower_bound = float(avg_px) * (
                        1.0 - float(self._grid_lower_pct or 0.0)
                    )
                    upper_bound = float(avg_px) * (
                        1.0 + float(self._grid_upper_pct or 0.0)
                    )
                    zone_entries.append(f"{sym}=[{lower_bound:.4f}, {upper_bound:.4f}]")
                if zone_entries:
                    zone_desc = "zone_prices(" + "; ".join(zone_entries) + ")"
                else:
                    # Fallback to percent display when no avg_price available
                    zone_desc = f"zone_pct=[-{float(self._grid_lower_pct or 0.0):.4f}, +{float(self._grid_upper_pct or 0.0):.4f}]"
            except Exception:
                zone_desc = f"zone_pct=[-{float(self._grid_lower_pct or 0.0):.4f}, +{float(self._grid_upper_pct or 0.0):.4f}]"
        count_desc = (
            f", count={int(self._grid_count)}" if self._grid_count is not None else ""
        )
        params_desc = f"params(source={src}, step_pct={self._step_pct:.4f}, max_steps={self._max_steps}, base_fraction={self._base_fraction:.4f}"
        if zone_desc:
            params_desc += f", {zone_desc}"
        params_desc += f"{count_desc})"
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
            rationale = f"Grid NOOP — reasons: {summary}. {params_desc}{advisor_desc}"
            return ComposeResult(instructions=[], rationale=rationale)

        plan = TradePlanProposal(
            ts=ts,
            items=items,
            rationale=f"Grid plan — {params_desc}{advisor_desc}",
        )
        # Reuse parent normalization: quantity filters, buying power, cap_factor, reduceOnly, etc.
        normalized = self._normalize_plan(context, plan)
        return ComposeResult(instructions=normalized, rationale=plan.rationale)
