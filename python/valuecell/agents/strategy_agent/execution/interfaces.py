from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, List, Optional

from ..models import TradeInstruction, TxResult

# Contracts for execution gateways (module-local abstract interfaces).
# An implementation may route to a real exchange or a paper broker.


class ExecutionGateway(ABC):
    """Executes normalized trade instructions against an exchange/broker."""

    @abstractmethod
    async def execute(
        self,
        instructions: List[TradeInstruction],
        market_snapshot: Optional[Dict[str, float]] = None,
    ) -> List[TxResult]:
        """Execute the provided instructions and return TxResult items.

        Notes:
        - Implementations may simulate fills (paper) or submit to a real exchange.
        - market_snapshot is optional context for pricing simulations.
        - Lifecycle (partial fills, cancels) can be represented with PARTIAL/REJECTED.
        """

        raise NotImplementedError
