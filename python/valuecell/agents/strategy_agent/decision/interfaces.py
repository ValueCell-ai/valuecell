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
    async def compose(self, context: ComposeContext) -> List[TradeInstruction]:
        """Produce normalized trade instructions given the current context.

        This method is async because LLM providers and agent wrappers are often
        asynchronous. Implementations should perform any network/IO and return
        a validated list of TradeInstruction objects.
        """
        raise NotImplementedError
