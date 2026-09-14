"""Main arbitrage bot that orchestrates all services."""

import logging
import time
import signal
from typing import Optional
from datetime import datetime

from .config.settings import Settings, MT4Credentials, TradingConfig
from .services.mt4_service import MT4Service
from .services.market_data_service import MarketDataService
from .services.arbitrage_detector import ArbitrageDetector
from .services.trade_executor import TradeExecutor
from .utils.logger_setup import setup_logging


logger = logging.getLogger(__name__)


class ArbitrageBot:
    """Main arbitrage trading bot that coordinates all services.
    
    This bot monitors forex markets for triangular arbitrage opportunities
    and automatically executes trades when profitable opportunities are detected.
    """
    
    def __init__(self, settings: Optional[Settings] = None):
        """Initialize the arbitrage bot.
        
        Args:
            settings: Application settings (uses defaults if None)
        """
        self.settings = settings or Settings()
        self._running = False
        self._shutdown_requested = False
        
        # Initialize services
        self.mt_service = MT4Service(self.settings.mt4)
        self.market_data = MarketDataService(self.mt_service)
        self.detector = ArbitrageDetector(self.market_data, self.settings.trading)
        self.executor = TradeExecutor(self.mt_service)
        
        # Statistics
        self._cycles_run = 0
        self._opportunities_detected = 0
        self._trades_executed = 0
        self._start_time: Optional[datetime] = None
    
    def start(self, run_duration_seconds: Optional[float] = None) -> None:
        """Start the arbitrage bot.
        
        Args:
            run_duration_seconds: Optional duration to run in seconds (None for indefinite)
        """
        logger.info("Starting Arbitrage Bot...")
        self._running = True
        self._shutdown_requested = False
        self._start_time = datetime.now()
        
        # Connect to MetaTrader
        if not self.mt_service.connect():
            logger.error("Failed to connect to MetaTrader")
            return
        
        # Display account info
        account_info = self.mt_service.get_account_info()
        if account_info:
            logger.info(
                f"Connected - Account: {account_info['login']}, "
                f"Balance: {account_info['balance']} {account_info['currency']}"
            )
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._handle_shutdown)
        if hasattr(signal, 'SIGTERM'):
            signal.signal(signal.SIGTERM, self._handle_shutdown)
        
        try:
            self._run_loop(run_duration_seconds)
        finally:
            self.stop()
    
    def _run_loop(self, duration: Optional[float]) -> None:
        """Main trading loop.
        
        Args:
            duration: Optional duration to run in seconds
        """
        start_time = time.time()
        
        while self._running and not self._shutdown_requested:
            cycle_start = time.time()
            
            # Check duration limit
            if duration and (time.time() - start_time) > duration:
                logger.info(f"Run duration {duration}s reached")
                break
            
            # Run one cycle
            self._run_cycle()
            
            # Sleep until next cycle
            elapsed = time.time() - cycle_start
            sleep_time = max(0, self.settings.trading.check_interval_seconds - elapsed)
            if sleep_time > 0:
                time.sleep(sleep_time)
    
    def _run_cycle(self) -> None:
        """Run one trading cycle."""
        self._cycles_run += 1
        
        # Scan for arbitrage opportunities
        opportunities = self.detector.scan()
        
        if opportunities:
            self._opportunities_detected += len(opportunities)
            
            for opportunity in opportunities:
                logger.info(opportunity.get_execution_summary())
                
                # Execute the opportunity
                if self.executor.execute_arbitrage(opportunity):
                    self._trades_executed += 1
                    logger.info(
                        f"Successfully executed arbitrage: "
                        f"{opportunity.expected_profit_pips:.2f} pips expected"
                    )
                else:
                    logger.warning("Arbitrage execution failed or partial")
        else:
            logger.debug(f"Cycle {self._cycles_run}: No opportunities found")
    
    def stop(self) -> None:
        """Stop the arbitrage bot."""
        logger.info("Stopping Arbitrage Bot...")
        self._running = False
        
        # Disconnect from MetaTrader
        self.mt_service.disconnect()
        
        # Log final statistics
        self._log_statistics()
    
    def _handle_shutdown(self, signum, frame) -> None:
        """Handle shutdown signals gracefully."""
        logger.info(f"Shutdown signal received ({signum})")
        self._shutdown_requested = True
    
    def _log_statistics(self) -> None:
        """Log final trading statistics."""
        if self._start_time:
            runtime = (datetime.now() - self._start_time).total_seconds()
            
            stats = [
                "=" * 50,
                "TRADING SESSION STATISTICS",
                "=" * 50,
                f"Runtime: {runtime:.0f} seconds ({runtime/60:.1f} minutes)",
                f"Cycles run: {self._cycles_run}",
                f"Opportunities detected: {self._opportunities_detected}",
                f"Trades executed: {self._trades_executed}",
                f"Detection rate: {self._opportunities_detected/max(1, self._cycles_run):.2%}",
                f"Execution success: {self._trades_executed/max(1, self._opportunities_detected):.2%}",
                "=" * 50
            ]
            
            for line in stats:
                logger.info(line)
    
    def run_demo(self, cycles: int = 10) -> None:
        """Run a demonstration of the bot without actual trading.
        
        Args:
            cycles: Number of demonstration cycles to run
        """
        logger.info("Running DEMO mode (no real trades)")
        
        # Connect to MT (simulated if library not available)
        if not self.mt_service.connect():
            logger.error("Failed to connect")
            return
        
        # Show account info
        account_info = self.mt_service.get_account_info()
        if account_info:
            print(f"\nAccount: {account_info['login']} @ {account_info['server']}")
            print(f"Balance: {account_info['balance']} {account_info['currency']}\n")
        
        # Run demo cycles
        for i in range(cycles):
            print(f"\n--- Cycle {i+1}/{cycles} ---")
            
            # Fetch prices
            prices = self.market_data.fetch_all_prices(self.settings.trading.symbols)
            
            if prices:
                print("\nCurrent Prices:")
                for symbol, price in prices.items():
                    print(f"  {symbol}: Bid={price.bid:.5f}, Ask={price.ask:.5f}, "
                          f"Spread={price.spread_pips:.1f} pips")
                
                # Check for arbitrage
                opportunity = self.detector.check_triangular_arbitrage()
                
                if opportunity:
                    print(f"\n*** ARBITRAGE OPPORTUNITY DETECTED ***")
                    print(opportunity.get_execution_summary())
                    
                    if opportunity.validate_legs():
                        print("\nTrade legs would be executed:")
                        for leg in opportunity.legs:
                            print(f"  {leg.action} {leg.lot_size} lots {leg.symbol} "
                                  f"@ {leg.entry_price:.5f}")
                else:
                    print("\nNo arbitrage opportunity found")
            else:
                print("Could not fetch prices")
            
            time.sleep(1)
        
        self.mt_service.disconnect()
        print("\nDemo completed.")
    
    @property
    def is_running(self) -> bool:
        """Check if bot is currently running."""
        return self._running
    
    @property
    def statistics(self) -> dict:
        """Get current trading statistics."""
        return {
            'cycles_run': self._cycles_run,
            'opportunities_detected': self._opportunities_detected,
            'trades_executed': self._trades_executed,
            'running_time': (datetime.now() - self._start_time).total_seconds() if self._start_time else 0
        }
