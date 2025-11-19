from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from valuecell.agents.common.trading.models import (
    FeatureVector,
    TradeInstruction,
    TxResult,
)

# Contracts for execution gateways (module-local abstract interfaces).
# An implementation may route to a real exchange or a paper broker.


class BaseExecutionGateway(ABC):
    """Executes normalized trade instructions against an exchange/broker."""

    @abstractmethod
    async def execute(
        self,
        instructions: List[TradeInstruction],
        market_features: Optional[List[FeatureVector]] = None,
    ) -> List[TxResult]:
        """Execute the provided instructions and return TxResult items.

        Notes:
        - Implementations may simulate fills (paper) or submit to a real exchange.
        - market_features contains interval="market" FeatureVector entries for pricing.
        - Lifecycle (partial fills, cancels) can be represented with PARTIAL/REJECTED.
        """

        raise NotImplementedError

    @abstractmethod
    async def close(self) -> None:
        """Close the gateway and release any held resources.

        Implementations should cleanup network connections, clients, or other
        resources they hold. This method is optional to call but should be
        implemented by gateways that allocate external resources.
        """

        raise NotImplementedError
