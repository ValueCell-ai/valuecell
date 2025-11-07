from __future__ import annotations

import asyncio
from typing import AsyncGenerator, Dict, Optional

from loguru import logger

from valuecell.core.agent.responses import streaming
from valuecell.core.types import BaseAgent, StreamResponse
from valuecell.server.services.strategy_persistence import (
    build_strategy_summary,
    persist_portfolio_view,
    persist_trade_history,
)

from .models import (
    ComponentType,
    StrategyStatus,
    StrategyStatusContent,
    UserRequest,
)
from .runtime import create_strategy_runtime


class StrategyAgent(BaseAgent):
    """Top-level Strategy Agent integrating the decision coordinator."""

    async def stream(
        self,
        query: str,
        conversation_id: str,
        task_id: str,
        dependencies: Optional[Dict] = None,
    ) -> AsyncGenerator[StreamResponse, None]:
        try:
            request = UserRequest.model_validate_json(query)
        except ValueError as exc:
            logger.exception("StrategyAgent received invalid payload")
            yield streaming.message_chunk(str(exc))
            yield streaming.done()
            return

        runtime = create_strategy_runtime(request)
        logger.info(
            "Created runtime for strategy_id={} conversation={} task={}",
            runtime.strategy_id,
            conversation_id,
            task_id,
        )
        initial_payload = StrategyStatusContent(
            strategy_id=runtime.strategy_id,
            status=StrategyStatus.RUNNING,
        )
        yield streaming.component_generator(
            content=initial_payload.model_dump_json(),
            component_type=ComponentType.STATUS.value,
        )

        try:
            logger.info(
                "Starting decision loop for strategy_id={}", runtime.strategy_id
            )
            while True:
                result = await runtime.run_cycle()
                logger.info(
                    "Run cycle completed for strategy={} trades_count={}",
                    runtime.strategy_id,
                    len(result.trades),
                )
                # Persist and stream trades
                for trade in result.trades:
                    try:
                        item = persist_trade_history(runtime.strategy_id, trade)
                        if item:
                            logger.info(
                                "Persisted trade {} for strategy={}",
                                getattr(trade, "trade_id", None),
                                runtime.strategy_id,
                            )
                        else:
                            logger.warning(
                                "persist_trade_history returned None for strategy={} trade={}",
                                runtime.strategy_id,
                                getattr(trade, "trade_id", None),
                            )
                    except Exception:
                        logger.exception(
                            "Failed to persist trade {} for {}",
                            getattr(trade, "trade_id", None),
                            runtime.strategy_id,
                        )

                    yield streaming.component_generator(
                        content=trade.model_dump_json(),
                        component_type=ComponentType.UPDATE_TRADE.value,
                    )

                # Persist portfolio snapshot (positions)
                try:
                    ok = persist_portfolio_view(
                        runtime.strategy_id, result.portfolio_view
                    )
                    if ok:
                        positions_count = (
                            len(result.portfolio_view.positions)
                            if getattr(result.portfolio_view, "positions", None)
                            is not None
                            else 0
                        )
                        logger.info(
                            "Persisted portfolio view for strategy={} positions_count={}",
                            runtime.strategy_id,
                            positions_count,
                        )
                    else:
                        logger.warning(
                            "persist_portfolio_view returned False for strategy={}",
                            runtime.strategy_id,
                        )
                except Exception:
                    logger.exception(
                        "Failed to persist portfolio view for {}", runtime.strategy_id
                    )

                # Rebuild summary from DB (aggregates holdings/details) and stream
                try:
                    db_summary = build_strategy_summary(runtime.strategy_id)
                    if db_summary is not None:
                        logger.info(
                            "Streaming DB-backed strategy summary for strategy={}",
                            runtime.strategy_id,
                        )
                        yield streaming.component_generator(
                            content=db_summary.model_dump_json(),
                            component_type=ComponentType.UPDATE_STRATEGY_SUMMARY.value,
                        )
                    else:
                        logger.info(
                            "DB-backed summary missing, streaming runtime summary for strategy={}",
                            runtime.strategy_id,
                        )
                        # fallback to runtime-provided summary
                        yield streaming.component_generator(
                            content=result.strategy_summary.model_dump_json(),
                            component_type=ComponentType.UPDATE_STRATEGY_SUMMARY.value,
                        )
                except Exception:
                    logger.exception(
                        "Failed to build/stream strategy summary for {}",
                        runtime.strategy_id,
                    )
                    yield streaming.component_generator(
                        content=result.strategy_summary.model_dump_json(),
                        component_type=ComponentType.UPDATE_STRATEGY_SUMMARY.value,
                    )

                # Stream the portfolio view (original runtime snapshot)
                logger.info(
                    "Streaming portfolio view for strategy={} (positions={})",
                    runtime.strategy_id,
                    len(result.portfolio_view.positions)
                    if getattr(result.portfolio_view, "positions", None) is not None
                    else 0,
                )
                yield streaming.component_generator(
                    content=result.portfolio_view.model_dump_json(),
                    component_type=ComponentType.UPDATE_PORTFOLIO.value,
                )
                await asyncio.sleep(request.trading_config.decide_interval)

        except asyncio.CancelledError:
            raise
        except Exception as err:  # noqa: BLE001
            logger.exception("StrategyAgent stream failed: {}", err)
            yield streaming.message_chunk(f"StrategyAgent error: {err}")
        finally:
            yield streaming.done()
