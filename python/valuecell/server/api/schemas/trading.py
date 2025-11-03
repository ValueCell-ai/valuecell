"""Trading-related API schemas."""

from typing import List, Optional

from pydantic import BaseModel, Field

from .base import SuccessResponse


class PositionItem(BaseModel):
    """Represents a single open position entry."""

    symbol: str = Field(..., description="Symbol in client format, e.g. BTC-USD")
    quantity: float = Field(..., description="Position size")
    entry_price: float = Field(..., description="Average entry price")
    current_price: Optional[float] = Field(
        None, description="Current mark/mid price if available"
    )
    unrealized_pnl: float = Field(..., description="Unrealized P&L in quote currency")
    pnl_percent: Optional[float] = Field(
        None, description="Unrealized P&L percentage relative to notional"
    )


class OpenPositionsData(BaseModel):
    """Container of open positions for the account."""

    exchange: str = Field(..., description="Exchange identifier, e.g. okx")
    network: Optional[str] = Field(None, description="Network or environment")
    positions: List[PositionItem] = Field(default_factory=list)


class OpenPositionsResponse(SuccessResponse[OpenPositionsData]):
    """Success response wrapping open positions data."""

    pass
