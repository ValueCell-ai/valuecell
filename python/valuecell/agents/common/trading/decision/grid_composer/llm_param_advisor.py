from __future__ import annotations

import json
from typing import Optional

from agno.agent import Agent as AgnoAgent
from loguru import logger

from valuecell.agents.common.trading.constants import (
    FEATURE_GROUP_BY_KEY,
    FEATURE_GROUP_BY_MARKET_SNAPSHOT,
)
from valuecell.utils import model as model_utils

from ...models import ComposeContext, GridParamAdvice, UserRequest

SYSTEM_PROMPT = (
    "You are a grid parameter advisor. "
    "Given the current market snapshot metrics and runtime settings, propose grid parameters dynamically. "
    "Use higher sensitivity (smaller step_pct, larger max_steps) for high-liquidity, high-volatility pairs; lower sensitivity otherwise. "
    "Respect typical ranges: step_pct 0.0005~0.01, max_steps 1~5, base_fraction 0.03~0.10. "
    "Optionally include grid zone bounds (grid_lower_pct, grid_upper_pct) and grid_count when appropriate. "
    "Calibrate base_fraction and optional grid_count using portfolio context: equity, buying_power, free_cash, and constraints.max_leverage. "
    "Align parameter sensitivity with available capital and risk limits (cap_factor). Prefer smaller base_fraction and fewer steps when capital is tight. "
    "Output pure JSON with fields: grid_step_pct, grid_max_steps, grid_base_fraction, and optionally grid_lower_pct, grid_upper_pct, grid_count, advisor_rationale. "
    "advisor_rationale should briefly explain your thinking and operational basis (e.g., volatility, liquidity, funding, OI, buying_power) for parameter selection."
)


class GridParamAdvisor:
    def __init__(
        self, request: UserRequest, prev_params: Optional[dict] = None
    ) -> None:
        self._request = request
        # Previous applied grid params from composer (optional), used to anchor suggestions
        self._prev_params = prev_params or {}

    async def advise(self, context: ComposeContext) -> Optional[GridParamAdvice]:
        cfg = self._request.llm_model_config
        try:
            model = model_utils.create_model_with_provider(
                provider=cfg.provider,
                model_id=cfg.model_id,
                api_key=cfg.api_key,
            )

            # Extract a compact per-symbol snapshot of key metrics
            keys = (
                "price.last",
                "price.change_pct",
                "price.volume",
                "open_interest",
                "funding.rate",
            )
            metrics: dict[str, dict[str, float]] = {}
            for fv in context.features or []:
                try:
                    symbol = str(getattr(fv.instrument, "symbol", ""))
                    meta = fv.meta or {}
                    if (
                        meta.get(FEATURE_GROUP_BY_KEY)
                        != FEATURE_GROUP_BY_MARKET_SNAPSHOT
                    ):
                        continue
                    if symbol not in (self._request.trading_config.symbols or []):
                        continue
                    snap = metrics.setdefault(symbol, {})
                    for k in keys:
                        val = fv.values.get(k)
                        if val is not None:
                            try:
                                snap[k] = float(val)  # type: ignore
                            except Exception:
                                pass
                except Exception:
                    continue

            payload = {
                "market_type": self._request.exchange_config.market_type,
                "decide_interval": self._request.trading_config.decide_interval,
                "symbols": self._request.trading_config.symbols,
                "snapshot_metrics": metrics,
            }

            # Include previous applied parameters to promote continuity and gradual changes
            try:
                prev = {}
                for k in (
                    "grid_step_pct",
                    "grid_max_steps",
                    "grid_base_fraction",
                    "grid_lower_pct",
                    "grid_upper_pct",
                    "grid_count",
                ):
                    v = self._prev_params.get(k)
                    if v is not None:
                        prev[k] = float(v) if isinstance(v, (int, float)) else v
                if prev:
                    payload["previous_params"] = prev
            except Exception:
                # Ignore if previous params cannot be assembled
                pass

            # Include portfolio/buying power context so the model scales params realistically
            try:
                pv = context.portfolio
                # Derive equity with safe fallbacks
                equity: Optional[float] = None
                try:
                    if getattr(pv, "total_value", None) is not None:
                        equity = float(pv.total_value)  # type: ignore
                    else:
                        bal = float(pv.account_balance)  # type: ignore
                        upnl = float(getattr(pv, "total_unrealized_pnl", 0.0) or 0.0)  # type: ignore
                        equity = bal + upnl
                except Exception:
                    equity = None

                constraints = getattr(pv, "constraints", None)
                max_lev = None
                try:
                    max_lev = (
                        float(getattr(constraints, "max_leverage", None))
                        if constraints is not None
                        and getattr(constraints, "max_leverage", None) is not None
                        else float(self._request.trading_config.max_leverage)
                    )
                except Exception:
                    max_lev = None

                portfolio_ctx = {
                    "equity": equity,
                    "buying_power": getattr(pv, "buying_power", None),
                    "free_cash": getattr(pv, "free_cash", None),
                    "constraints": {
                        "max_leverage": max_lev,
                        "quantity_step": getattr(constraints, "quantity_step", None)
                        if constraints
                        else None,
                        "min_trade_qty": getattr(constraints, "min_trade_qty", None)
                        if constraints
                        else None,
                        "max_order_qty": getattr(constraints, "max_order_qty", None)
                        if constraints
                        else None,
                        "max_position_qty": getattr(
                            constraints, "max_position_qty", None
                        )
                        if constraints
                        else None,
                    },
                    "cap_factor": float(self._request.trading_config.cap_factor),
                }
                payload["portfolio"] = portfolio_ctx
            except Exception:
                # Portfolio context is optional; proceed without if assembly fails
                pass

            instructions = (
                "Return JSON only. Include advisor_rationale summarizing your thought process and operational basis. "
                "Keep within ranges; favor smaller step_pct for high-liquidity and high-volatility pairs. "
                "If funding.rate is high or open_interest large, prefer tighter grid and smaller base_fraction; otherwise be conservative. "
                "Consider portfolio.equity, buying_power, free_cash, constraints.max_leverage, and cap_factor to scale base_fraction and optional grid_count. "
                "Avoid suggesting parameter combinations that imply excessive total size under available buying_power. "
                "Anchor suggestions to previous_params when provided; prefer gradual adjustments (e.g., limit grid_count delta within ±2 and keep step_pct changes small) unless metrics indicate a clear regime shift."
            )
            prompt = (
                f"{instructions}\n\nContext:\n{json.dumps(payload, ensure_ascii=False)}"
            )

            agent = AgnoAgent(
                model=model,
                output_schema=GridParamAdvice,
                markdown=False,
                instructions=[SYSTEM_PROMPT],
                use_json_mode=model_utils.model_should_use_json_mode(model),
            )

            response = await agent.arun(prompt)
            content = getattr(response, "content", None) or response
            if isinstance(content, GridParamAdvice):
                logger.info(
                    "LLM grid advice: step_pct={}, max_steps={}, base_fraction={}, lower={}, upper={}, count={}, rationale={}",
                    content.grid_step_pct,
                    content.grid_max_steps,
                    content.grid_base_fraction,
                    content.grid_lower_pct,
                    content.grid_upper_pct,
                    content.grid_count,
                    getattr(content, "advisor_rationale", None),
                )
                return content
            logger.warning("LLM advice failed validation: {}", content)
        except Exception as exc:
            logger.error("LLM param advisor error: {}", exc)
        return None
