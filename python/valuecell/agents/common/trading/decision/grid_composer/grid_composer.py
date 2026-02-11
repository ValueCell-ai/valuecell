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
    - Without positions: use recent change percent (prefer 1m feature) to
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
        
        # Track symbols that have hit Stop Loss and should not be traded anymore
        self._stopped_symbols: set[str] = set()
        
        # Tiered take-profit tracking: {symbol: {partial_closed: bool, peak_pnl: float}}
        self._tp_tracking: dict[str, dict] = {}

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
        # Define symbols early for use in TP/SL and param logic
        symbols = list(dict.fromkeys(self._request.trading_config.symbols))

        # 0) Quick pre-check: Skip LLM if no buying power and no positions to close
        # This saves expensive LLM calls when we can't trade anyway
        has_positions = any(
            context.portfolio.positions.get(sym) and 
            context.portfolio.positions[sym].quantity != 0
            for sym in symbols
        )
        buying_power = float(context.portfolio.buying_power or 0.0)
        min_required_bp = 1.0  # Minimum $1 to consider trading
        
        if not has_positions and buying_power < min_required_bp:
            logger.warning(
                f"⚠️ Skipping compose: No positions and insufficient buying power "
                f"(${buying_power:.2f} < ${min_required_bp:.2f}). "
                f"Skipping LLM call to save costs."
            )
            return ComposeResult(
                instructions=[],
                rationale=f"No action: Insufficient buying power (${buying_power:.2f}) and no positions to manage."
            )

        # 1) Refresh interval is internal (no user-configurable grid_* fields)

        # 2) User grid overrides removed — parameters decided by the model only

        # 3) Refresh LLM advice periodically (always enabled)
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
                        self._step_pct = max(0.003, float(advice.grid_step_pct))  # Minimum 0.3%
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

        # 3) Check Take Profit and Stop Loss - read from config (supports runtime changes)
        tp_pct_threshold = float(
            getattr(self._request.trading_config, 'take_profit_pct', 22.0)
        )
        sl_pct_threshold = float(
            getattr(self._request.trading_config, 'stop_loss_pct', -20.0)
        )
        logger.info(
            f"⚙️ TP/SL Config: Take Profit={tp_pct_threshold:.1f}%, Stop Loss={sl_pct_threshold:.1f}%"
        )
        items: List[TradeDecisionItem] = []
        noop_reasons: List[str] = []
        should_stop_strategy = False
        
        # 🔍 DEBUG: Log current positions at compose start
        position_symbols = list(context.portfolio.positions.keys())
        logger.info(f"📦 Compose start - Portfolio has {len(position_symbols)} positions: {position_symbols}")
        for sym in position_symbols:
            pos = context.portfolio.positions.get(sym)
            if pos and pos.quantity != 0:
                logger.info(f"  📊 Position {sym}: qty={pos.quantity:.4f}, avg_px={pos.avg_price:.4f}")

        # Helper to snapshot buy/sell ranges near current price
        def ranges_near(curr_px: float):
            pass  # Placeholder, not used in TP/SL check
        
        # Prepare buying power/constraints/price map, then generate plan and reuse parent normalization
        equity, allowed_lev, constraints, _projected_gross, price_map = (
            self._init_buying_power_context(context)
        )

        # Helper to resolve prev/curr prices for grid logic
        def resolve_prev_curr_prices(symbol: str) -> Optional[Tuple[float, float]]:
            # Prefer 1m change_pct from market snapshot
            for fv in context.features or []:
                if getattr(fv.instrument, "symbol", "") != symbol:
                    continue
                meta = fv.meta or {}
                group_key = meta.get(FEATURE_GROUP_BY_KEY)
                if group_key == FEATURE_GROUP_BY_MARKET_SNAPSHOT:
                    curr_px = fv.values.get("price.last")
                    prev_px = fv.values.get("price.open")  # Use open as previous
                    if curr_px is not None and prev_px is not None:
                        return float(prev_px), float(curr_px)
            # Fallback to current price and a synthetic previous price based on step_pct
            curr_px = float(price_map.get(symbol) or 0.0)
            if curr_px > 0:
                # If no historical data, assume previous price was within one step
                return curr_px * (1.0 - self._step_pct / 2), curr_px
            return None

        # Helper for debug info when price is missing
        def snapshot_price_debug(symbol: str) -> str:
            for fv in context.features or []:
                if getattr(fv.instrument, "symbol", "") != symbol:
                    continue
                meta = fv.meta or {}
                group_key = meta.get(FEATURE_GROUP_BY_KEY)
                if group_key == FEATURE_GROUP_BY_MARKET_SNAPSHOT:
                    return f"snapshot_price.last={fv.values.get('price.last')}, snapshot_price.open={fv.values.get('price.open')}"
            return "no market snapshot"

        # Determine market type once
        is_spot = self._request.exchange_config.market_type == MarketType.SPOT

        # 🔍 DEBUG: Log TP/SL check loop start
        logger.info(f"🎯 Starting TP/SL checks for {len(symbols)} symbols: {symbols}")
        
        for symbol in symbols:
            # If symbol is already stopped (hit SL previously), don't process it unless we still have position to close
            if symbol in self._stopped_symbols:
               # We might want to check here if position remains and retry close, otherwise skip
               logger.debug(f"⏭️ Skipping {symbol}: already in stopped_symbols")
               pass

            pos = context.portfolio.positions.get(symbol)
            if not pos:
                logger.debug(f"⏭️ Skipping {symbol}: no position found in portfolio")
                continue

            quantity = float(pos.quantity or 0.0)
            if quantity == 0.0:
                logger.debug(f"⏭️ Skipping {symbol}: position quantity is 0")
                continue
            
            logger.info(f"✅ Checking TP/SL for {symbol} with position qty={quantity:.4f}")

            # Calculate unrealized PnL % using reliable mark price
            mark_px = float(price_map.get(symbol) or pos.mark_price or 0.0)
            avg_px = float(pos.avg_price or 0.0)
            entry_ts = getattr(pos, "entry_ts", 0)

            if mark_px > 0 and avg_px > 0:
                # Calculate price movement percentage (without leverage)
                price_move_pct = 0.0
                if quantity > 0:
                    price_move_pct = (mark_px - avg_px) / avg_px * 100.0
                else:
                    price_move_pct = (avg_px - mark_px) / avg_px * 100.0
                
                # Get actual leverage from position (populated by exchange sync)
                actual_leverage = float(getattr(pos, 'leverage', 1.0) or 1.0)
                
                # DEBUG: Log if leverage seems wrong
                if actual_leverage == 1.0 and abs(price_move_pct) > 1.0:
                    logger.warning(
                        f"⚠️ {symbol}: leverage=1.0 but price moved {price_move_pct:.2f}%. "
                        f"Leverage might not be synced correctly from exchange!"
                    )
                
                # Real PnL considering leverage effect
                # For leveraged positions: actual_pnl% = price_movement% × leverage
                pnl_pct = price_move_pct * actual_leverage
                
                logger.info(
                    f"TP/SL Check: {symbol} qty={quantity:.4f} mark_px={mark_px:.4f} avg_px={avg_px:.4f} "
                    f"price_move={price_move_pct:.2f}% lev={actual_leverage:.1f}x pnl={pnl_pct:.2f}% "
                    f"(TP={tp_pct_threshold}% SL={sl_pct_threshold}%)"
                )
                
                # Get tiered TP config
                partial_tp_enabled = getattr(self._request.trading_config, 'partial_tp_enabled', True)
                partial_tp_threshold = float(getattr(self._request.trading_config, 'partial_tp_threshold_pct', 15.0))
                partial_tp_ratio = float(getattr(self._request.trading_config, 'partial_tp_close_ratio', 0.3))
                trailing_drawdown = float(getattr(self._request.trading_config, 'trailing_stop_drawdown_pct', 3.0))
                
                # Initialize tracking state for this symbol
                if symbol not in self._tp_tracking:
                    self._tp_tracking[symbol] = {'partial_closed': False, 'peak_pnl': pnl_pct}
                
                track = self._tp_tracking[symbol]
                if pnl_pct > track['peak_pnl']:
                    track['peak_pnl'] = pnl_pct
                
                # Tier 1: Partial take profit
                if partial_tp_enabled and not track['partial_closed'] and pnl_pct >= partial_tp_threshold:
                    action = TradeDecisionAction.CLOSE_LONG if quantity > 0 else TradeDecisionAction.CLOSE_SHORT
                    close_qty = abs(quantity) * partial_tp_ratio
                    logger.warning(f"[PARTIAL TP] {symbol}: pnl={pnl_pct:.2f}% >= {partial_tp_threshold}%. Closing {partial_tp_ratio*100:.0f}% ({close_qty:.4f})")
                    items.append(TradeDecisionItem(
                        instrument=InstrumentRef(symbol=symbol, exchange_id=self._request.exchange_config.exchange_id),
                        action=action, target_qty=close_qty, leverage=1.0, confidence=1.0,
                        rationale=f"Partial TP: pnl={pnl_pct:.2f}% >= {partial_tp_threshold}%. Closing {partial_tp_ratio*100:.0f}%."
                    ))
                    track['partial_closed'] = True
                    track['peak_pnl'] = pnl_pct
                    continue
                
                # Tier 2: Trailing stop (after partial close)
                if partial_tp_enabled and track['partial_closed']:
                    drawdown = track['peak_pnl'] - pnl_pct
                    if drawdown >= trailing_drawdown:
                        action = TradeDecisionAction.CLOSE_LONG if quantity > 0 else TradeDecisionAction.CLOSE_SHORT
                        logger.warning(f"[TRAILING STOP] {symbol}: peak={track['peak_pnl']:.2f}% current={pnl_pct:.2f}% drawdown={drawdown:.2f}%")
                        items.append(TradeDecisionItem(
                            instrument=InstrumentRef(symbol=symbol, exchange_id=self._request.exchange_config.exchange_id),
                            action=action, target_qty=abs(quantity), leverage=1.0, confidence=1.0,
                            rationale=f"Trailing stop: drawdown={drawdown:.2f}% from peak={track['peak_pnl']:.2f}%."
                        ))
                        self._tp_tracking[symbol] = {'partial_closed': False, 'peak_pnl': 0.0}
                        continue
                
                # Fallback: Full TP at higher threshold
                if pnl_pct >= tp_pct_threshold:
                    action = TradeDecisionAction.CLOSE_LONG if quantity > 0 else TradeDecisionAction.CLOSE_SHORT
                    logger.warning(f"[FULL TP] {symbol}: pnl={pnl_pct:.2f}% >= {tp_pct_threshold}%. Closing full position.")
                    items.append(TradeDecisionItem(
                        instrument=InstrumentRef(symbol=symbol, exchange_id=self._request.exchange_config.exchange_id),
                        action=action, target_qty=abs(quantity), leverage=1.0, confidence=1.0,
                        rationale=f"Full TP: pnl={pnl_pct:.2f}% >= {tp_pct_threshold}%.")
                    )
                    if symbol in self._tp_tracking:
                        self._tp_tracking[symbol] = {'partial_closed': False, 'peak_pnl': 0.0}
                    continue

                # Check Stop Loss
                if pnl_pct <= sl_pct_threshold:
                    action = TradeDecisionAction.CLOSE_LONG if quantity > 0 else TradeDecisionAction.CLOSE_SHORT
                    logger.error(
                        f"🛑 STOP LOSS triggered for {symbol}: pnl={pnl_pct:.2f}% <= {sl_pct_threshold}%. Closing position qty={abs(quantity):.4f} and STOPPING {symbol} strategy."
                    )
                    items.append(
                        TradeDecisionItem(
                            instrument=InstrumentRef(
                                symbol=symbol,
                                exchange_id=self._request.exchange_config.exchange_id,
                            ),
                            action=action,
                            target_qty=abs(quantity), # Close full position
                            leverage=1.0,
                            confidence=1.0,
                            rationale=f"Stop Loss triggered: pnl={pnl_pct:.2f}% <= {sl_pct_threshold}%. Closing position and STOPPING strategy for {symbol}. (Restart strategy to resume)."
                        )
                    )
                    self._stopped_symbols.add(symbol) # Blacklist this symbol
                    should_stop_strategy = True  # Signal coordinator to stop the strategy
                    continue # Skip grid logic for this symbol

        for symbol in symbols:
            # Skip if we already generated a critical TP/SL action for this symbol
            if any(item.instrument.symbol == symbol for item in items):
                continue
            
            # Skip if symbol is stopped (hit SL)
            if symbol in self._stopped_symbols:
                noop_reasons.append(f"{symbol}: STOPPED due to previous Stop Loss (Restart to resume).")
                continue

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
            
            # Adaptive adjustment: ensure base_qty meets minimum notional requirement
            # Extract min_notional from constraints (could be dict or scalar)
            min_notional_value = None
            if constraints and getattr(constraints, "min_notional", None) is not None:
                min_notional = constraints.min_notional
                if isinstance(min_notional, dict):
                    min_notional_value = min_notional.get(symbol)
                else:
                    min_notional_value = min_notional
            
            # If min_notional check fails, increase base_qty to meet requirement
            if min_notional_value is not None and min_notional_value > 0:
                notional = base_qty * price
                if notional < min_notional_value:
                    # Calculate minimum qty needed
                    min_qty = min_notional_value / price
                    logger.info(
                        f"📊 {symbol}: Adjusting base_qty from {base_qty:.6f} to {min_qty:.6f} "
                        f"(notional {notional:.2f} < min {min_notional_value:.2f})"
                    )
                    base_qty = min_qty
            
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
        
        # Capture stopped symbols in rationale
        stopped_desc = ""
        if self._stopped_symbols:
           stopped_desc = f". STOPPED_SYMBOLS={list(self._stopped_symbols)}"

        if not items:
            logger.debug(
                "GridComposer produced NOOP plan for compose_id={}", context.compose_id
            )
            # Compose a concise rationale summarizing why no actions were emitted
            summary = "; ".join(noop_reasons) if noop_reasons else "no triggers hit"
            rationale = f"Grid NOOP — reasons: {summary}. {params_desc}{advisor_desc}{stopped_desc}"
            return ComposeResult(instructions=[], rationale=rationale, should_stop=False)

        plan = TradePlanProposal(
            ts=ts,
            items=items,
            rationale=f"Grid plan — {params_desc}{advisor_desc}{stopped_desc}",
        )
        # Reuse parent normalization: quantity filters, buying power, cap_factor, reduceOnly, etc.
        normalized = self._normalize_plan(context, plan)
        return ComposeResult(
            instructions=normalized, 
            rationale=plan.rationale,
            should_stop=should_stop_strategy
        )
