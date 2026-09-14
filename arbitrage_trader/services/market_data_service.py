"""Market data service for fetching and managing price data."""

import logging
from typing import Dict, Optional, List
from datetime import datetime
from collections import deque

from ..models.price_data import PriceData
from .mt4_service import MT4Service


logger = logging.getLogger(__name__)


class MarketDataService:
    """Service for fetching and caching market data."""
    
    def __init__(self, mt4_service: MT4Service, cache_size: int = 100):
        """Initialize market data service.
        
        Args:
            mt4_service: MT4 service instance
            cache_size: Maximum number of price updates to cache per symbol
        """
        self.mt4_service = mt4_service
        self._price_cache: Dict[str, deque] = {}
        self._latest_prices: Dict[str, PriceData] = {}
        self._cache_size = cache_size
        self._last_update: Dict[str, datetime] = {}
    
    def fetch_price(self, symbol: str) -> Optional[PriceData]:
        """Fetch current price for a symbol.
        
        Args:
            symbol: Trading symbol (e.g., 'EURUSD')
            
        Returns:
            PriceData object or None if fetch failed
        """
        if not self.mt4_service.connected:
            logger.warning("MT service not connected")
            return None
        
        price_data = self.mt4_service.get_current_price(symbol)
        
        if price_data and price_data.is_valid():
            self._update_cache(symbol, price_data)
            return price_data
        else:
            logger.warning(f"Invalid price data for {symbol}")
            return None
    
    def fetch_all_prices(self, symbols: List[str]) -> Dict[str, PriceData]:
        """Fetch prices for multiple symbols.
        
        Args:
            symbols: List of trading symbols
            
        Returns:
            Dictionary mapping symbol to PriceData
        """
        prices = {}
        for symbol in symbols:
            price = self.fetch_price(symbol)
            if price:
                prices[symbol] = price
        
        return prices
    
    def get_latest_price(self, symbol: str) -> Optional[PriceData]:
        """Get the latest cached price for a symbol.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Latest PriceData or None if not available
        """
        return self._latest_prices.get(symbol)
    
    def get_price_history(self, symbol: str, count: int = 10) -> List[PriceData]:
        """Get recent price history for a symbol.
        
        Args:
            symbol: Trading symbol
            count: Number of historical prices to retrieve
            
        Returns:
            List of PriceData objects (most recent first)
        """
        cache = self._price_cache.get(symbol, deque())
        return list(cache)[:count]
    
    def _update_cache(self, symbol: str, price_data: PriceData) -> None:
        """Update the price cache with new data.
        
        Args:
            symbol: Trading symbol
            price_data: New price data
        """
        # Initialize cache if needed
        if symbol not in self._price_cache:
            self._price_cache[symbol] = deque(maxlen=self._cache_size)
        
        # Add to cache
        self._price_cache[symbol].appendleft(price_data)
        self._latest_prices[symbol] = price_data
        self._last_update[symbol] = datetime.now()
        
        logger.debug(f"Updated cache for {symbol}: bid={price_data.bid:.5f}, ask={price_data.ask:.5f}")
    
    def get_last_update_time(self, symbol: str) -> Optional[datetime]:
        """Get the timestamp of the last price update for a symbol.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Datetime of last update or None
        """
        return self._last_update.get(symbol)
    
    def is_price_fresh(self, symbol: str, max_age_seconds: float = 5.0) -> bool:
        """Check if the cached price is still fresh.
        
        Args:
            symbol: Trading symbol
            max_age_seconds: Maximum age in seconds for price to be considered fresh
            
        Returns:
            True if price is fresh, False otherwise
        """
        last_update = self._last_update.get(symbol)
        if last_update is None:
            return False
        
        age = (datetime.now() - last_update).total_seconds()
        return age <= max_age_seconds
    
    def clear_cache(self, symbol: Optional[str] = None) -> None:
        """Clear the price cache.
        
        Args:
            symbol: Specific symbol to clear, or None to clear all
        """
        if symbol:
            if symbol in self._price_cache:
                self._price_cache[symbol].clear()
            if symbol in self._latest_prices:
                del self._latest_prices[symbol]
            if symbol in self._last_update:
                del self._last_update[symbol]
        else:
            self._price_cache.clear()
            self._latest_prices.clear()
            self._last_update.clear()
        
        logger.info(f"Cleared price cache{'for ' + symbol if symbol else ''}")
