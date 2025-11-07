from __future__ import annotations

import asyncio
from datetime import datetime
from typing import AsyncGenerator, Dict, Optional

from loguru import logger

from valuecell.core.agent.responses import streaming
from valuecell.core.types import BaseAgent, StreamResponse
from valuecell.server.services import strategy_persistence

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
        strategy_id = runtime.strategy_id
        logger.info(
            "Created runtime for strategy_id={} conversation={} task={}",
            strategy_id,
            conversation_id,
            task_id,
        )
        initial_payload = StrategyStatusContent(
            strategy_id=strategy_id,
            status=StrategyStatus.RUNNING,
        )
        yield streaming.component_generator(
            content=initial_payload.model_dump_json(),
            component_type=ComponentType.STATUS.value,
        )

        # Wait until strategy is marked as running in persistence layer
        since = datetime.now()
        while not strategy_persistence.strategy_running(strategy_id):
            if (datetime.now() - since).total_seconds() > 300:
                logger.error(
                    "Timeout waiting for strategy_id={} to be marked as running",
                    strategy_id,
                )
                break

            await asyncio.sleep(1)
            logger.info(
                "Waiting for strategy_id={} to be marked as running", strategy_id
            )

        try:
            logger.info("Starting decision loop for strategy_id={}", strategy_id)
            while True:
                if not strategy_persistence.strategy_running(strategy_id):
                    logger.info(
                        "Strategy_id={} is no longer running, exiting decision loop",
                        strategy_id,
                    )
                    break

                result = await runtime.run_cycle()
                logger.info(
                    "Run cycle completed for strategy={} trades_count={}",
                    strategy_id,
                    len(result.trades),
                )
                # Persist and stream trades
                for trade in result.trades:
                    item = strategy_persistence.persist_trade_history(
                        strategy_id, trade
                    )
                    if item:
                        logger.info(
                            "Persisted trade {} for strategy={}",
                            getattr(trade, "trade_id", None),
                            strategy_id,
                        )

                # Persist portfolio snapshot (positions)
                ok = strategy_persistence.persist_portfolio_view(result.portfolio_view)
                if ok:
                    logger.info(
                        "Persisted portfolio view for strategy={}",
                        strategy_id,
                    )

                # Persist strategy summary
                ok = strategy_persistence.persist_strategy_summary(
                    result.strategy_summary
                )
                if ok:
                    logger.info(
                        "Persisted strategy summary for strategy={}",
                        strategy_id,
                    )

                logger.info(
                    "Waiting for next decision cycle for strategy_id={}, interval={}seconds",
                    strategy_id,
                    request.trading_config.decide_interval,
                )
                await asyncio.sleep(request.trading_config.decide_interval)

        except asyncio.CancelledError:
            raise
        except Exception as err:  # noqa: BLE001
            logger.exception("StrategyAgent stream failed: {}", err)
            yield streaming.message_chunk(f"StrategyAgent error: {err}")
        finally:
            yield streaming.done()
