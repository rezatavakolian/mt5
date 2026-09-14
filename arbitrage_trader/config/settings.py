"""Configuration settings for the arbitrage trader."""

from dataclasses import dataclass
from typing import List


@dataclass
class MT4Credentials:
    """MetaTrader account credentials."""
    server: str = "MetaQuotes-Demo"
    login: int = 112605427
    password: str = "*1ArTjSj"
    investor_password: str = "6dO_PfId"


@dataclass
class TradingConfig:
    """Trading configuration parameters."""
    # Symbols to monitor for arbitrage
    symbols: List[str] = None
    
    # Arbitrage detection thresholds
    min_profit_threshold_pips: float = 2.0
    max_spread_threshold_pips: float = 3.0
    
    # Risk management
    lot_size: float = 0.01
    max_positions: int = 3
    stop_loss_pips: float = 10.0
    take_profit_pips: float = 15.0
    
    # Timing
    price_fetch_timeout_ms: int = 1000
    check_interval_seconds: float = 0.5
    
    def __post_init__(self):
        if self.symbols is None:
            self.symbols = ["EURUSD", "AUDUSD", "EURAUD"]


@dataclass
class Settings:
    """Application settings container."""
    mt4: MT4Credentials = None
    trading: TradingConfig = None
    
    def __post_init__(self):
        if self.mt4 is None:
            self.mt4 = MT4Credentials()
        if self.trading is None:
            self.trading = TradingConfig()
