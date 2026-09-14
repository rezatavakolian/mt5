"""Price data model."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class PriceData:
    """Represents price data for a trading symbol."""
    symbol: str
    bid: float
    ask: float
    timestamp: datetime
    spread: Optional[float] = None
    
    def __post_init__(self):
        """Calculate spread if not provided."""
        if self.spread is None and self.bid > 0 and self.ask > 0:
            self.spread = self.ask - self.bid
    
    @property
    def mid_price(self) -> float:
        """Calculate mid price."""
        return (self.bid + self.ask) / 2
    
    @property
    def spread_pips(self) -> float:
        """Calculate spread in pips (assuming 4 decimal places for most forex pairs)."""
        if self.spread is None:
            return 0.0
        # Adjust for JPY pairs which use 2 decimal places
        if 'JPY' in self.symbol:
            return self.spread * 100
        return self.spread * 10000
    
    def is_valid(self) -> bool:
        """Check if price data is valid."""
        return (self.bid > 0 and 
                self.ask > 0 and 
                self.ask > self.bid and
                self.timestamp is not None)
