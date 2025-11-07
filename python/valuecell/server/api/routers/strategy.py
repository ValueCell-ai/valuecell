"""
Strategy API router for handling strategy-related endpoints.
"""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from valuecell.server.api.schemas.base import SuccessResponse
from valuecell.server.api.schemas.strategy import (
    StrategyCurveResponse,
    StrategyDetailResponse,
    StrategyHoldingFlatItem,
    StrategyHoldingFlatResponse,
    StrategyListData,
    StrategyListResponse,
    StrategyStatusSuccessResponse,
    StrategyStatusUpdateResponse,
    StrategySummaryData,
)
from valuecell.server.db import get_db
from valuecell.server.db.models.strategy import Strategy
from valuecell.server.db.repositories import get_strategy_repository
from valuecell.server.services.strategy_service import StrategyService


def create_strategy_router() -> APIRouter:
    """Create and configure the strategy router."""

    router = APIRouter(
        prefix="/strategies",
        tags=["strategies"],
        responses={404: {"description": "Not found"}},
    )

    @router.get(
        "/",
        response_model=StrategyListResponse,
        summary="Get all strategies",
        description="Get a list of strategies created via StrategyAgent with optional filters",
    )
    async def get_strategies(
        user_id: Optional[str] = Query(None, description="Filter by user ID"),
        status: Optional[str] = Query(None, description="Filter by status"),
        name_filter: Optional[str] = Query(
            None, description="Filter by strategy name or ID (supports fuzzy matching)"
        ),
        db: Session = Depends(get_db),
    ) -> StrategyListResponse:
        """
        Get all strategies list.

        - **user_id**: Filter by owner user ID
        - **status**: Filter by strategy status (running, stopped)
        - **name_filter**: Filter by strategy name or ID with fuzzy matching

        Returns a response containing the strategy list and statistics.
        """
        try:
            query = db.query(Strategy)

            filters = []
            if user_id:
                filters.append(Strategy.user_id == user_id)
            if status:
                filters.append(Strategy.status == status)
            if name_filter:
                filters.append(
                    or_(
                        Strategy.name.ilike(f"%{name_filter}%"),
                        Strategy.strategy_id.ilike(f"%{name_filter}%"),
                    )
                )

            if filters:
                query = query.filter(and_(*filters))

            strategies = query.order_by(Strategy.created_at.desc()).all()

            def map_status(raw: Optional[str]) -> str:
                return "running" if (raw or "").lower() == "running" else "stopped"

            def normalize_trading_mode(meta: dict, cfg: dict) -> Optional[str]:
                v = meta.get("trading_mode") or cfg.get("trading_mode")
                if not v:
                    return None
                v = str(v).lower()
                if v in ("live", "real", "realtime"):
                    return "live"
                if v in ("virtual", "paper", "sim"):
                    return "virtual"
                return None

            def to_optional_float(value) -> Optional[float]:
                if value is None:
                    return None
                try:
                    return float(value)
                except Exception:
                    return None

            strategy_data_list = []
            for s in strategies:
                meta = s.strategy_metadata or {}
                cfg = s.config or {}
                item = StrategySummaryData(
                    strategy_id=s.strategy_id,
                    strategy_name=s.name,
                    status=map_status(s.status),
                    trading_mode=normalize_trading_mode(meta, cfg),
                    unrealized_pnl=to_optional_float(meta.get("unrealized_pnl", 0.0)),
                    unrealized_pnl_pct=to_optional_float(
                        meta.get("unrealized_pnl_pct", 0.0)
                    ),
                    created_at=s.created_at,
                    exchange_id=(meta.get("exchange_id") or cfg.get("exchange_id")),
                    model_id=(
                        meta.get("model_id")
                        or meta.get("llm_model_id")
                        or cfg.get("model_id")
                        or cfg.get("llm_model_id")
                    ),
                )
                strategy_data_list.append(item)

            running_count = sum(1 for s in strategy_data_list if s.status == "running")

            list_data = StrategyListData(
                strategies=strategy_data_list,
                total=len(strategy_data_list),
                running_count=running_count,
            )

            return SuccessResponse.create(
                data=list_data,
                msg=f"Successfully retrieved {list_data.total} strategies",
            )
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to retrieve strategy list: {str(e)}"
            )

    @router.get(
        "/holding",
        response_model=StrategyHoldingFlatResponse,
        summary="Get current holdings for a strategy",
        description="Return the latest portfolio holdings of the specified strategy",
    )
    async def get_strategy_holding(
        id: str = Query(..., description="Strategy ID"),
    ) -> StrategyHoldingFlatResponse:
        try:
            data = await StrategyService.get_strategy_holding(id)
            if not data:
                return SuccessResponse.create(
                    data=[],
                    msg="No holdings found for strategy",
                )

            items: List[StrategyHoldingFlatItem] = []
            for p in data.positions or []:
                try:
                    t = p.trade_type or ("LONG" if p.quantity >= 0 else "SHORT")
                    qty = abs(p.quantity)
                    items.append(
                        StrategyHoldingFlatItem(
                            symbol=p.symbol,
                            type=t,
                            leverage=p.leverage,
                            entry_price=p.avg_price,
                            quantity=qty,
                            unrealized_pnl=p.unrealized_pnl,
                            unrealized_pnl_pct=p.unrealized_pnl_pct,
                        )
                    )
                except Exception:
                    continue

            return SuccessResponse.create(
                data=items,
                msg="Successfully retrieved strategy holdings",
            )
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to retrieve holdings: {str(e)}"
            )

    @router.get(
        "/detail",
        response_model=StrategyDetailResponse,
        summary="Get strategy trade details",
        description="Return a list of trade details generated from the latest portfolio snapshot",
    )
    async def get_strategy_detail(
        id: str = Query(..., description="Strategy ID"),
    ) -> StrategyDetailResponse:
        try:
            data = await StrategyService.get_strategy_detail(id)
            if not data:
                # Return empty list with success instead of 404
                return SuccessResponse.create(
                    data=[],
                    msg="No details found for strategy",
                )
            return SuccessResponse.create(
                data=data,
                msg="Successfully retrieved strategy details",
            )
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to retrieve details: {str(e)}"
            )

    @router.get(
        "/holding_price_curve",
        response_model=StrategyCurveResponse,
        summary="Get strategy holding price curve (single or all)",
        description="If id is provided, return single strategy curve. If omitted, return combined curves for all strategies with nulls for missing data.",
    )
    async def get_strategy_holding_price_curve(
        id: Optional[str] = Query(None, description="Strategy ID (optional)"),
        limit: Optional[int] = Query(
            None,
            description="Limit number of strategies when id omitted (most recent first)",
            ge=1,
            le=200,
        ),
        db: Session = Depends(get_db),
    ) -> StrategyCurveResponse:
        try:
            repo = get_strategy_repository(db_session=db)

            # Case 1: Single strategy
            if id:
                strategy = repo.get_strategy_by_strategy_id(id)
                if not strategy:
                    raise HTTPException(status_code=404, detail="Strategy not found")

                strategy_name = strategy.name or f"Strategy-{id.split('-')[-1][:8]}"
                created_at = strategy.created_at or datetime.utcnow()

                data = [["Time", strategy_name]]

                # Build series from aggregated portfolio snapshots (StrategyPortfolioView).
                snapshots = repo.get_portfolio_snapshots(id)
                if snapshots:
                    # repository returns desc order; present oldest->newest
                    for s in reversed(snapshots):
                        t = s.snapshot_ts or created_at
                        time_str = t.strftime("%Y-%m-%d %H:%M:%S")
                        try:
                            v = (
                                float(s.total_value)
                                if s.total_value is not None
                                else None
                            )
                        except Exception:
                            v = None
                        data.append([time_str, v])
                else:
                    return SuccessResponse.create(
                        data=[],
                        msg="No holding price curve found for strategy",
                    )

                return SuccessResponse.create(
                    data=data,
                    msg="Fetched holding price curve successfully",
                )

            # Case 2: Combined curves for all strategies
            query = db.query(Strategy).order_by(Strategy.created_at.desc())
            if limit:
                query = query.limit(limit)
            strategies = query.all()

            # Build series per strategy: {strategy_id: {time_str: value}}
            series_map = {}
            strategy_order = []  # Keep consistent header order
            name_map = {}
            created_times = []

            for s in strategies:
                sid = s.strategy_id
                sname = s.name or f"Strategy-{sid.split('-')[-1][:8]}"
                strategy_order.append(sid)
                name_map[sid] = sname
                created_at = s.created_at or datetime.utcnow()
                created_times.append(created_at)

                # Build per-strategy entries from aggregated portfolio snapshots
                entries = {}
                snapshots = repo.get_portfolio_snapshots(sid)
                if snapshots:
                    for s in reversed(snapshots):
                        t = s.snapshot_ts or created_at
                        time_str = t.strftime("%Y-%m-%d %H:%M:%S")
                        try:
                            v = (
                                float(s.total_value)
                                if s.total_value is not None
                                else None
                            )
                        except Exception:
                            v = None
                        entries[time_str] = v
                series_map[sid] = entries

            # Union of all timestamps
            all_times = set()
            for entries in series_map.values():
                for ts in entries.keys():
                    all_times.add(ts)

            data = [["Time"] + [name_map[sid] for sid in strategy_order]]

            if all_times:
                for time_str in sorted(all_times):
                    row = [time_str]
                    for sid in strategy_order:
                        v = series_map.get(sid, {}).get(time_str)
                        row.append(v if v is not None else None)
                    data.append(row)
            else:
                # No data across all strategies: return empty array
                return SuccessResponse.create(
                    data=[],
                    msg="No holding price curves found",
                )

            return SuccessResponse.create(
                data=data,
                msg="Fetched merged holding price curves successfully",
            )
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to retrieve holding price curve: {str(e)}",
            )

    @router.post(
        "/stop",
        response_model=StrategyStatusSuccessResponse,
        summary="Stop a strategy",
        description="Set the strategy status to 'stopped' by ID (via query param 'id')",
    )
    async def stop_strategy(
        id: str = Query(..., description="Strategy ID"),
        db: Session = Depends(get_db),
    ) -> StrategyStatusSuccessResponse:
        try:
            repo = get_strategy_repository(db_session=db)
            strategy = repo.get_strategy_by_strategy_id(id)
            if not strategy:
                raise HTTPException(status_code=404, detail="Strategy not found")

            # Update status to 'stopped' (idempotent)
            repo.upsert_strategy(strategy_id=id, status="stopped")

            response_data = StrategyStatusUpdateResponse(
                strategy_id=id,
                status="stopped",
                message=f"Strategy '{id}' has been stopped",
            )

            return SuccessResponse.create(
                data=response_data,
                msg=f"Successfully stopped strategy '{id}'",
            )
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to stop strategy: {str(e)}",
            )

    return router
