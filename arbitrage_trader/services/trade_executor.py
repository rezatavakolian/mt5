"""Trade execution service for placing and managing trades."""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False

from ..models.arbitrage_opportunity import ArbitrageOpportunity, TradeLeg
from .mt4_service import MT4Service


logger = logging.getLogger(__name__)


class TradeExecutor:
    """Service for executing trades on the MetaTrader platform."""
    
    def __init__(self, mt4_service: MT4Service):
        """Initialize trade executor.
        
        Args:
            mt4_service: MT4 service instance
        """
        self.mt4_service = mt4_service
        self._execution_log: List[Dict[str, Any]] = []
        self._positions_opened = 0
        self._positions_closed = 0
    
    def execute_arbitrage(self, opportunity: ArbitrageOpportunity) -> bool:
        """Execute all legs of an arbitrage opportunity.
        
        Args:
            opportunity: The arbitrage opportunity to execute
            
        Returns:
            True if all legs executed successfully, False otherwise
        """
        if not opportunity.validate_legs():
            logger.error("Invalid arbitrage opportunity")
            return False
        
        if not self.mt4_service.connected:
            logger.error("Not connected to MetaTrader")
            return False
        
        logger.info(f"Executing arbitrage with {len(opportunity.legs)} legs")
        
        successful_legs = 0
        failed_legs = 0
        
        for leg in opportunity.legs:
            success = self._execute_leg(leg, opportunity)
            if success:
                successful_legs += 1
            else:
                failed_legs += 1
                logger.error(f"Failed to execute leg: {leg.symbol} {leg.action}")
        
        # Log execution summary
        self._log_execution(opportunity, successful_legs, failed_legs)
        
        if failed_legs > 0:
            logger.warning(f"Partial execution: {successful_legs}/{len(opportunity.legs)} legs successful")
            # In a real system, you might want to close the successful legs here
            # to avoid exposure, but that depends on your risk management strategy
            return False
        
        logger.info(f"Successfully executed all {successful_legs} legs")
        return True
    
    def _execute_leg(self, leg: TradeLeg, opportunity: ArbitrageOpportunity) -> bool:
        """Execute a single trade leg.
        
        Args:
            leg: The trade leg to execute
            opportunity: Parent arbitrage opportunity
            
        Returns:
            True if execution successful, False otherwise
        """
        if not MT5_AVAILABLE:
            # Simulate execution in mock mode
            logger.info(f"[SIMULATED] {leg.action} {leg.lot_size} lots {leg.symbol} @ {leg.entry_price}")
            self._record_execution(leg, True, "Simulated", opportunity)
            self._positions_opened += 1
            return True
        
        try:
            # Determine order type
            order_type = mt5.ORDER_TYPE_BUY if leg.action == 'BUY' else mt5.ORDER_TYPE_SELL
            
            # Prepare the trade request
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": leg.symbol,
                "volume": leg.lot_size,
                "type": order_type,
                "price": leg.entry_price,
                "sl": leg.stop_loss,
                "tp": leg.take_profit,
                "deviation": 20,  # Maximum price deviation in points
                "magic": 234000,  # Magic number to identify orders from this EA
                "comment": f"Arb_{opportunity.opportunity_type.value}",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            
            # Send the order
            result = mt5.order_send(request)
            
            if result is None:
                error = mt5.last_error()
                logger.error(f"Order send failed: {error}")
                self._record_execution(leg, False, str(error), opportunity)
                return False
            
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                logger.error(f"Order failed: {result.comment} (retcode={result.retcode})")
                self._record_execution(leg, False, result.comment, opportunity)
                return False
            
            logger.info(
                f"Order executed: {leg.action} {leg.volume} {leg.symbol} @ {result.price}, "
                f"ticket={result.order}"
            )
            
            self._record_execution(leg, True, f"Ticket: {result.order}", opportunity)
            self._positions_opened += 1
            return True
            
        except Exception as e:
            logger.error(f"Exception executing leg: {e}")
            self._record_execution(leg, False, str(e), opportunity)
            return False
    
    def close_position(self, ticket: int) -> bool:
        """Close an open position by ticket.
        
        Args:
            ticket: Position ticket number
            
        Returns:
            True if closed successfully, False otherwise
        """
        if not MT5_AVAILABLE:
            logger.info(f"[SIMULATED] Close position #{ticket}")
            self._positions_closed += 1
            return True
        
        try:
            # Get position info
            position = mt5.position_get(ticket=ticket)
            if position is None:
                logger.error(f"Position {ticket} not found")
                return False
            
            # Prepare close request (opposite action)
            order_type = mt5.ORDER_TYPE_SELL if position.type == mt5.POSITION_TYPE_BUY else mt5.ORDER_TYPE_BUY
            
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": position.symbol,
                "volume": position.volume,
                "type": order_type,
                "position": ticket,
                "price": mt5.symbol_info_tick(position.symbol).ask if order_type == mt5.ORDER_TYPE_BUY else mt5.symbol_info_tick(position.symbol).bid,
                "deviation": 20,
                "magic": 234000,
                "comment": "Close arbitrage position",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            
            result = mt5.order_send(request)
            
            if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                logger.info(f"Position {ticket} closed successfully")
                self._positions_closed += 1
                return True
            else:
                logger.error(f"Failed to close position {ticket}")
                return False
                
        except Exception as e:
            logger.error(f"Exception closing position: {e}")
            return False
    
    def close_all_positions(self, symbols: Optional[List[str]] = None) -> int:
        """Close all open positions, optionally filtered by symbols.
        
        Args:
            symbols: List of symbols to filter by (None for all)
            
        Returns:
            Number of positions closed
        """
        if not MT5_AVAILABLE:
            logger.info("[SIMULATED] Close all positions")
            return 0
        
        try:
            positions = mt5.positions_get()
            if positions is None:
                return 0
            
            closed_count = 0
            for position in positions:
                if symbols is None or position.symbol in symbols:
                    if self.close_position(position.ticket):
                        closed_count += 1
            
            return closed_count
            
        except Exception as e:
            logger.error(f"Error closing positions: {e}")
            return 0
    
    def _record_execution(
        self, 
        leg: TradeLeg, 
        success: bool, 
        message: str,
        opportunity: ArbitrageOpportunity
    ) -> None:
        """Record execution details for logging and auditing.
        
        Args:
            leg: The trade leg
            success: Whether execution was successful
            message: Result message
            opportunity: Parent opportunity
        """
        record = {
            'timestamp': datetime.now(),
            'symbol': leg.symbol,
            'action': leg.action,
            'lot_size': leg.lot_size,
            'entry_price': leg.entry_price,
            'success': success,
            'message': message,
            'opportunity_type': opportunity.opportunity_type.value
        }
        
        self._execution_log.append(record)
    
    def _log_execution(
        self, 
        opportunity: ArbitrageOpportunity, 
        successful: int, 
        failed: int
    ) -> None:
        """Log execution summary.
        
        Args:
            opportunity: The executed opportunity
            successful: Number of successful legs
            failed: Number of failed legs
        """
        summary = {
            'timestamp': datetime.now(),
            'opportunity_type': opportunity.opportunity_type.value,
            'symbols': opportunity.symbols_involved,
            'expected_profit_pips': opportunity.expected_profit_pips,
            'legs_total': len(opportunity.legs),
            'legs_successful': successful,
            'legs_failed': failed
        }
        
        self._execution_log.append(summary)
        
        if failed == 0:
            logger.info(
                f"Arbitrage executed: {opportunity.expected_profit_pips:.2f} pips expected, "
                f"symbols={', '.join(opportunity.symbols_involved)}"
            )
    
    def get_execution_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent execution history.
        
        Args:
            limit: Maximum number of records to return
            
        Returns:
            List of execution records
        """
        return self._execution_log[-limit:]
    
    @property
    def positions_opened(self) -> int:
        """Get total positions opened."""
        return self._positions_opened
    
    @property
    def positions_closed(self) -> int:
        """Get total positions closed."""
        return self._positions_closed
