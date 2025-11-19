from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional

from ..models import ComposeContext, TradeInstruction


@dataclass
class ComposeResult:
    instructions: List[TradeInstruction]
    rationale: Optional[str] = None


# Contracts for decision making (module-local abstract interfaces).
# Composer hosts the LLM call and guardrails, producing executable instructions.


class Composer(ABC):
    """LLM-driven decision composer with guardrails.

    Input: ComposeContext
    Output: TradeInstruction list
    """

    @abstractmethod
    async def compose(self, context: ComposeContext) -> ComposeResult:
        """Produce normalized trade instructions given the current context.

        This method is async because LLM providers and agent wrappers are often
        asynchronous. Implementations should perform any network/IO and return
        a validated ComposeResult containing instructions and optional rationale.
        """
        raise NotImplementedError
