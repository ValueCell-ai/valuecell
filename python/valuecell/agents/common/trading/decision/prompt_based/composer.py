from __future__ import annotations

import json
from typing import Dict

from agno.agent import Agent as AgnoAgent
from loguru import logger

from valuecell.utils import env as env_utils
from valuecell.utils import model as model_utils

from ...models import (
    ComposeContext,
    ComposeResult,
    TradeDecisionAction,
    TradePlanProposal,
    UserRequest,
)
from ...utils import (
    extract_market_section,
    group_features,
    prune_none,
    send_discord_message,
)
from ..interfaces import BaseComposer
from .system_prompt import SYSTEM_PROMPT


class LlmComposer(BaseComposer):
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

    def _build_prompt_text(self) -> str:
        """Return a resolved prompt text by fusing custom_prompt and prompt_text.

        Fusion logic:
        - If custom_prompt exists, use it as base
        - If prompt_text also exists, append it after custom_prompt
        - If only prompt_text exists, use it
        - Fallback: simple generated mention of symbols
        """
        custom = self._request.trading_config.custom_prompt
        prompt = self._request.trading_config.prompt_text
        if custom and prompt:
            return f"{custom}\n\n{prompt}"
        elif custom:
            return custom
        elif prompt:
            return prompt
        symbols = ", ".join(self._request.trading_config.symbols)
        return f"Compose trading instructions for symbols: {symbols}."

    async def compose(self, context: ComposeContext) -> ComposeResult:
        prompt = self._build_llm_prompt(context)
        try:
            plan = await self._call_llm(prompt)
            if not plan.items:
                logger.info(
                    "LLM returned empty plan for compose_id={} with rationale={}",
                    context.compose_id,
                    plan.rationale,
                )
                return ComposeResult(instructions=[], rationale=plan.rationale)
        except Exception as exc:  # noqa: BLE001
            logger.error("LLM invocation failed: {}", exc)
            return ComposeResult(
                instructions=[], rationale=f"LLM invocation failed: {exc}"
            )

        # Optionally forward non-NOOP plan rationale to Discord webhook (env-driven)
        try:
            await self._send_plan_to_discord(plan)
        except Exception as exc:  # do not fail compose on notification errors
            logger.error("Failed sending plan to Discord: {}", exc)

        normalized = self._normalize_plan(context, plan)
        return ComposeResult(instructions=normalized, rationale=plan.rationale)

    # ------------------------------------------------------------------

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
        features = group_features(context.features)
        market = extract_market_section(features.get("market_snapshot", []))

        # Portfolio positions
        positions = [
            {
                "symbol": sym,
                "qty": float(snap.quantity),
                "unrealized_pnl": snap.unrealized_pnl,
                "entry_ts": snap.entry_ts,
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

        payload = prune_none(
            {
                "strategy_prompt": self._build_prompt_text(),
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
            "Always include a concise top-level 'rationale'. "
            "If you choose NOOP (items is empty), set 'rationale' to explain why: reference current prices and 'price.change_pct' vs thresholds, and any constraints or risk flags that led to NOOP. "
            "Output JSON with items array."
        )

        return f"{instructions}\n\nContext:\n{json.dumps(payload, ensure_ascii=False)}"

    async def _call_llm(self, prompt: str) -> TradePlanProposal:
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
            output_schema=TradePlanProposal,
            markdown=False,
            instructions=[SYSTEM_PROMPT],
            use_json_mode=model_utils.model_should_use_json_mode(model),
            debug_mode=env_utils.agent_debug_mode_enabled(),
        )
        response = await agent.arun(prompt)
        # Agent may return a raw object or a wrapper with `.content`.
        content = getattr(response, "content", None) or response
        logger.debug("Received LLM response {}", content)
        # If the agent already returned a validated model, return it directly
        if isinstance(content, TradePlanProposal):
            return content

        logger.error("LLM output failed validation: {}", content)
        return TradePlanProposal(
            items=[],
            rationale=(
                "LLM output failed validation. The model you chose "
                f"`{model_utils.describe_model(model)}` "
                "may be incompatible or returned unexpected output. "
                f"Raw output: {content}"
            ),
        )

    async def _send_plan_to_discord(self, plan: TradePlanProposal) -> None:
        """Send plan rationale to Discord when there are actionable items.

        Behavior:
        - If `plan.items` contains any item whose `action` is not `NOOP`, send
          a Markdown-formatted message containing the plan-level rationale and
          per-item brief rationales.
        - Reads webhook from `STRATEGY_AGENT_DISCORD_WEBHOOK_URL` (handled by
          `send_discord_message`). Does nothing if no actionable items exist.
        """
        actionable = [it for it in plan.items if it.action != TradeDecisionAction.NOOP]
        if not actionable:
            return

        strategy_name = self._request.trading_config.strategy_name
        parts = [f"## Strategy {strategy_name} — Actions Detected\n"]
        # top-level rationale
        top_r = plan.rationale
        if top_r:
            parts.append("**Overall rationale:**\n")
            parts.append(f"{top_r}\n")

        parts.append("**Items:**\n")
        for it in actionable:
            action = it.action.value
            instr_parts = []
            # instrument symbol if exists
            instr_parts.append(f"`{it.instrument.symbol}`")
            # target qty / magnitude
            instr_parts.append(f"qty={it.target_qty}")
            # item rationale
            item_r = it.rationale
            summary = " — ".join(instr_parts) if instr_parts else ""
            if item_r:
                parts.append(f"- **{action}** {summary} — Reasoning: {item_r}\n")
            else:
                parts.append(f"- **{action}** {summary}\n")

        message = "\n".join(parts)

        try:
            resp = await send_discord_message(message)
            logger.debug(
                "Sent plan to Discord, response len={}", len(resp) if resp else 0
            )
        except Exception as exc:
            logger.warning("Error sending plan to Discord, err={}", exc)
