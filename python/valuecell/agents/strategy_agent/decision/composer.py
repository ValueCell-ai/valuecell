from __future__ import annotations

import json
import math
from typing import Dict, List, Optional

from loguru import logger
from pydantic import ValidationError

from .interfaces import Composer
from ..models import (
    ComposeContext,
    LlmDecisionAction,
    LlmPlanProposal,
    TradeInstruction,
    TradeSide,
    UserRequest,
)


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
        self._base_constraints: Dict[str, float | int] = {
            "max_positions": request.trading_config.max_positions,
            "max_leverage": request.trading_config.max_leverage,
        }

    async def compose(self, context: ComposeContext) -> List[TradeInstruction]:
        prompt = self._build_llm_prompt(context)
        logger.debug(
            "Built LLM prompt for compose_id={}: {}",
            context.compose_id,
            prompt,
        )
        try:
            plan = await self._call_llm(prompt)
        except NotImplementedError:
            logger.warning("LLM call not implemented; returning no instructions")
            return []
        except ValidationError as exc:
            logger.error("LLM output failed validation: {}", exc)
            return []
        except Exception:  # noqa: BLE001
            logger.exception("LLM invocation failed")
            return []

        if not plan.items:
            logger.debug(
                "LLM returned empty plan for compose_id={}", context.compose_id
            )
            return []

        constraints = self._merge_constraints(context)
        return self._normalize_plan(context, plan, constraints)

    # ------------------------------------------------------------------
    # Prompt + LLM helpers

    def _build_llm_prompt(self, context: ComposeContext) -> str:
        """Serialize compose context into a textual prompt for the LLM."""

        payload = {
            "strategy_prompt": context.prompt_text,
            "compose_id": context.compose_id,
            "timestamp": context.ts,
            "portfolio": context.portfolio.model_dump(mode="json"),
            "market_snapshot": context.market_snapshot or {},
            "digest": context.digest.model_dump(mode="json"),
            "features": [vector.model_dump(mode="json") for vector in context.features],
            "constraints": context.constraints or {},
        }

        instructions = (
            "You are a trading strategy planner. Analyze the JSON context and "
            "produce a structured plan that aligns with the LlmPlanProposal "
            "schema (items array with instrument, action, target_qty, rationale, "
            "confidence). Focus on risk-aware, executable decisions."
        )

        return f"{instructions}\n\nContext:\n{json.dumps(payload, ensure_ascii=False, indent=2)}"

    async def _call_llm(
        self, prompt: str
    ) -> LlmPlanProposal:  # pragma: no cover - implemented async
        """Invoke an LLM asynchronously and parse the response into LlmPlanProposal.

        This implementation follows the parser_agent pattern: it creates a model
        via `create_model_with_provider`, wraps it in an `agno.agent.Agent` with
        `output_schema=LlmPlanProposal`, and awaits `agent.arun(prompt)`. The
        agent's `response.content` is returned (or validated) as a
        `LlmPlanProposal`.
        """

        from valuecell.utils.model import create_model_with_provider
        from agno.agent import Agent as AgnoAgent

        cfg = self._request.llm_model_config
        model = create_model_with_provider(
            provider=cfg.provider,
            model_id=cfg.model_id,
            api_key=cfg.api_key,
        )

        # Wrap model in an Agent (consistent with parser_agent usage)
        agent = AgnoAgent(model=model, output_schema=LlmPlanProposal, markdown=False)
        response = await agent.arun(prompt)
        content = getattr(response, "content", None) or response
        logger.debug("Received LLM response {}", content)
        return content

    # ------------------------------------------------------------------
    # Normalization / guardrails helpers

    def _merge_constraints(self, context: ComposeContext) -> Dict[str, float | int]:
        merged: Dict[str, float | int] = dict(self._base_constraints)
        if context.constraints:
            merged.update(context.constraints)
        return merged

    def _normalize_plan(
        self,
        context: ComposeContext,
        plan: LlmPlanProposal,
        constraints: Dict[str, float | int],
    ) -> List[TradeInstruction]:
        instructions: List[TradeInstruction] = []

        projected_positions: Dict[str, float] = {
            symbol: snapshot.quantity
            for symbol, snapshot in context.portfolio.positions.items()
        }
        active_positions = sum(
            1
            for qty in projected_positions.values()
            if abs(qty) > self._quantity_precision
        )

        max_positions = constraints.get("max_positions")
        quantity_step = float(constraints.get("quantity_step", 0) or 0.0)
        min_trade_qty = float(constraints.get("min_trade_qty", 0) or 0.0)
        max_order_qty = constraints.get("max_order_qty")
        max_position_qty = constraints.get("max_position_qty")
        min_notional = constraints.get("min_notional")

        for idx, item in enumerate(plan.items):
            symbol = item.instrument.symbol
            current_qty = projected_positions.get(symbol, 0.0)

            target_qty = self._resolve_target_quantity(
                item, current_qty, max_position_qty
            )
            delta = target_qty - current_qty

            if abs(delta) <= self._quantity_precision:
                logger.debug(
                    "Skipping symbol {} because delta {} <= quantity_precision {}",
                    symbol,
                    delta,
                    self._quantity_precision,
                )
                continue

            is_new_position = (
                abs(current_qty) <= self._quantity_precision
                and abs(target_qty) > self._quantity_precision
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
            quantity = abs(delta)

            quantity = self._apply_quantity_filters(
                symbol,
                quantity,
                quantity_step,
                min_trade_qty,
                max_order_qty,
                min_notional,
                context.market_snapshot or {},
            )

            if quantity <= self._quantity_precision:
                logger.debug(
                    "Post-filter quantity for {} is {} <= precision {} -> skipping",
                    symbol,
                    quantity,
                    self._quantity_precision,
                )
                continue

            # Update projected positions for subsequent guardrails
            signed_delta = quantity if side is TradeSide.BUY else -quantity
            projected_positions[symbol] = current_qty + signed_delta

            if is_new_position:
                active_positions += 1
            if abs(projected_positions[symbol]) <= self._quantity_precision:
                active_positions = max(active_positions - 1, 0)

            final_target = projected_positions[symbol]
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

            instruction = TradeInstruction(
                instruction_id=f"{context.compose_id}:{symbol}:{idx}",
                compose_id=context.compose_id,
                instrument=item.instrument,
                side=side,
                quantity=quantity,
                price_mode="market",
                limit_price=None,
                max_slippage_bps=self._default_slippage_bps,
                meta=meta,
            )
            instructions.append(instruction)
            logger.debug(
                "Created TradeInstruction {} for {} side={} qty={}",
                instruction.instruction_id,
                symbol,
                instruction.side,
                instruction.quantity,
            )

        return instructions

    def _resolve_target_quantity(
        self,
        item,
        current_qty: float,
        max_position_qty: Optional[float],
    ) -> float:
        if item.action == LlmDecisionAction.NOOP:
            return current_qty
        if item.action == LlmDecisionAction.FLAT:
            target = 0.0
        else:
            target = float(item.target_qty)

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

        if max_order_qty is not None:
            qty = min(qty, float(max_order_qty))

        if quantity_step > 0:
            qty = math.floor(qty / quantity_step) * quantity_step

        if qty <= 0:
            return 0.0

        if qty < min_trade_qty:
            return 0.0

        if min_notional is not None:
            price = market_snapshot.get(symbol)
            if price is None:
                return 0.0
            if qty * price < float(min_notional):
                return 0.0

        return qty
