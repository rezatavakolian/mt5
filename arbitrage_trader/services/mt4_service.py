"""MetaTrader 4/5 service for connecting to MT platform."""

import logging
from typing import Optional, Dict, Any
from datetime import datetime

try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False
    logging.warning("MetaTrader5 package not available. Running in simulation mode.")

from ..config.settings import MT4Credentials
from ..models.price_data import PriceData


logger = logging.getLogger(__name__)


class MT4Service:
    """Service for interacting with MetaTrader platform."""
    
    def __init__(self, credentials: MT4Credentials):
        """Initialize MT4 service with credentials."""
        self.credentials = credentials
        self.connected = False
        self._last_error = None
        
        if not MT5_AVAILABLE:
            logger.warning("MT5 library not available - using mock mode")
    
    def connect(self) -> bool:
        """Establish connection to MetaTrader."""
        if not MT5_AVAILABLE:
            logger.info("Simulating MT connection (MT5 library not installed)")
            self.connected = True
            return True
        
        try:
            # Initialize MT5
            if not mt5.initialize():
                self._last_error = f"Initialization failed: {mt5.last_error()}"
                logger.error(self._last_error)
                return False
            
            # Login with credentials
            login_result = mt5.login(
                login=self.credentials.login,
                password=self.credentials.password,
                server=self.credentials.server
            )
            
            if not login_result:
                self._last_error = f"Login failed: {mt5.last_error()}"
                logger.error(self._last_error)
                return False
            
            self.connected = True
            logger.info(f"Successfully connected to {self.credentials.server}")
            return True
            
        except Exception as e:
            self._last_error = str(e)
            logger.error(f"Connection error: {e}")
            return False
    
    def disconnect(self) -> None:
        """Disconnect from MetaTrader."""
        if MT5_AVAILABLE and self.connected:
            mt5.shutdown()
        self.connected = False
        logger.info("Disconnected from MetaTrader")
    
    def get_symbol_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get information about a trading symbol."""
        if not self.connected:
            logger.warning("Not connected to MT platform")
            return None
        
        if not MT5_AVAILABLE:
            # Mock data for simulation
            return {
                'name': symbol,
                'visible': True,
                'trade_mode': 0,
                'spread': 10,
                'digits': 5,
                'point': 0.00001
            }
        
        try:
            info = mt5.symbol_info(symbol)
            if info is None:
                logger.warning(f"Symbol {symbol} not found")
                return None
            
            if not info.visible:
                if not mt5.symbol_select(symbol, True):
                    logger.warning(f"Could not enable symbol {symbol}")
                    return None
            
            return {
                'name': info.name,
                'visible': info.visible,
                'trade_mode': info.trade_mode,
                'spread': info.spread,
                'digits': info.digits,
                'point': info.point
            }
        except Exception as e:
            logger.error(f"Error getting symbol info for {symbol}: {e}")
            return None
    
    def get_current_price(self, symbol: str) -> Optional[PriceData]:
        """Get current bid/ask price for a symbol."""
        if not self.connected:
            logger.warning("Not connected to MT platform")
            return None
        
        if not MT5_AVAILABLE:
            # Mock data for simulation
            import random
            base_prices = {
                'EURUSD': 1.0850,
                'AUDUSD': 0.6520,
                'EURAUD': 1.6640
            }
            base = base_prices.get(symbol, 1.0)
            spread = random.uniform(0.0001, 0.0003)
            bid = base + random.uniform(-0.0005, 0.0005)
            ask = bid + spread
            
            return PriceData(
                symbol=symbol,
                bid=bid,
                ask=ask,
                timestamp=datetime.now()
            )
        
        try:
            tick = mt5.symbol_info_tick(symbol)
            if tick is None:
                logger.warning(f"No tick data for {symbol}")
                return None
            
            return PriceData(
                symbol=symbol,
                bid=tick.bid,
                ask=tick.ask,
                timestamp=datetime.fromtimestamp(tick.time)
            )
        except Exception as e:
            logger.error(f"Error getting price for {symbol}: {e}")
            return None
    
    def get_account_info(self) -> Optional[Dict[str, Any]]:
        """Get account information."""
        if not self.connected:
            return None
        
        if not MT5_AVAILABLE:
            return {
                'login': self.credentials.login,
                'server': self.credentials.server,
                'balance': 10000.0,
                'equity': 10000.0,
                'currency': 'USD'
            }
        
        try:
            account = mt5.account_info()
            if account is None:
                return None
            
            return {
                'login': account.login,
                'server': account.server,
                'balance': account.balance,
                'equity': account.equity,
                'currency': account.currency,
                'leverage': account.leverage
            }
        except Exception as e:
            logger.error(f"Error getting account info: {e}")
            return None
    
    @property
    def last_error(self) -> Optional[str]:
        """Get the last error message."""
        return self._last_error
