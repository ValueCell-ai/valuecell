from typing import Dict, List, Optional

from ..models import TradeInstruction, TradeSide, TxResult
from .interfaces import ExecutionGateway


class PaperExecutionGateway(ExecutionGateway):
    """Async paper executor that simulates fills with slippage and fees.

    - Uses instruction.max_slippage_bps to compute execution price around snapshot.
    - Applies a flat fee_bps to notional to produce fee_cost.
    - Marks orders as FILLED with filled_qty=requested quantity.
    """

    def __init__(self, fee_bps: float = 10.0) -> None:
        self._fee_bps = float(fee_bps)
        self.executed: List[TradeInstruction] = []

    async def execute(
        self,
        instructions: List[TradeInstruction],
        market_snapshot: Optional[Dict[str, float]] = None,
    ) -> List[TxResult]:
        results: List[TxResult] = []
        price_map = market_snapshot or {}
        for inst in instructions:
            self.executed.append(inst)
            ref_price = float(price_map.get(inst.instrument.symbol, 0.0) or 0.0)
            slip_bps = float(inst.max_slippage_bps or 0.0)
            slip = slip_bps / 10_000.0
            if inst.side == TradeSide.BUY:
                exec_price = ref_price * (1.0 + slip)
            else:
                exec_price = ref_price * (1.0 - slip)

            notional = exec_price * float(inst.quantity)
            fee_cost = notional * (self._fee_bps / 10_000.0) if notional else 0.0

            results.append(
                TxResult(
                    instruction_id=inst.instruction_id,
                    instrument=inst.instrument,
                    side=inst.side,
                    requested_qty=float(inst.quantity),
                    filled_qty=float(inst.quantity),
                    avg_exec_price=float(exec_price) if exec_price else None,
                    slippage_bps=slip_bps or None,
                    fee_cost=fee_cost or None,
                    leverage=inst.leverage,
                    meta=inst.meta,
                )
            )

        return results
