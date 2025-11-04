from __future__ import annotations

# Core interfaces for orchestration and portfolio service.
# Plain ABCs to avoid runtime dependencies on pydantic. Concrete implementations
# wire the pipeline: data -> features -> composer -> execution -> history/digest.

from abc import ABC, abstractmethod


class DecisionCoordinator(ABC):
    """Coordinates a single decision cycle end-to-end.

    A typical run performs:
        1) fetch portfolio view
        2) pull data and compute features
        3) build compose context (prompt_text, digest, constraints)
        4) compose (LLM + guardrails) -> trade instructions
        5) execute instructions
        6) record checkpoints and update digest
    """

    @abstractmethod
    def run_once(self) -> None:
        """Execute one decision cycle."""
        raise NotImplementedError
