"""Trading-related API routes: positions, balances, etc."""

from __future__ import annotations

import os
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query

from valuecell.agents.auto_trading_agent.exchanges.okx_exchange import (
    OKXExchange,
)
from valuecell.server.api.schemas.base import SuccessResponse
from valuecell.server.api.schemas.trading import (
    OpenPositionsData,
    OpenPositionsResponse,
    PositionItem,
)


def create_trading_router() -> APIRouter:
    """Create trading router with endpoints for positions and balances."""

    router = APIRouter(prefix="/trading", tags=["Trading"])

    @router.get(
        "/positions",
        response_model=OpenPositionsResponse,
        summary="Get open positions",
        description="Fetch current open positions and unrealized P&L from the configured exchange",
    )
    async def get_open_positions(
        exchange: Optional[str] = Query(None, description="Exchange name"),
        network: Optional[str] = Query(
            None, description="Network/environment, e.g. testnet|mainnet|paper"
        ),
    ) -> OpenPositionsResponse:
        try:
            # Resolve target exchange: query > env > default
            resolved_exchange = (
                exchange or os.getenv("AUTO_TRADING_EXCHANGE", "paper")
            ).lower()

            items: List[PositionItem] = []

            if resolved_exchange == "okx":
                api_key = os.getenv("OKX_API_KEY", "").strip()
                api_secret = os.getenv("OKX_API_SECRET", "").strip()
                passphrase = os.getenv("OKX_API_PASSPHRASE", "").strip()
                (os.getenv("OKX_ALLOW_LIVE_TRADING", "false").lower() == "true")
                resolved_network = (
                    network or os.getenv("OKX_NETWORK", "paper")
                ).lower()

                okx = OKXExchange(
                    api_key=api_key,
                    api_secret=api_secret,
                    passphrase=passphrase,
                    network=resolved_network,
                    # default to contracts; margin_mode/inst_type internal defaults
                )
                await okx.connect()
                raw_positions: Dict[
                    str, Dict[str, float]
                ] = await okx.get_open_positions()

                for symbol, pos in raw_positions.items():
                    qty = float(pos.get("quantity", 0.0) or 0.0)
                    entry_px = float(pos.get("entry_price", 0.0) or 0.0)
                    try:
                        current_px = await okx.get_current_price(symbol)
                    except Exception:
                        current_px = None
                    unreal_pnl = float(pos.get("unrealized_pnl", 0.0) or 0.0)
                    notional = abs(qty) * entry_px if entry_px else 0.0
                    pnl_pct = (unreal_pnl / notional * 100.0) if notional else None
                    items.append(
                        PositionItem(
                            symbol=symbol,
                            quantity=qty,
                            entry_price=entry_px,
                            current_price=current_px,
                            unrealized_pnl=unreal_pnl,
                            pnl_percent=pnl_pct,
                        )
                    )
                data = OpenPositionsData(
                    exchange="okx", network=resolved_network, positions=items
                )
                return SuccessResponse.create(data=data, msg="Retrieved open positions")

            # Paper / unsupported exchange: return empty set gracefully
            resolved_network = network or os.getenv("OKX_NETWORK") or "paper"
            data = OpenPositionsData(
                exchange=resolved_exchange, network=resolved_network, positions=[]
            )
            return SuccessResponse.create(
                data=data, msg="No positions for selected exchange"
            )

        except HTTPException:
            raise
        except Exception as e:  # pragma: no cover - generic server error wrapper
            raise HTTPException(
                status_code=500, detail=f"Failed to fetch positions: {str(e)}"
            )

    return router
