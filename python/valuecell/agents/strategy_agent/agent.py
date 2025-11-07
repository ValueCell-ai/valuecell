from __future__ import annotations

import asyncio
from typing import AsyncGenerator, Dict, Optional

from loguru import logger

from valuecell.core.agent.responses import streaming
from valuecell.core.types import BaseAgent, StreamResponse
from valuecell.server.services.strategy_persistence import (
    persist_portfolio_view,
    persist_trade_history,
    persist_strategy_summary,
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
                    item = persist_trade_history(runtime.strategy_id, trade)
                    if item:
                        logger.info(
                            "Persisted trade {} for strategy={}",
                            getattr(trade, "trade_id", None),
                            runtime.strategy_id,
                        )

                # Persist portfolio snapshot (positions)
                ok = persist_portfolio_view(result.portfolio_view)
                if ok:
                    logger.info(
                        "Persisted portfolio view for strategy={}",
                        runtime.strategy_id,
                    )

                # Persist strategy summary
                ok = persist_strategy_summary(result.strategy_summary)
                if ok:
                    logger.info(
                        "Persisted strategy summary for strategy={}",
                        runtime.strategy_id,
                    )

        except asyncio.CancelledError:
            raise
        except Exception as err:  # noqa: BLE001
            logger.exception("StrategyAgent stream failed: {}", err)
            yield streaming.message_chunk(f"StrategyAgent error: {err}")
        finally:
            yield streaming.done()
