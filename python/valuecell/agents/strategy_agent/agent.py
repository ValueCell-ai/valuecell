from __future__ import annotations

import asyncio
import logging
from typing import AsyncGenerator, Dict, Optional

from valuecell.core.agent.responses import streaming
from valuecell.core.types import BaseAgent, StreamResponse

from .models import (
    ComponentType,
    StrategyStatusContent,
    UserRequest,
    StrategyStatus,
)
from .runtime import create_strategy_runtime

logger = logging.getLogger(__name__)


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
            logger.warning("StrategyAgent received invalid payload: %s", exc)
            yield streaming.message_chunk(str(exc))
            yield streaming.done()
            return

        runtime = create_strategy_runtime(request)
        initial_payload = StrategyStatusContent(
            strategy_id=runtime.strategy_id,
            status=StrategyStatus.RUNNING,
        )
        yield streaming.component_generator(
            content=initial_payload.model_dump_json(),
            component_type=ComponentType.STATUS.value,
        )

        try:
            while True:
                result = runtime.run_cycle()
                for trade in result.trades:
                    yield streaming.component_generator(
                        content=trade.model_dump_json(),
                        component_type=ComponentType.UPDATE_TRADE.value,
                    )
                yield streaming.component_generator(
                    content=result.strategy_summary.model_dump_json(),
                    component_type=ComponentType.UPDATE_STRATEGY_SUMMARY.value,
                )
                yield streaming.component_generator(
                    content=result.portfolio_view.model_dump_json(),
                    component_type=ComponentType.UPDATE_PORTFOLIO.value,
                )
                await asyncio.sleep(request.trading_config.decide_interval)

        except asyncio.CancelledError:
            raise
        except Exception as err:  # noqa: BLE001
            logger.exception("StrategyAgent stream failed: %%s", err)
            yield streaming.message_chunk(f"StrategyAgent error: {err}")
        finally:
            yield streaming.done()
