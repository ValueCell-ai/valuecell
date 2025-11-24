from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, AsyncGenerator, Dict, Optional

from loguru import logger

from valuecell.agents.common.trading._internal.runtime import create_strategy_runtime
from valuecell.agents.common.trading._internal.stream_controller import StreamController
from valuecell.agents.common.trading.models import (
    ComponentType,
    StopReason,
    StrategyStatus,
    StrategyStatusContent,
    UserRequest,
)
from valuecell.core.agent.responses import streaming
from valuecell.core.types import BaseAgent, StreamResponse

if TYPE_CHECKING:
    from valuecell.agents.common.trading._internal.runtime import (
        DecisionCycleResult,
        StrategyRuntime,
    )
    from valuecell.agents.common.trading.decision import Composer
    from valuecell.agents.common.trading.features.interfaces import BaseFeaturesPipeline


class BaseStrategyAgent(BaseAgent, ABC):
    """Abstract base class for strategy agents.

    Users should subclass this and implement:
    - _build_features_pipeline: Define feature computation logic
    - _create_decision_composer: Define decision composer (optional, defaults to LLM)
    - _on_start: Custom initialization after runtime creation (optional)
    - _on_cycle_result: Hook for post-cycle custom logic (optional)
    - _on_stop: Custom cleanup before finalization (optional)

    The base class handles:
    - Stream lifecycle and state transitions
    - Persistence orchestration (initial state, cycle results, finalization)
    - Error handling and resource cleanup
    """

    @abstractmethod
    def _build_features_pipeline(
        self, request: UserRequest
    ) -> BaseFeaturesPipeline | None:
        """Build the features pipeline for the strategy.

        Return a `FeaturesPipeline` implementation to customize how market data
        and feature vectors are produced for each decision cycle. Returning
        ``None`` instructs the runtime to use the default pipeline.

        Args:
            request: The user request with strategy configuration

        Returns:
            FeaturesPipeline instance or None for default behaviour
        """
        raise NotImplementedError

    def _create_decision_composer(self, request: UserRequest) -> Composer | None:
        """Build the decision composer for the strategy.

        Override to provide a custom composer. Return None to use default LLM composer.

        Args:
            request: The user request with strategy configuration

        Returns:
            Composer instance or None for default composer
        """
        return None

    def _on_start(self, runtime: StrategyRuntime, request: UserRequest) -> None:
        """Hook called after runtime creation, before first cycle.

        Use for custom initialization, caching, or metric registration.
        Exceptions are logged but don't prevent runtime startup.

        Args:
            runtime: The created strategy runtime
            request: The user request
        """
        pass

    def _on_cycle_result(
        self,
        result: DecisionCycleResult,
        runtime: StrategyRuntime,
        request: UserRequest,
    ) -> None:
        """Hook called after each decision cycle completes.

        Non-blocking; exceptions are swallowed and logged.
        Use for custom metrics, logging, or side effects.

        Args:
            result: The DecisionCycleResult from the cycle
            runtime: The strategy runtime
            request: The user request
        """
        pass

    def _on_stop(
        self, runtime: StrategyRuntime, request: UserRequest, reason: StopReason | str
    ) -> None:
        """Hook called before finalization when strategy stops.

        Use for cleanup or final reporting.
        Exceptions are logged but don't prevent finalization.

        Args:
            runtime: The strategy runtime
            request: The user request
            reason: Reason for stopping (e.g., 'normal_exit', 'cancelled', 'error')
        """
        pass

    async def stream(
        self,
        query: str,
        conversation_id: str,
        task_id: str,
        dependencies: Optional[Dict] = None,
    ) -> AsyncGenerator[StreamResponse, None]:
        """Stream strategy execution with lifecycle management.

        Handles:
        - Request parsing and validation
        - Runtime creation with custom hooks
        - State transitions and persistence
        - Decision loop execution
        - Resource cleanup and finalization
        """
        # Parse and validate request
        try:
            request = UserRequest.model_validate_json(query)
        except ValueError as exc:
            logger.exception("StrategyAgent received invalid payload")
            yield streaming.message_chunk(str(exc))
            yield streaming.done()
            return

        # Create runtime (calls _build_decision, _build_features_pipeline internally)
        # Reuse externally supplied strategy_id if present for continuation semantics.
        strategy_id_override = request.trading_config.strategy_id
        runtime = await self._create_runtime(
            request, strategy_id_override=strategy_id_override
        )
        strategy_id = runtime.strategy_id
        logger.info(
            "Created runtime for strategy_id={} conversation={} task={}",
            strategy_id,
            conversation_id,
            task_id,
        )

        # Initialize stream controller
        controller = StreamController(strategy_id)

        # Emit initial RUNNING status
        initial_payload = StrategyStatusContent(
            strategy_id=strategy_id,
            status=StrategyStatus.RUNNING,
        )
        yield streaming.component_generator(
            content=initial_payload.model_dump_json(),
            component_type=ComponentType.STATUS.value,
        )

        # Wait until strategy is marked as running in persistence layer
        await controller.wait_running()

        # Call user hook for custom initialization
        try:
            self._on_start(runtime, request)
        except Exception:
            logger.exception("Error in _on_start hook for strategy {}", strategy_id)

        stop_reason = StopReason.NORMAL_EXIT
        try:
            logger.info("Starting decision loop for strategy_id={}", strategy_id)
            # Idempotent initial state persistence: skip if already exists (resume).
            if not controller.has_initial_state():
                controller.persist_initial_state(runtime)
            else:
                logger.info(
                    "Detected existing initial state; skipping duplicate persist for strategy_id={}",
                    strategy_id,
                )

            # Main decision loop
            while controller.is_running():
                result = await runtime.run_cycle()
                logger.info(
                    "Run cycle completed for strategy={} trades_count={}",
                    strategy_id,
                    len(result.trades),
                )

                # Persist cycle results
                controller.persist_cycle_results(result)

                # Call user hook for post-cycle logic
                try:
                    self._on_cycle_result(result, runtime, request)
                except Exception:
                    logger.exception(
                        "Error in _on_cycle_result hook for strategy {}", strategy_id
                    )

                logger.info(
                    "Waiting for next decision cycle for strategy_id={}, interval={}seconds",
                    strategy_id,
                    request.trading_config.decide_interval,
                )
                await asyncio.sleep(request.trading_config.decide_interval)

            logger.info(
                "Strategy_id={} is no longer running, exiting decision loop",
                strategy_id,
            )
            stop_reason = StopReason.NORMAL_EXIT

        except asyncio.CancelledError:
            stop_reason = StopReason.CANCELLED
            logger.info("Strategy {} cancelled", strategy_id)
            raise
        except Exception as err:  # noqa: BLE001
            stop_reason = StopReason.ERROR
            logger.exception("StrategyAgent stream failed: {}", err)
            yield streaming.message_chunk(f"StrategyAgent error: {err}")
        finally:
            # Enforce position closure on normal stop (e.g., user clicked stop)
            if stop_reason == StopReason.NORMAL_EXIT:
                try:
                    trades = await runtime.coordinator.close_all_positions()
                    if trades:
                        controller.persist_trades(trades)
                except Exception:
                    logger.exception(
                        "Error closing positions on stop for strategy {}", strategy_id
                    )
                    # If closing positions fails, we should consider this an error state
                    # to prevent the strategy from being marked as cleanly stopped if it still has positions.
                    # However, the user intent was to stop.
                    # Let's log it and proceed, but maybe mark status as ERROR instead of STOPPED?
                    # For now, we stick to STOPPED but log the error clearly.
                    stop_reason = StopReason.ERROR_CLOSING_POSITIONS

            # Call user hook before finalization
            try:
                self._on_stop(runtime, request, stop_reason)
            except Exception:
                logger.exception("Error in _on_stop hook for strategy {}", strategy_id)

            # Persist a final portfolio snapshot regardless of stop reason (best-effort)
            try:
                controller.persist_portfolio_snapshot(runtime)
            except Exception:
                logger.exception(
                    "Failed to persist final portfolio snapshot for strategy {}",
                    strategy_id,
                )

            # Finalize: close resources and mark stopped/paused/error
            await controller.finalize(runtime, reason=stop_reason)
            yield streaming.done()

    async def _create_runtime(
        self, request: UserRequest, strategy_id_override: str | None = None
    ) -> StrategyRuntime:
        """Create strategy runtime with custom components.

        Calls user hooks to build custom decision composer and features pipeline.
        Falls back to defaults if hooks return None.

        Args:
            request: User request with strategy configuration

        Returns:
            StrategyRuntime instance
        """
        # Let user build custom composer (or None for default)
        composer = self._create_decision_composer(request)

        # Let user build custom features pipeline (or None for default)
        # The coordinator invokes this pipeline each cycle to fetch data
        # and compute the feature vectors consumed by the decision step.
        features_pipeline = self._build_features_pipeline(request)

        # Create runtime with custom components
        # The runtime factory will use defaults if composer/features are None
        return await create_strategy_runtime(
            request,
            composer=composer,
            features_pipeline=features_pipeline,
            strategy_id_override=strategy_id_override,
        )
