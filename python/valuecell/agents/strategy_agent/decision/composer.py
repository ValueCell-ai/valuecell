from __future__ import annotations

import json
import math
from typing import Dict, List, Optional

from agno.agent import Agent as AgnoAgent
from loguru import logger
from pydantic import ValidationError

from valuecell.utils import env as env_utils
from valuecell.utils import model as model_utils

from ..models import (
    ComposeContext,
    Constraints,
    LlmDecisionAction,
    LlmPlanProposal,
    MarketType,
    TradeInstruction,
    TradeSide,
    UserRequest,
)
from ..utils import extract_price_map
from .interfaces import Composer
from .system_prompt import SYSTEM_PROMPT


class LlmComposer(Composer):
    """LLM-driven composer that turns context into trade instructions.

    The core flow follows the README design:
    1. Build a serialized prompt from the compose context (features, portfolio,
       digest, prompt text, market snapshot, constraints).
    2. Call an LLM to obtain an :class:`LlmPlanProposal` (placeholder method).
    3. Normalize the proposal into executable :class:`TradeInstruction` objects,
       applying guardrails based on context constraints and trading config.

    The `_call_llm` method is intentionally left unimplemented so callers can
    supply their own integration. Override it in a subclass or monkeypatch at
    runtime. The method should accept a string prompt and return an instance of
    :class:`LlmPlanProposal` (validated via Pydantic).
    """

    def __init__(
        self,
        request: UserRequest,
        *,
        default_slippage_bps: int = 25,
        quantity_precision: float = 1e-9,
    ) -> None:
        self._request = request
        self._default_slippage_bps = default_slippage_bps
        self._quantity_precision = quantity_precision

    async def compose(self, context: ComposeContext) -> List[TradeInstruction]:
        prompt = self._build_llm_prompt(context)
        try:
            plan = await self._call_llm(prompt)
            if not plan.items:
                logger.info(
                    "LLM returned empty plan for compose_id={} with rationale={}",
                    context.compose_id,
                    plan.rationale,
                )
                return []
        except ValidationError as exc:
            logger.error("LLM output failed validation: {}", exc)
            return []
        except Exception:  # noqa: BLE001
            logger.exception("LLM invocation failed")
            return []

        return self._normalize_plan(context, plan)

    # ------------------------------------------------------------------
    # Prompt + LLM helpers

    @staticmethod
    def _prune_none(obj):
        """Recursively remove None, empty dict, and empty list values."""
        if isinstance(obj, dict):
            pruned = {
                k: LlmComposer._prune_none(v) for k, v in obj.items() if v is not None
            }
            return {k: v for k, v in pruned.items() if v not in (None, {}, [])}
        if isinstance(obj, list):
            pruned = [LlmComposer._prune_none(v) for v in obj]
            return [v for v in pruned if v not in (None, {}, [])]
        return obj

    def _compact_market_snapshot(self, snapshot: Dict) -> Dict:
        """Extract decision-critical fields from market snapshot.

        Reduces ~70% token usage while preserving key signals.
        """
        compact = {}
        for symbol, data in snapshot.items():
            if not isinstance(data, dict):
                continue

            entry = {}
            # Price action
            if price := data.get("price"):
                if isinstance(price, dict):
                    entry["last"] = price.get("last") or price.get("close")
                    entry["change_pct"] = price.get("percentage")
                    entry["volume_24h"] = price.get("baseVolume")

            # Open interest
            if oi := data.get("open_interest"):
                if isinstance(oi, dict):
                    entry["open_interest"] = oi.get("openInterestAmount") or oi.get(
                        "baseVolume"
                    )

            # Funding rate
            if fr := data.get("funding_rate"):
                if isinstance(fr, dict):
                    entry["funding_rate"] = fr.get("fundingRate")
                    entry["mark_price"] = fr.get("markPrice")

            if entry:
                compact[symbol] = {k: v for k, v in entry.items() if v is not None}

        return compact

    def _organize_features(self, features: List) -> Dict:
        """Organize features by interval and remove redundant metadata.

        Dynamically groups features by their interval (e.g., 1s, 1m, 5m, 15m).
        """
        by_interval = {}

        for fv in features:
            data = fv.model_dump(mode="json")
            interval = data.get("meta", {}).get("interval", "")

            if not interval:
                continue

            # Remove window timestamps (not useful for LLM)
            if "meta" in data:
                data["meta"] = {
                    "interval": interval,
                    "count": data["meta"].get("count"),
                }

            # Group by interval
            if interval not in by_interval:
                by_interval[interval] = []
            by_interval[interval].append(data)

        return by_interval

    def _build_summary(self, context: ComposeContext) -> Dict:
        """Build portfolio summary with risk metrics."""
        pv = context.portfolio

        return {
            "active_positions": sum(
                1
                for snap in pv.positions.values()
                if abs(float(getattr(snap, "quantity", 0.0) or 0.0)) > 0.0
            ),
            "total_value": pv.total_value,
            "account_balance": pv.account_balance,
            "free_cash": pv.free_cash,
            "unrealized_pnl": pv.total_unrealized_pnl,
            "sharpe_ratio": context.digest.sharpe_ratio,
        }

    def _build_llm_prompt(self, context: ComposeContext) -> str:
        """Build structured prompt for LLM decision-making.

        Produces a compact JSON with:
        - summary: portfolio metrics + risk signals
        - market: compacted price/OI/funding data
        - features: organized by interval (1m structural, 1s realtime)
        - portfolio: current positions
        - digest: per-symbol historical performance
        """
        pv = context.portfolio

        # Build components
        summary = self._build_summary(context)
        market = self._compact_market_snapshot(context.market_snapshot or {})
        features = self._organize_features(context.features)

        # Portfolio positions
        positions = [
            {
                "symbol": sym,
                "qty": float(snap.quantity),
                "avg_px": snap.avg_price,
                "unrealized_pnl": snap.unrealized_pnl,
            }
            for sym, snap in pv.positions.items()
            if abs(float(snap.quantity)) > 0
        ]

        # Constraints
        constraints = (
            pv.constraints.model_dump(mode="json", exclude_none=True)
            if pv.constraints
            else {}
        )

        payload = self._prune_none(
            {
                "strategy_prompt": context.prompt_text,
                "summary": summary,
                "market": market,
                "features": features,
                "positions": positions,
                "constraints": constraints,
            }
        )

        instructions = (
            "Read Context and decide. "
            "features.1m = structural trends (240 periods), features.1s = realtime signals (180 periods). "
            "market.funding_rate: positive = longs pay shorts. "
            "Respect constraints and risk_flags. Prefer NOOP when edge unclear. "
            "Output JSON with items array."
        )

        return f"{instructions}\n\nContext:\n{json.dumps(payload, ensure_ascii=False)}"

    async def _call_llm(self, prompt: str) -> LlmPlanProposal:
        """Invoke an LLM asynchronously and parse the response into LlmPlanProposal.

        This implementation follows the parser_agent pattern: it creates a model
        via `create_model_with_provider`, wraps it in an `agno.agent.Agent` with
        `output_schema=LlmPlanProposal`, and awaits `agent.arun(prompt)`. The
        agent's `response.content` is returned (or validated) as a
        `LlmPlanProposal`.
        """

        cfg = self._request.llm_model_config
        model = model_utils.create_model_with_provider(
            provider=cfg.provider,
            model_id=cfg.model_id,
            api_key=cfg.api_key,
        )

        # Wrap model in an Agent (consistent with parser_agent usage)
        agent = AgnoAgent(
            model=model,
            output_schema=LlmPlanProposal,
            markdown=False,
            instructions=[SYSTEM_PROMPT],
            use_json_mode=model_utils.model_should_use_json_mode(model),
            debug_mode=env_utils.agent_debug_mode_enabled(),
        )
        response = await agent.arun(prompt)
        content = getattr(response, "content", None) or response
        logger.debug("Received LLM response {}", content)
        return content

    # ------------------------------------------------------------------
    # Normalization / guardrails helpers

    def _init_buying_power_context(
        self,
        context: ComposeContext,
    ) -> tuple:
        """Initialize buying power tracking context.

        Returns:
            (equity, allowed_lev, constraints, projected_gross, price_map)
        """
        constraints = context.portfolio.constraints or Constraints(
            max_positions=self._request.trading_config.max_positions,
            max_leverage=self._request.trading_config.max_leverage,
        )

        # Compute equity based on market type:
        if self._request.exchange_config.market_type == MarketType.SPOT:
            # Spot: use available cash as equity
            equity = float(getattr(context.portfolio, "cash", 0.0) or 0.0)
        else:
            # Derivatives: use portfolio equity (cash + net exposure), or total_value if provided
            if getattr(context.portfolio, "total_value", None) is not None:
                equity = float(context.portfolio.total_value or 0.0)
            else:
                cash = float(getattr(context.portfolio, "cash", 0.0) or 0.0)
                net = float(getattr(context.portfolio, "net_exposure", 0.0) or 0.0)
                equity = cash + net

        # Market-type leverage policy: SPOT -> 1.0; Derivatives -> constraints
        if self._request.exchange_config.market_type == MarketType.SPOT:
            allowed_lev = 1.0
        else:
            allowed_lev = (
                float(constraints.max_leverage)
                if constraints.max_leverage is not None
                else 1.0
            )

        # Initialize projected gross exposure
        price_map = extract_price_map(context.market_snapshot or {})
        if getattr(context.portfolio, "gross_exposure", None) is not None:
            projected_gross = float(context.portfolio.gross_exposure or 0.0)
        else:
            projected_gross = 0.0
            for sym, snap in context.portfolio.positions.items():
                px = float(
                    price_map.get(sym) or getattr(snap, "mark_price", 0.0) or 0.0
                )
                projected_gross += abs(float(snap.quantity)) * px

        return equity, allowed_lev, constraints, projected_gross, price_map

    def _normalize_quantity(
        self,
        symbol: str,
        quantity: float,
        side: TradeSide,
        current_qty: float,
        constraints: Constraints,
        equity: float,
        allowed_lev: float,
        projected_gross: float,
        price_map: Dict[str, float],
    ) -> tuple:
        """Normalize quantity through all guardrails: filters, caps, and buying power.

        Returns:
            (final_qty, consumed_buying_power_delta)
        """
        qty = quantity

        # Step 1: per-order filters (step size, min notional, max order qty)
        logger.debug(f"_normalize_quantity Step 1: {symbol} qty={qty} before filters")
        qty = self._apply_quantity_filters(
            symbol,
            qty,
            float(constraints.quantity_step or 0.0),
            float(constraints.min_trade_qty or 0.0),
            constraints.max_order_qty,
            constraints.min_notional,
            price_map,
        )
        logger.debug(f"_normalize_quantity Step 1: {symbol} qty={qty} after filters")

        if qty <= self._quantity_precision:
            logger.warning(
                f"Post-filter quantity for {symbol} is {qty} <= precision {self._quantity_precision} -> returning 0"
            )
            return 0.0, 0.0

        # Step 2: notional/leverage cap (Phase 1 rules)
        price = price_map.get(symbol)
        if price is not None and price > 0:
            # cap_factor controls how aggressively we allow position sizing by notional.
            # Make it configurable via trading_config.cap_factor (strategy parameter).
            cap_factor = float(
                getattr(self._request.trading_config, "cap_factor", 1.5) or 1.5
            )
            if constraints.quantity_step and constraints.quantity_step > 0:
                cap_factor = max(cap_factor, 1.5)

            allowed_lev_cap = (
                allowed_lev if math.isfinite(allowed_lev) else float("inf")
            )
            max_abs_by_factor = (cap_factor * equity) / float(price)
            max_abs_by_lev = (allowed_lev_cap * equity) / float(price)
            max_abs_final = min(max_abs_by_factor, max_abs_by_lev)

            desired_final = current_qty + (qty if side is TradeSide.BUY else -qty)
            if math.isfinite(max_abs_final) and abs(desired_final) > max_abs_final:
                target_abs = max_abs_final
                new_qty = max(0.0, target_abs - abs(current_qty))
                if new_qty < qty:
                    logger.debug(
                        "Capping {} qty due to notional/leverage (price={}, cap_factor={}, old_qty={}, new_qty={})",
                        symbol,
                        price,
                        cap_factor,
                        qty,
                        new_qty,
                    )
                    qty = new_qty

        if qty <= self._quantity_precision:
            logger.debug(
                "Post-cap quantity for {} is {} <= precision {} -> skipping",
                symbol,
                qty,
                self._quantity_precision,
            )
            return 0.0, 0.0

        # Step 3: buying power clamp
        px = price_map.get(symbol)
        if px is None or px <= 0:
            logger.debug(
                "No price for {} to evaluate buying power; using full quantity",
                symbol,
            )
            final_qty = qty
        else:
            if self._request.exchange_config.market_type == MarketType.SPOT:
                # Spot: cash-only buying power
                avail_bp = max(0.0, equity)
            else:
                # Derivatives: margin-based buying power
                avail_bp = max(0.0, equity * allowed_lev - projected_gross)
            # When buying power is exhausted, we should still allow reductions/closures.
            # Set additional purchasable units to 0 but proceed with piecewise logic
            # so that de-risking trades are not blocked.
            a = abs(current_qty)
            # Conservative buffer for expected slippage: assume execution price may move
            # against us by `self._default_slippage_bps`. Use a higher effective price
            # when computing how many units fit into available buying power so that
            # planned increases don't accidentally exceed real-world costs.
            slip_bps = float(self._default_slippage_bps or 0.0)
            slip = slip_bps / 10000.0
            effective_px = float(px) * (1.0 + slip)
            ap_units = (avail_bp / effective_px) if avail_bp > 0 else 0.0

            # Piecewise: additional gross consumption must fit into available BP
            if side is TradeSide.BUY:
                if current_qty >= 0:
                    q_allowed = ap_units
                else:
                    if qty <= 2 * a:
                        q_allowed = qty
                    else:
                        q_allowed = 2 * a + ap_units
            else:  # SELL
                if current_qty <= 0:
                    q_allowed = ap_units
                else:
                    if qty <= 2 * a:
                        q_allowed = qty
                    else:
                        q_allowed = 2 * a + ap_units

            final_qty = max(0.0, min(qty, q_allowed))

        if final_qty <= self._quantity_precision:
            logger.debug(
                "Post-buying-power quantity for {} is {} <= precision {} -> skipping",
                symbol,
                final_qty,
                self._quantity_precision,
            )
            return 0.0, 0.0

        # Compute consumed buying power delta
        abs_before = abs(current_qty)
        abs_after = abs(
            current_qty + (final_qty if side is TradeSide.BUY else -final_qty)
        )
        delta_abs = abs_after - abs_before
        consumed_bp_delta = (
            delta_abs * price_map.get(symbol, 0.0) if delta_abs > 0 else 0.0
        )

        return final_qty, consumed_bp_delta

    def _normalize_plan(
        self,
        context: ComposeContext,
        plan: LlmPlanProposal,
    ) -> List[TradeInstruction]:
        instructions: List[TradeInstruction] = []

        # --- prepare state ---
        projected_positions: Dict[str, float] = {
            symbol: snapshot.quantity
            for symbol, snapshot in context.portfolio.positions.items()
        }

        def _count_active(pos_map: Dict[str, float]) -> int:
            return sum(1 for q in pos_map.values() if abs(q) > self._quantity_precision)

        active_positions = _count_active(projected_positions)

        # Initialize buying power context
        equity, allowed_lev, constraints, projected_gross, price_map = (
            self._init_buying_power_context(context)
        )

        max_positions = constraints.max_positions
        max_position_qty = constraints.max_position_qty

        # --- process each planned item ---
        for idx, item in enumerate(plan.items):
            symbol = item.instrument.symbol
            current_qty = projected_positions.get(symbol, 0.0)

            # determine the intended target quantity (clamped by max_position_qty)
            target_qty = self._resolve_target_quantity(
                item, current_qty, max_position_qty
            )
            # SPOT long-only: do not allow negative target quantities
            if (
                self._request.exchange_config.market_type == MarketType.SPOT
                and target_qty < 0
            ):
                target_qty = 0.0
            # Enforce: single-lot per symbol and no direct flip. If target flips side,
            # split into two sub-steps: first flat to 0, then open to target side.
            sub_targets: List[float] = []
            if current_qty * target_qty < 0:
                sub_targets = [0.0, float(target_qty)]
            else:
                sub_targets = [float(target_qty)]

            local_current = float(current_qty)
            for sub_i, sub_target in enumerate(sub_targets):
                delta = sub_target - local_current

                if abs(delta) <= self._quantity_precision:
                    continue

                is_new_position = (
                    abs(local_current) <= self._quantity_precision
                    and abs(sub_target) > self._quantity_precision
                )
                if (
                    is_new_position
                    and max_positions is not None
                    and active_positions >= int(max_positions)
                ):
                    logger.warning(
                        "Skipping symbol {} due to max_positions constraint (active={} max={})",
                        symbol,
                        active_positions,
                        max_positions,
                    )
                    continue

                side = TradeSide.BUY if delta > 0 else TradeSide.SELL
                # requested leverage (default 1.0), clamped to constraints
                requested_lev = (
                    float(item.leverage)
                    if getattr(item, "leverage", None) is not None
                    else 1.0
                )
                allowed_lev_item = (
                    float(constraints.max_leverage)
                    if constraints.max_leverage is not None
                    else requested_lev
                )
                if self._request.exchange_config.market_type == MarketType.SPOT:
                    # Spot: long-only, no leverage
                    final_leverage = 1.0
                else:
                    final_leverage = max(1.0, min(requested_lev, allowed_lev_item))
                quantity = abs(delta)

                # Normalize quantity through all guardrails
                logger.debug(f"Before normalize: {symbol} quantity={quantity}")
                quantity, consumed_bp = self._normalize_quantity(
                    symbol,
                    quantity,
                    side,
                    local_current,
                    constraints,
                    equity,
                    allowed_lev,
                    projected_gross,
                    price_map,
                )
                logger.debug(
                    f"After normalize: {symbol} quantity={quantity}, consumed_bp={consumed_bp}"
                )

                if quantity <= self._quantity_precision:
                    logger.warning(
                        f"SKIPPED: {symbol} quantity={quantity} <= precision={self._quantity_precision} after normalization"
                    )
                    continue

                # Update projected positions for subsequent guardrails
                signed_delta = quantity if side is TradeSide.BUY else -quantity
                projected_positions[symbol] = local_current + signed_delta
                projected_gross += consumed_bp

                # active positions accounting
                if is_new_position:
                    active_positions += 1
                if abs(projected_positions[symbol]) <= self._quantity_precision:
                    active_positions = max(active_positions - 1, 0)

                # Use a stable per-item sub-index to keep instruction ids unique
                instr = self._create_instruction(
                    context,
                    idx * 10 + sub_i,
                    item,
                    symbol,
                    side,
                    quantity,
                    final_leverage,
                    local_current,
                    sub_target,
                )
                instructions.append(instr)

                # advance local_current for the next sub-step
                local_current = projected_positions[symbol]

        return instructions

    def _create_instruction(
        self,
        context: ComposeContext,
        idx: int,
        item,
        symbol: str,
        side: TradeSide,
        quantity: float,
        final_leverage: float,
        current_qty: float,
        target_qty: float,
    ) -> TradeInstruction:
        """Create a normalized TradeInstruction with metadata."""
        final_target = current_qty + (quantity if side is TradeSide.BUY else -quantity)
        meta = {
            "requested_target_qty": target_qty,
            "current_qty": current_qty,
            "final_target_qty": final_target,
            "action": item.action.value,
        }
        if item.confidence is not None:
            meta["confidence"] = item.confidence
        if item.rationale:
            meta["rationale"] = item.rationale

        # For derivatives/perpetual markets, mark reduceOnly when instruction reduces absolute exposure to avoid accidental reverse opens
        try:
            if self._request.exchange_config.market_type != MarketType.SPOT:
                if abs(final_target) < abs(current_qty):
                    meta["reduceOnly"] = True
                    # Bybit uses a different param key
                    if (
                        self._request.exchange_config.exchange_id or ""
                    ).lower() == "bybit":
                        meta["reduce_only"] = True
        except Exception:
            # Ignore any exception; do not block instruction creation
            pass

        instruction = TradeInstruction(
            instruction_id=f"{context.compose_id}:{symbol}:{idx}",
            compose_id=context.compose_id,
            instrument=item.instrument,
            action=item.action,
            side=side,
            quantity=quantity,
            leverage=final_leverage,
            max_slippage_bps=self._default_slippage_bps,
            meta=meta,
        )
        logger.debug(
            "Created TradeInstruction {} for {} side={} qty={} lev={}",
            instruction.instruction_id,
            symbol,
            instruction.side,
            instruction.quantity,
            final_leverage,
        )
        return instruction

    def _resolve_target_quantity(
        self,
        item,
        current_qty: float,
        max_position_qty: Optional[float],
    ) -> float:
        # NOOP: keep current position
        if item.action == LlmDecisionAction.NOOP:
            return current_qty

        # Interpret target_qty as operation magnitude (not final position), normalized to positive
        mag = abs(float(item.target_qty))
        target = current_qty

        # Compute target position per open/close long/short action
        if item.action == LlmDecisionAction.OPEN_LONG:
            base = current_qty if current_qty > 0 else 0.0
            target = base + mag
        elif item.action == LlmDecisionAction.OPEN_SHORT:
            base = current_qty if current_qty < 0 else 0.0
            target = base - mag
        elif item.action == LlmDecisionAction.CLOSE_LONG:
            if current_qty > 0:
                target = max(current_qty - mag, 0.0)
            else:
                # No long position, keep unchanged
                target = current_qty
        elif item.action == LlmDecisionAction.CLOSE_SHORT:
            if current_qty < 0:
                target = min(current_qty + mag, 0.0)
            else:
                # No short position, keep unchanged
                target = current_qty
        else:
            # Fallback: treat unknown action as NOOP
            target = current_qty

        # Clamp by max_position_qty (symmetric)
        if max_position_qty is not None:
            max_abs = abs(float(max_position_qty))
            target = max(-max_abs, min(max_abs, target))

        return target

    def _apply_quantity_filters(
        self,
        symbol: str,
        quantity: float,
        quantity_step: float,
        min_trade_qty: float,
        max_order_qty: Optional[float],
        min_notional: Optional[float],
        market_snapshot: Dict[str, float],
    ) -> float:
        qty = quantity
        logger.debug(f"Filtering {symbol}: initial qty={qty}")

        if max_order_qty is not None:
            qty = min(qty, float(max_order_qty))
            logger.debug(f"After max_order_qty filter: qty={qty}")

        if quantity_step > 0:
            qty = math.floor(qty / quantity_step) * quantity_step
            logger.debug(f"After quantity_step filter: qty={qty}")

        if qty <= 0:
            logger.warning(f"FILTERED: {symbol} qty={qty} <= 0")
            return 0.0

        if qty < min_trade_qty:
            logger.warning(
                f"FILTERED: {symbol} qty={qty} < min_trade_qty={min_trade_qty}"
            )
            return 0.0

        if min_notional is not None:
            price = market_snapshot.get(symbol)
            if price is None:
                logger.warning(f"FILTERED: {symbol} no price in market_snapshot")
                return 0.0
            notional = qty * price
            if notional < float(min_notional):
                logger.warning(
                    f"FILTERED: {symbol} notional={notional:.4f} < min_notional={min_notional}"
                )
                return 0.0
            logger.debug(
                f"Passed min_notional check: notional={notional:.4f} >= {min_notional}"
            )

        logger.debug(f"Final qty for {symbol}: {qty}")
        return qty
