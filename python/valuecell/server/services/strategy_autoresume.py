"""Server-side strategy auto-resume logic.

This module scans persisted strategies with status 'running' on process
startup and dispatches them through the existing AgentOrchestrator using
their stored configuration. The core orchestrator remains unaware of
auto-resume concerns per design (separation of coordination vs runtime ops).

Resume Semantics:
 - Strategies whose status == 'running' (previous session crashed) are resumed.
 - Strategies whose status == 'stopped' with metadata.stop_reason == 'cancelled'
     (gracefully cancelled but intended to auto-resume) are also resumed.
 - Each strategy's original config dict is parsed into a UserRequest.
 - The stored strategy_id is injected into TradingConfig.strategy_id so the
   underlying runtime reuses portfolio state (idempotent initial snapshot).
 - Streaming responses are consumed and discarded (fire-and-forget). External
   observers can implement their own hooks if needed.

Failures during individual strategy resume are logged and skipped without
impacting other candidates.
"""

from __future__ import annotations

import asyncio
from typing import Optional

from loguru import logger

from valuecell.agents.common.trading.models import (
    StopReason,
    StrategyStatus,
    StrategyStatusContent,
    UserRequest,
)
from valuecell.core.coordinate.orchestrator import AgentOrchestrator
from valuecell.core.types import CommonResponseEvent, UserInput, UserInputMetadata
from valuecell.server.db.models.strategy import Strategy
from valuecell.server.db.repositories.strategy_repository import get_strategy_repository
from valuecell.server.services import strategy_persistence
from valuecell.utils.uuid import generate_conversation_id

_AUTORESUME_STARTED = False


async def auto_resume_strategies(
    orchestrator: AgentOrchestrator,
    max_strategies: Optional[int] = None,
) -> None:
    """Dispatch background resume tasks for persisted running strategies.

    Args:
        orchestrator: Existing AgentOrchestrator instance.
        max_strategies: Optional limit to number of strategies resumed.
    """
    global _AUTORESUME_STARTED
    if _AUTORESUME_STARTED:
        return
    _AUTORESUME_STARTED = True

    try:
        repo = get_strategy_repository()
        rows = repo.list_strategies_by_status(
            [StrategyStatus.RUNNING.value, StrategyStatus.STOPPED.value],
            limit=max_strategies,
        )
        candidates = [s for s in rows if _should_resume(s)]
        if not candidates:
            logger.info("Auto-resume: no eligible strategies found")
            return
        logger.info("Auto-resume: found {} eligible strategies", len(candidates))
        # Create tasks for each resume and keep them running. We await the
        # gathered tasks so that when this coroutine is run with
        # `asyncio.run(...)` (background thread) the loop stays alive until
        # the resumed strategies finish. When scheduled on an already-running
        # loop, this will run as background tasks concurrently as well.
        tasks = [asyncio.create_task(_resume_one(orchestrator, s)) for s in candidates]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    except asyncio.CancelledError:
        raise
    except Exception:
        logger.exception("Auto-resume scan failed")


async def _resume_one(orchestrator: AgentOrchestrator, strategy_row: Strategy) -> None:
    strategy_id = strategy_row.strategy_id
    try:
        config_dict = strategy_row.config or {}
        metadata = strategy_row.strategy_metadata or {}
        agent_name = metadata.get("agent_name")

        # Parse request; tolerate partial configs
        request = UserRequest.model_validate(config_dict)
        if request.trading_config.strategy_id is None and strategy_id:
            request.trading_config.strategy_id = strategy_id

        user_input = UserInput(
            query=request.model_dump_json(),
            target_agent_name=agent_name,
            meta=UserInputMetadata(
                user_id=strategy_row.user_id,
                conversation_id=generate_conversation_id(),
            ),
        )

        async for chunk in orchestrator.process_user_input(user_input):
            logger.debug("Auto-resume chunk for strategy_id={}: {}", strategy_id, chunk)
            if chunk.event == CommonResponseEvent.COMPONENT_GENERATOR:
                logger.info(
                    "Auto-resume dispatched strategy_id={} agent={}",
                    strategy_id,
                    agent_name,
                )
                status_content = StrategyStatusContent.model_validate_json(
                    chunk.data.payload.content
                )
                strategy_persistence.set_strategy_status(
                    strategy_id, status_content.status.value
                )
                return

    except asyncio.CancelledError:
        raise
    except Exception:
        logger.exception(
            "Auto-resume failed for strategy_id={}", strategy_id or "<unknown>"
        )


def _should_resume(strategy_row: Strategy) -> bool:
    """Return True if strategy should be auto-resumed based on status/metadata."""
    status_raw = strategy_row.status or ""
    metadata = strategy_row.strategy_metadata or {}
    try:
        status_enum = StrategyStatus(status_raw)
    except Exception:
        # Unknown/invalid status - skip
        return False

    if status_enum == StrategyStatus.RUNNING:
        return True

    if (
        status_enum == StrategyStatus.STOPPED
        and metadata.get("stop_reason") == StopReason.CANCELLED.value
    ):
        return True

    return False
