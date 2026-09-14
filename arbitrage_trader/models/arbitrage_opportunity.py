"""Arbitrage opportunity model."""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Tuple
from enum import Enum


class ArbitrageType(Enum):
    """Types of arbitrage opportunities."""
    TRIANGULAR = "triangular"
    STATISTICAL = "statistical"


@dataclass
class TradeLeg:
    """Represents one leg of an arbitrage trade."""
    symbol: str
    action: str  # 'BUY' or 'SELL'
    lot_size: float
    entry_price: float
    stop_loss: float = 0.0
    take_profit: float = 0.0


@dataclass
class ArbitrageOpportunity:
    """Represents a detected arbitrage opportunity."""
    opportunity_type: ArbitrageType
    symbols_involved: List[str]
    expected_profit_pips: float
    timestamp: datetime
    legs: List[TradeLeg]
    confidence_score: float = 0.0
    
    @property
    def is_triangular(self) -> bool:
        """Check if this is a triangular arbitrage."""
        return self.opportunity_type == ArbitrageType.TRIANGULAR
    
    @property
    def leg_count(self) -> int:
        """Get number of trade legs."""
        return len(self.legs)
    
    def validate_legs(self) -> bool:
        """Validate that all trade legs are properly configured."""
        if not self.legs:
            return False
        
        for leg in self.legs:
            if leg.lot_size <= 0:
                return False
            if leg.entry_price <= 0:
                return False
            if leg.action not in ['BUY', 'SELL']:
                return False
        
        return True
    
    def get_execution_summary(self) -> str:
        """Get a summary of the opportunity for logging/display."""
        summary = [
            f"Type: {self.opportunity_type.value}",
            f"Symbols: {', '.join(self.symbols_involved)}",
            f"Expected Profit: {self.expected_profit_pips:.2f} pips",
            f"Confidence: {self.confidence_score:.2%}",
            f"Legs: {self.leg_count}"
        ]
        
        for i, leg in enumerate(self.legs, 1):
            summary.append(f"  Leg {i}: {leg.action} {leg.lot_size} lots {leg.symbol} @ {leg.entry_price}")
        
        return "\n".join(summary)
