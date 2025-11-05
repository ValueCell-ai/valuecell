from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

from ..models import ComposeContext, TradeInstruction

# Contracts for decision making (module-local abstract interfaces).
# Composer hosts the LLM call and guardrails, producing executable instructions.


class Composer(ABC):
    """LLM-driven decision composer with guardrails.

    Input: ComposeContext
    Output: TradeInstruction list
    """

    @abstractmethod
    def compose(self, context: ComposeContext) -> List[TradeInstruction]:
        """Produce normalized trade instructions given the current context.
        Call the LLM, parse/validate output, apply guardrails (limits, step size,
        min notional, cool-down), and return executable instructions.
        Any optional auditing metadata should be recorded via HistoryRecorder.
        """
        raise NotImplementedError
