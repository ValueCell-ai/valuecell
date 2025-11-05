from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

from ..models import TradeInstruction

# Contracts for execution gateways (module-local abstract interfaces).
# An implementation may route to a real exchange or a paper broker.


class ExecutionGateway(ABC):
    """Executes normalized trade instructions against an exchange/broker."""

    @abstractmethod
    def execute(self, instructions: List[TradeInstruction]) -> None:
        """Submit the provided instructions for execution.
        Implementors may be synchronous or asynchronous. At this stage we
        do not model order/fill/cancel lifecycles.
        """

        raise NotImplementedError
