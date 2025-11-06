from datetime import datetime, timezone
from typing import List, Optional

from valuecell.agents.strategy_agent.models import ComponentType, PortfolioView
from valuecell.core.types import (
    CommonResponseEvent,
    ComponentGeneratorResponseDataPayload,
)
from valuecell.server.api.schemas.strategy import (
    PositionHoldingItem,
    StrategyDetailItem,
    StrategyHoldingData,
)
from valuecell.server.services.conversation_service import get_conversation_service


class StrategyService:
    @staticmethod
    async def get_strategy_holding(strategy_id: str) -> Optional[StrategyHoldingData]:
        cs = get_conversation_service()
        items = await cs.item_store.get_items(
            conversation_id=None,
            role=None,
            event=CommonResponseEvent.COMPONENT_GENERATOR.value,
            component_type=ComponentType.UPDATE_PORTFOLIO.value,
            limit=1000,
            order="desc",
        )

        for item in items:
            try:
                payload = ComponentGeneratorResponseDataPayload.model_validate_json(
                    item.payload
                )
                content = payload.content
                if isinstance(content, str):
                    view = PortfolioView.model_validate_json(content)
                else:
                    view = PortfolioView.model_validate(content)
            except Exception:
                continue

            if view.strategy_id != strategy_id:
                continue

            positions: List[PositionHoldingItem] = []
            for symbol, pos in (view.positions or {}).items():
                try:
                    instrument = getattr(pos, "instrument", None)
                    exchange_id = (
                        getattr(instrument, "exchange_id", None) if instrument else None
                    )
                    positions.append(
                        PositionHoldingItem(
                            symbol=getattr(instrument, "symbol", symbol)
                            if instrument
                            else symbol,
                            exchange_id=exchange_id,
                            quantity=pos.quantity,
                            avg_price=pos.avg_price,
                            mark_price=pos.mark_price,
                            unrealized_pnl=pos.unrealized_pnl,
                            unrealized_pnl_pct=pos.unrealized_pnl_pct,
                            notional=pos.notional,
                            leverage=pos.leverage,
                            entry_ts=pos.entry_ts,
                            trade_type=(
                                pos.trade_type.value
                                if getattr(pos, "trade_type", None)
                                else None
                            ),
                        )
                    )
                except Exception:
                    continue

            return StrategyHoldingData(
                strategy_id=view.strategy_id,
                ts=view.ts,
                cash=view.cash,
                positions=positions,
                total_value=view.total_value,
                total_unrealized_pnl=view.total_unrealized_pnl,
                available_cash=view.available_cash,
            )

        return None

    @staticmethod
    async def get_strategy_detail(
        strategy_id: str,
    ) -> Optional[List[StrategyDetailItem]]:
        cs = get_conversation_service()
        items = await cs.item_store.get_items(
            conversation_id=None,
            role=None,
            event=CommonResponseEvent.COMPONENT_GENERATOR.value,
            component_type=ComponentType.UPDATE_PORTFOLIO.value,
            limit=1000,
            order="desc",
        )

        for item in items:
            try:
                payload = ComponentGeneratorResponseDataPayload.model_validate_json(
                    item.payload
                )
                content = payload.content
                if isinstance(content, str):
                    view = PortfolioView.model_validate_json(content)
                else:
                    view = PortfolioView.model_validate(content)
            except Exception:
                continue

            if view.strategy_id != strategy_id:
                continue

            details: List[StrategyDetailItem] = []
            for symbol, pos in (view.positions or {}).items():
                try:
                    instrument = getattr(pos, "instrument", None)
                    sym = (
                        getattr(instrument, "symbol", symbol) if instrument else symbol
                    )
                    t = (
                        pos.trade_type.value
                        if getattr(pos, "trade_type", None)
                        else ("LONG" if pos.quantity >= 0 else "SHORT")
                    )
                    side = "BUY" if t == "LONG" else "SELL"
                    qty = abs(pos.quantity)
                    entry_ts = pos.entry_ts or view.ts
                    holding_ms = (
                        int((view.ts or entry_ts) - entry_ts) if entry_ts else None
                    )
                    # UTC time string for entry
                    time_str = None
                    if entry_ts:
                        dt = datetime.fromtimestamp(entry_ts / 1000.0, tz=timezone.utc)
                        time_str = dt.isoformat()

                    trade_id = f"{view.strategy_id}:{sym}:{entry_ts}"

                    details.append(
                        StrategyDetailItem(
                            trade_id=trade_id,
                            symbol=sym,
                            type=t,
                            side=side,
                            leverage=pos.leverage,
                            quantity=qty,
                            unrealized_pnl=pos.unrealized_pnl,
                            entry_price=pos.avg_price,
                            exit_price=None,
                            holding_ms=holding_ms,
                            time=time_str,
                            note="",
                        )
                    )
                except Exception:
                    continue

            return details

        return None
