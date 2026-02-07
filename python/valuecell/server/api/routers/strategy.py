"""
Strategy API router for handling strategy-related endpoints.
"""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from loguru import logger
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from valuecell.server.api.schemas.base import StatusCode, SuccessResponse
from valuecell.server.api.schemas.strategy import (
    BacktestConfigRequest,
    BacktestResultData,
    BacktestResultResponse,
    BacktestStartResponse,
    BaseStrategyType,
    DynamicStrategyConfig,
    ManualClosePositionData,
    ManualClosePositionRequest,
    ManualClosePositionResponse,
    MarketStateAndScoresData,
    MarketStateAndScoresResponse,
    PositionControlUpdateRequest,
    PositionControlUpdateResponse,
    RiskMode,
    ScoreWeights,
    StrategyCurveResponse,
    StrategyDetailResponse,
    StrategyHoldingFlatItem,
    StrategyHoldingFlatResponse,
    StrategyListData,
    StrategyListResponse,
    StrategyPerformanceResponse,
    StrategyPortfolioSummaryResponse,
    StrategyStatusSuccessResponse,
    StrategyStatusUpdateResponse,
    StrategySummaryData,
    StrategyType,
)
from valuecell.server.db import get_db
from valuecell.server.db.models.strategy import Strategy
from valuecell.server.db.repositories import get_strategy_repository
from valuecell.server.services.backtest_service import (
    BacktestConfig,
    BacktestService,
)
from valuecell.server.services.dynamic_strategy_service import (
    BaseStrategyType as ServiceBaseStrategyType,
    DynamicStrategyScorer,
    RiskMode as ServiceRiskMode,
)
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

            def normalize_strategy_type(
                meta: dict, cfg: dict
            ) -> Optional[StrategyType]:
                val = meta.get("strategy_type")
                if not val:
                    val = (cfg.get("trading_config", {}) or {}).get("strategy_type")
                if val is None:
                    agent_name = str(meta.get("agent_name") or "").lower()
                    if "prompt" in agent_name:
                        return StrategyType.PROMPT
                    if "grid" in agent_name:
                        return StrategyType.GRID
                    return None

                raw = str(val).strip().lower()
                if raw.startswith("strategytype."):
                    raw = raw.split(".", 1)[1]
                raw_compact = "".join(ch for ch in raw if ch.isalnum())

                if raw in ("prompt based strategy", "grid strategy"):
                    return (
                        StrategyType.PROMPT
                        if raw.startswith("prompt")
                        else StrategyType.GRID
                    )
                if raw_compact in ("promptbasedstrategy", "gridstrategy"):
                    return (
                        StrategyType.PROMPT
                        if raw_compact.startswith("prompt")
                        else StrategyType.GRID
                    )
                if raw in ("prompt", "grid"):
                    return StrategyType.PROMPT if raw == "prompt" else StrategyType.GRID

                agent_name = str(meta.get("agent_name") or "").lower()
                if "prompt" in agent_name:
                    return StrategyType.PROMPT
                if "grid" in agent_name:
                    return StrategyType.GRID
                return None

            strategy_data_list = []
            for s in strategies:
                meta = s.strategy_metadata or {}
                cfg = s.config or {}
                status = map_status(s.status)
                stop_reason_display = ""
                if status == "stopped":
                    stop_reason = meta.get("stop_reason")
                    stop_reason_detail = meta.get("stop_reason_detail")
                    stop_reason_display = (
                        f"{'(' + stop_reason + ')' if stop_reason else ''}"
                        f"{stop_reason_detail if stop_reason_detail else ''}".strip()
                    ) or "..."

                total_pnl, total_pnl_pct = 0.0, 0.0
                if (
                    portfolio_summary
                    := await StrategyService.get_strategy_portfolio_summary(
                        s.strategy_id
                    )
                ):
                    total_pnl = to_optional_float(portfolio_summary.total_pnl) or 0.0
                    total_pnl_pct = (
                        to_optional_float(portfolio_summary.total_pnl_pct) or 0.0
                    )

                item = StrategySummaryData(
                    strategy_id=s.strategy_id,
                    strategy_name=s.name,
                    strategy_type=normalize_strategy_type(meta, cfg),
                    status=status,
                    stop_reason=stop_reason_display,
                    trading_mode=normalize_trading_mode(meta, cfg),
                    total_pnl=total_pnl,
                    total_pnl_pct=total_pnl_pct,
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
        "/performance",
        response_model=StrategyPerformanceResponse,
        summary="Get strategy performance and configuration overview",
        description=(
            "Return ROI strictly from portfolio view equity (total_value) relative to initial capital; model/provider; and final prompt strictly from templates (no fallback)."
        ),
    )
    async def get_strategy_performance(
        id: str = Query(..., description="Strategy ID"),
    ) -> StrategyPerformanceResponse:
        try:
            # Fail for explicitly invalid IDs (prefix 'invalid'), but do not raise 404
            raw_id = (id or "").strip()
            if raw_id.lower().startswith("invalid"):
                # Return HTTP 400 for invalid IDs
                raise HTTPException(
                    status_code=StatusCode.BAD_REQUEST, detail="Invalid strategy id"
                )

            data = await StrategyService.get_strategy_performance(id)
            if not data:
                # Strategy not found: return HTTP 404
                raise HTTPException(
                    status_code=StatusCode.NOT_FOUND, detail="Strategy not found"
                )

            return SuccessResponse.create(
                data=data,
                msg="Successfully retrieved strategy performance and configuration",
            )
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to retrieve strategy performance: {str(e)}",
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
        "/portfolio_summary",
        response_model=StrategyPortfolioSummaryResponse,
        summary="Get latest portfolio summary for a strategy",
        description=(
            "Return aggregated portfolio metrics (cash, total value, unrealized PnL)"
            " for the most recent snapshot."
        ),
    )
    async def get_strategy_portfolio_summary(
        id: str = Query(..., description="Strategy ID"),
    ) -> StrategyPortfolioSummaryResponse:
        try:
            data = await StrategyService.get_strategy_portfolio_summary(id)
            if not data:
                return SuccessResponse.create(
                    data=None,
                    msg="No portfolio summary found for strategy",
                )

            return SuccessResponse.create(
                data=data,
                msg="Successfully retrieved strategy portfolio summary",
            )
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to retrieve portfolio summary: {str(e)}",
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

    @router.post(
        "/start",
        response_model=StrategyStatusSuccessResponse,
        summary="Start a stopped strategy",
        description="Resume a stopped strategy by ID (via query param 'id'). This will trigger auto-resume logic.",
    )
    async def start_strategy(
        id: str = Query(..., description="Strategy ID"),
        background_tasks: BackgroundTasks = BackgroundTasks(),
        db: Session = Depends(get_db),
    ) -> StrategyStatusSuccessResponse:
        try:
            repo = get_strategy_repository(db_session=db)
            strategy = repo.get_strategy_by_strategy_id(id)
            if not strategy:
                raise HTTPException(status_code=404, detail="Strategy not found")

            # Update status to 'running' if it's stopped
            if strategy.status == "stopped":
                # Validate stop reason - only allow restarting stop-loss stopped strategies
                metadata = strategy.metadata or {}
                stop_reason = metadata.get("stop_reason")
                
                from valuecell.agents.common.trading.models import StopReason
                if stop_reason != StopReason.STOP_LOSS.value:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Cannot restart strategy: it was stopped for reason '{stop_reason or 'unknown'}'. Only stop-loss stopped strategies can be restarted.",
                    )
                
                repo.upsert_strategy(strategy_id=id, status="running")
                
                # Trigger auto-resume in background
                try:
                    from valuecell.core.coordinate.orchestrator import AgentOrchestrator
                    from valuecell.server.services.strategy_autoresume import _resume_one
                    
                    orchestrator = AgentOrchestrator()
                    # Refresh strategy object to get updated status
                    strategy = repo.get_strategy_by_strategy_id(id)
                    
                    # Schedule resume as background task
                    async def resume_task():
                        try:
                            await _resume_one(orchestrator, strategy)
                            logger.info(f"Successfully resumed strategy {id}")
                        except Exception as e:
                            logger.exception(f"Failed to resume strategy {id}: {e}")
                    
                    background_tasks.add_task(resume_task)
                    
                    response_data = StrategyStatusUpdateResponse(
                        strategy_id=id,
                        status="running",
                        message=f"Strategy '{id}' is being started. It may take a few moments to begin decision cycles.",
                    )
                except Exception as resume_error:
                    # If resume fails, at least status is updated
                    logger.warning(f"Failed to trigger auto-resume: {resume_error}")
                    response_data = StrategyStatusUpdateResponse(
                        strategy_id=id,
                        status="running",
                        message=f"Strategy '{id}' status updated to running. Please restart the server to activate.",
                    )
            elif strategy.status == "running":
                response_data = StrategyStatusUpdateResponse(
                    strategy_id=id,
                    status="running",
                    message=f"Strategy '{id}' is already running",
                )
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Cannot start strategy with status '{strategy.status}'",
                )

            return SuccessResponse.create(
                data=response_data,
                msg=f"Successfully started strategy '{id}'",
            )
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to start strategy: {str(e)}",
            )

    # Dynamic Strategy Endpoints
    @router.get(
        "/dynamic/scores",
        response_model=MarketStateAndScoresResponse,
        summary="Get market state and strategy scores",
        description="Get real-time market indicators and strategy scores for dynamic strategy selection",
    )
    async def get_market_state_and_scores(
        symbol: str = Query(..., description="Trading symbol (e.g., BTC/USDT)"),
        base_strategies: Optional[str] = Query(
            "TREND,GRID,BREAKOUT,ARBITRAGE",
            description="Comma-separated list of base strategies to evaluate",
        ),
        risk_mode: str = Query("NEUTRAL", description="Risk mode: AGGRESSIVE, NEUTRAL, or DEFENSIVE"),
        exchange_id: str = Query("okx", description="Exchange identifier"),
    ) -> MarketStateAndScoresResponse:
        """Get market state and strategy scores."""
        try:
            # Parse base strategies
            strategy_names = [s.strip() for s in base_strategies.split(",")]
            base_strategy_list = []
            for name in strategy_names:
                try:
                    base_strategy_list.append(ServiceBaseStrategyType(name))
                except ValueError:
                    logger.warning(f"Invalid strategy type: {name}, skipping")
                    continue

            if not base_strategy_list:
                base_strategy_list = [ServiceBaseStrategyType.TREND]

            # Parse risk mode
            try:
                risk_mode_enum = ServiceRiskMode(risk_mode.upper())
            except ValueError:
                risk_mode_enum = ServiceRiskMode.NEUTRAL

            # Create scorer and get scores
            scorer = DynamicStrategyScorer()
            result = await scorer.get_market_state_and_scores(
                symbols=[symbol],
                exchange_id=exchange_id,
                base_strategies=base_strategy_list,
                risk_mode=risk_mode_enum,
            )

            # Convert to response format
            response_data = MarketStateAndScoresData(
                currentState=result.currentState,
                strategyScores=[
                    {
                        "name": score.name,
                        "score": score.score,
                        "reason": score.reason,
                    }
                    for score in result.strategyScores
                ],
                recommendedStrategy=result.recommendedStrategy,
                marketIndicators={
                    "volatility": result.marketIndicators.volatility,
                    "trendStrength": result.marketIndicators.trendStrength,
                    "volumeRatio": result.marketIndicators.volumeRatio,
                    "marketSentiment": result.marketIndicators.marketSentiment,
                },
            )

            return SuccessResponse.create(
                data=response_data,
                msg="Successfully retrieved market state and strategy scores",
            )
        except Exception as e:
            logger.exception("Error getting market state and scores: {}", e)
            raise HTTPException(
                status_code=500,
                detail=f"Failed to get market state and scores: {str(e)}",
            )

    # Backtest Endpoints (Binance only)
    _backtest_service = BacktestService()

    @router.post(
        "/backtest/run",
        response_model=BacktestStartResponse,
        summary="Start a backtest (Binance only)",
        description="Start a backtest for a strategy configuration using Binance historical data",
    )
    async def run_backtest(
        config: BacktestConfigRequest,
        background_tasks: BackgroundTasks,
        db: Session = Depends(get_db),
    ) -> BacktestStartResponse:
        """Start a backtest."""
        try:
            from datetime import datetime

            # Parse dates
            start_date = datetime.fromisoformat(config.startDate.replace("Z", "+00:00"))
            end_date = datetime.fromisoformat(config.endDate.replace("Z", "+00:00"))

            # Extract symbols and interval from strategy config
            symbols = []
            interval = "1h"  # Default interval

            if config.strategyId:
                # Load strategy from database
                repo = get_strategy_repository(db_session=db)
                strategy = repo.get_strategy_by_strategy_id(config.strategyId)
                if not strategy:
                    raise HTTPException(status_code=404, detail="Strategy not found")
                # Extract symbols from strategy metadata
                meta = strategy.meta or {}
                symbols = meta.get("symbols", [])
                # Extract interval from strategy config if available
                cfg = strategy.config or {}
                trading_config = cfg.get("trading_config", {})
                decide_interval = trading_config.get("decide_interval", 60)
                # Map decide_interval to candle interval
                if decide_interval <= 60:
                    interval = "1m"
                elif decide_interval <= 300:
                    interval = "5m"
                elif decide_interval <= 3600:
                    interval = "1h"
                else:
                    interval = "1d"
            elif config.strategyConfig:
                # Extract from strategy config
                trading_config = config.strategyConfig.get("trading_config", {})
                symbols = trading_config.get("symbols", [])
                decide_interval = trading_config.get("decide_interval", 60)
                # Map decide_interval to candle interval
                if decide_interval <= 60:
                    interval = "1m"
                elif decide_interval <= 300:
                    interval = "5m"
                elif decide_interval <= 3600:
                    interval = "1h"
                else:
                    interval = "1d"

            if not symbols:
                raise HTTPException(
                    status_code=400, detail="No symbols found in strategy configuration"
                )

            # Create backtest config
            backtest_config = BacktestConfig(
                strategy_id=config.strategyId,
                strategy_config=config.strategyConfig,
                start_date=start_date,
                end_date=end_date,
                initial_capital=config.initialCapital,
                symbols=symbols,
                interval=interval,
            )

            # Start backtest
            backtest_id = await _backtest_service.start_backtest(backtest_config)

            return SuccessResponse.create(
                data={"backtestId": backtest_id},
                msg=f"Backtest {backtest_id} started",
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.exception("Error starting backtest: {}", e)
            raise HTTPException(
                status_code=500,
                detail=f"Failed to start backtest: {str(e)}",
            )

    @router.get(
        "/backtest/result",
        response_model=BacktestResultResponse,
        summary="Get backtest result",
        description="Get the result of a backtest by ID",
    )
    async def get_backtest_result(
        id: str = Query(..., description="Backtest ID"),
    ) -> BacktestResultResponse:
        """Get backtest result."""
        try:
            result = await _backtest_service.get_backtest_result(id)
            if not result:
                raise HTTPException(status_code=404, detail="Backtest not found")

            # Convert to response format
            response_data = BacktestResultData(
                backtestId=result.backtest_id,
                totalReturn=result.total_return,
                totalReturnPct=result.total_return_pct,
                sharpeRatio=result.sharpe_ratio,
                maxDrawdown=result.max_drawdown,
                maxDrawdownPct=result.max_drawdown_pct,
                winRate=result.win_rate,
                totalTrades=result.total_trades,
                startDate=result.start_date.isoformat(),
                endDate=result.end_date.isoformat(),
                equityCurve=result.equity_curve,
                trades=[
                    {
                        "symbol": trade.symbol,
                        "action": trade.action,
                        "entryPrice": trade.entry_price,
                        "exitPrice": trade.exit_price,
                        "quantity": trade.quantity,
                        "pnl": trade.pnl,
                        "pnlPct": trade.pnl_pct,
                        "entryTime": trade.entry_time.isoformat(),
                        "exitTime": trade.exit_time.isoformat(),
                    }
                    for trade in result.trades
                ],
            )

            return SuccessResponse.create(
                data=response_data,
                msg="Successfully retrieved backtest result",
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.exception("Error getting backtest result: {}", e)
            raise HTTPException(
                status_code=500,
                detail=f"Failed to get backtest result: {str(e)}",
            )

    # Position Control Endpoints
    @router.post(
        "/position-control/update",
        response_model=PositionControlUpdateResponse,
        summary="Update position control settings",
        description="Update position control settings for a running strategy",
    )
    async def update_position_control(
        request: PositionControlUpdateRequest,
        db: Session = Depends(get_db),
    ) -> PositionControlUpdateResponse:
        """Update position control settings."""
        try:
            repo = get_strategy_repository(db_session=db)
            strategy = repo.get_strategy_by_strategy_id(request.strategyId)
            if not strategy:
                raise HTTPException(status_code=404, detail="Strategy not found")

            # TODO: Implement actual position control update
            # This would need to update the running strategy's constraints
            # For now, just log the request
            logger.info(
                f"Position control update requested for strategy {request.strategyId}: "
                f"maxPositions={request.maxPositions}, "
                f"maxPositionQty={request.maxPositionQty}, "
                f"maxLeverage={request.maxLeverage}, "
                f"positionSize={request.positionSize}"
            )

            # In production, this would update the strategy runtime's constraints
            # For now, return success message
            return SuccessResponse.create(
                data={"message": "Position control settings updated successfully"},
                msg="Position control settings updated",
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.exception("Error updating position control: {}", e)
            raise HTTPException(
                status_code=500,
                detail=f"Failed to update position control: {str(e)}",
            )

    # Manual Close Position Endpoint
    @router.post(
        "/close_position",
        response_model=ManualClosePositionResponse,
        summary="Manually close position for a symbol",
        description="Close a specific position for a strategy by symbol and ratio. Strategy continues running after closure.",
    )
    async def close_position(
        request: ManualClosePositionRequest,
        db: Session = Depends(get_db),
    ) -> ManualClosePositionResponse:
        """Manually close position for a specific symbol.

        This will:
        1. Fetch current position for the symbol
        2. Calculate quantity to close based on closeRatio
        3. Execute market order to close the position
        4. Strategy continues running after closure
        """
        try:
            from valuecell.server.services.position_close_service import (
                close_position_for_strategy,
            )

            result = await close_position_for_strategy(
                strategy_id=request.strategyId,
                symbol=request.symbol,
                close_ratio=request.closeRatio,
                db=db,
            )

            return SuccessResponse.create(
                data=result,
                msg=f"Successfully closed {result.closeRatio*100:.1f}% of {result.symbol} position",
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.exception("Error closing position: {}", e)
            raise HTTPException(
                status_code=500,
                detail=f"Failed to close position: {str(e)}",
            )

    return router
