"""Arbitrage detection service for identifying trading opportunities."""

import logging
from typing import List, Optional, Tuple
from datetime import datetime

from ..models.price_data import PriceData
from ..models.arbitrage_opportunity import (
    ArbitrageOpportunity, 
    ArbitrageType, 
    TradeLeg
)
from ..config.settings import TradingConfig
from .market_data_service import MarketDataService


logger = logging.getLogger(__name__)


class ArbitrageDetector:
    """Service for detecting arbitrage opportunities in forex markets."""
    
    def __init__(self, market_data_service: MarketDataService, config: TradingConfig):
        """Initialize arbitrage detector.
        
        Args:
            market_data_service: Service for fetching market data
            config: Trading configuration
        """
        self.market_data = market_data_service
        self.config = config
        self._opportunities_found = 0
    
    def check_triangular_arbitrage(self) -> Optional[ArbitrageOpportunity]:
        """Check for triangular arbitrage opportunities.
        
        Triangular arbitrage involves three currency pairs that form a triangle.
        For EUR/USD, AUD/USD, EUR/AUD:
        - Path 1: EUR -> USD -> AUD -> EUR
        - Path 2: EUR -> AUD -> USD -> EUR
        
        Returns:
            ArbitrageOpportunity if found, None otherwise
        """
        symbols = self.config.symbols
        
        # We need exactly 3 symbols for triangular arbitrage
        if len(symbols) != 3:
            logger.warning(f"Need exactly 3 symbols for triangular arbitrage, got {len(symbols)}")
            return None
        
        # Fetch current prices
        prices = self.market_data.fetch_all_prices(symbols)
        
        if len(prices) != 3:
            logger.warning(f"Could not fetch prices for all symbols: {prices.keys()}")
            return None
        
        # Identify the three pairs and their base/quote currencies
        # Expected: EURUSD, AUDUSD, EURAUD
        eur_usd = prices.get('EURUSD')
        aud_usd = prices.get('AUDUSD')
        eur_aud = prices.get('EURAUD')
        
        if not all([eur_usd, aud_usd, eur_aud]):
            logger.warning("Missing required price data for triangular arbitrage")
            return None
        
        # Check spreads are acceptable
        max_spread = self.config.max_spread_threshold_pips / 10000
        if any(p.spread > max_spread for p in [eur_usd, aud_usd, eur_aud] if p.spread):
            logger.debug("Spreads too wide for arbitrage")
            return None
        
        # Calculate synthetic cross rate and compare with actual
        # EUR/AUD can be calculated as: EUR/USD / AUD/USD
        synthetic_eur_aud_bid = eur_usd.bid / aud_usd.ask
        synthetic_eur_aud_ask = eur_usd.ask / aud_usd.bid
        
        actual_eur_aud_bid = eur_aud.bid
        actual_eur_aud_ask = eur_aud.ask
        
        # Check for arbitrage opportunity
        # Opportunity exists if we can buy low on one market and sell high on another
        
        # Strategy 1: Buy EUR/AUD synthetic, sell actual EUR/AUD
        profit1 = actual_eur_aud_bid - synthetic_eur_aud_ask
        profit1_pips = profit1 * 10000
        
        # Strategy 2: Sell EUR/AUD synthetic, buy actual EUR/AUD
        profit2 = synthetic_eur_aud_bid - actual_eur_aud_ask
        profit2_pips = profit2 * 10000
        
        best_profit_pips = max(profit1_pips, profit2_pips)
        
        if best_profit_pips < self.config.min_profit_threshold_pips:
            logger.debug(f"Profit {best_profit_pips:.2f} pips below threshold {self.config.min_profit_threshold_pips}")
            return None
        
        # Create trade legs based on the profitable strategy
        if profit1_pips > profit2_pips:
            # Buy synthetic (BUY EURUSD, SELL AUDUSD), sell actual (SELL EURAUD)
            legs = self._create_triangular_legs(
                strategy='synthetic_buy',
                prices={'EURUSD': eur_usd, 'AUDUSD': aud_usd, 'EURAUD': eur_aud},
                lot_size=self.config.lot_size
            )
            expected_profit = profit1_pips
        else:
            # Sell synthetic (SELL EURUSD, BUY AUDUSD), buy actual (BUY EURAUD)
            legs = self._create_triangular_legs(
                strategy='synthetic_sell',
                prices={'EURUSD': eur_usd, 'AUDUSD': aud_usd, 'EURAUD': eur_aud},
                lot_size=self.config.lot_size
            )
            expected_profit = profit2_pips
        
        if not legs:
            return None
        
        opportunity = ArbitrageOpportunity(
            opportunity_type=ArbitrageType.TRIANGULAR,
            symbols_involved=symbols,
            expected_profit_pips=expected_profit,
            timestamp=datetime.now(),
            legs=legs,
            confidence_score=self._calculate_confidence(prices)
        )
        
        if opportunity.validate_legs():
            self._opportunities_found += 1
            logger.info(f"Triangular arbitrage opportunity detected: {expected_profit:.2f} pips")
            return opportunity
        else:
            logger.warning("Invalid trade legs generated")
            return None
    
    def _create_triangular_legs(
        self, 
        strategy: str, 
        prices: dict, 
        lot_size: float
    ) -> List[TradeLeg]:
        """Create trade legs for triangular arbitrage.
        
        Args:
            strategy: 'synthetic_buy' or 'synthetic_sell'
            prices: Dictionary of price data
            lot_size: Base lot size for trades
            
        Returns:
            List of TradeLeg objects
        """
        legs = []
        eur_usd = prices['EURUSD']
        aud_usd = prices['AUDUSD']
        eur_aud = prices['EURAUD']
        
        if strategy == 'synthetic_buy':
            # Buy EUR/USD (BUY EURUSD)
            # Sell AUD/USD (SELL AUDUSD)  
            # Sell EUR/AUD (SELL EURAUD)
            legs.append(TradeLeg(
                symbol='EURUSD',
                action='BUY',
                lot_size=lot_size,
                entry_price=eur_usd.ask,
                stop_loss=self._calculate_stop_loss(eur_usd.ask, 'BUY'),
                take_profit=self._calculate_take_profit(eur_usd.ask, 'BUY')
            ))
            
            legs.append(TradeLeg(
                symbol='AUDUSD',
                action='SELL',
                lot_size=lot_size,
                entry_price=aud_usd.bid,
                stop_loss=self._calculate_stop_loss(aud_usd.bid, 'SELL'),
                take_profit=self._calculate_take_profit(aud_usd.bid, 'SELL')
            ))
            
            legs.append(TradeLeg(
                symbol='EURAUD',
                action='SELL',
                lot_size=lot_size,
                entry_price=eur_aud.bid,
                stop_loss=self._calculate_stop_loss(eur_aud.bid, 'SELL'),
                take_profit=self._calculate_take_profit(eur_aud.bid, 'SELL')
            ))
            
        elif strategy == 'synthetic_sell':
            # Sell EUR/USD (SELL EURUSD)
            # Buy AUD/USD (BUY AUDUSD)
            # Buy EUR/AUD (BUY EURAUD)
            legs.append(TradeLeg(
                symbol='EURUSD',
                action='SELL',
                lot_size=lot_size,
                entry_price=eur_usd.bid,
                stop_loss=self._calculate_stop_loss(eur_usd.bid, 'SELL'),
                take_profit=self._calculate_take_profit(eur_usd.bid, 'SELL')
            ))
            
            legs.append(TradeLeg(
                symbol='AUDUSD',
                action='BUY',
                lot_size=lot_size,
                entry_price=aud_usd.ask,
                stop_loss=self._calculate_stop_loss(aud_usd.ask, 'BUY'),
                take_profit=self._calculate_take_profit(aud_usd.ask, 'BUY')
            ))
            
            legs.append(TradeLeg(
                symbol='EURAUD',
                action='BUY',
                lot_size=lot_size,
                entry_price=eur_aud.ask,
                stop_loss=self._calculate_stop_loss(eur_aud.ask, 'BUY'),
                take_profit=self._calculate_take_profit(eur_aud.ask, 'BUY')
            ))
        
        return legs
    
    def _calculate_stop_loss(self, entry_price: float, action: str) -> float:
        """Calculate stop loss price.
        
        Args:
            entry_price: Entry price for the trade
            action: 'BUY' or 'SELL'
            
        Returns:
            Stop loss price
        """
        sl_pips = self.config.stop_loss_pips / 10000
        if action == 'BUY':
            return entry_price - sl_pips
        else:
            return entry_price + sl_pips
    
    def _calculate_take_profit(self, entry_price: float, action: str) -> float:
        """Calculate take profit price.
        
        Args:
            entry_price: Entry price for the trade
            action: 'BUY' or 'SELL'
            
        Returns:
            Take profit price
        """
        tp_pips = self.config.take_profit_pips / 10000
        if action == 'BUY':
            return entry_price + tp_pips
        else:
            return entry_price - tp_pips
    
    def _calculate_confidence(self, prices: dict) -> float:
        """Calculate confidence score for an opportunity.
        
        Args:
            prices: Dictionary of price data
            
        Returns:
            Confidence score between 0 and 1
        """
        confidence = 1.0
        
        # Reduce confidence based on spread width
        avg_spread_pips = sum(p.spread_pips for p in prices.values() if p.spread) / len(prices)
        spread_factor = max(0, 1 - (avg_spread_pips / self.config.max_spread_threshold_pips))
        confidence *= spread_factor
        
        # Reduce confidence based on price age
        for price in prices.values():
            if price.timestamp:
                age_seconds = (datetime.now() - price.timestamp).total_seconds()
                if age_seconds > 1:
                    confidence *= max(0, 1 - (age_seconds / 5))
        
        return max(0, min(1, confidence))
    
    def scan(self) -> List[ArbitrageOpportunity]:
        """Scan for all types of arbitrage opportunities.
        
        Returns:
            List of detected opportunities
        """
        opportunities = []
        
        # Check for triangular arbitrage
        triangular = self.check_triangular_arbitrage()
        if triangular:
            opportunities.append(triangular)
        
        return opportunities
    
    @property
    def opportunities_found(self) -> int:
        """Get total number of opportunities found."""
        return self._opportunities_found
