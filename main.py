#!/usr/bin/env python3
"""
Forex Triangular Arbitrage Trading Bot

This software monitors forex markets for triangular arbitrage opportunities
among EUR/USD, AUD/USD, and EUR/AUD currency pairs, and automatically
executes trades when profitable opportunities are detected.

Usage:
    python main.py --demo          # Run in demo mode (no real trades)
    python main.py --live          # Run in live trading mode
    python main.py --duration 60   # Run for 60 seconds
    python main.py --help          # Show help message

Account Configuration:
    The default account credentials are pre-configured from your provided demo account.
    Modify config/settings.py or use environment variables to override.
"""

import argparse
import logging
import sys

from arbitrage_trader import ArbitrageBot
from arbitrage_trader.config.settings import Settings, MT4Credentials, TradingConfig
from arbitrage_trader.utils.logger_setup import setup_logging


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Forex Triangular Arbitrage Trading Bot',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        '--demo',
        action='store_true',
        help='Run in demo mode (simulated trades, no real money)'
    )
    
    parser.add_argument(
        '--live',
        action='store_true',
        help='Run in live trading mode (REAL trades with real money)'
    )
    
    parser.add_argument(
        '--duration',
        type=float,
        default=None,
        help='Trading duration in seconds (default: run indefinitely)'
    )
    
    parser.add_argument(
        '--cycles',
        type=int,
        default=10,
        help='Number of demo cycles to run (default: 10)'
    )
    
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Logging level (default: INFO)'
    )
    
    parser.add_argument(
        '--log-file',
        type=str,
        default=None,
        help='Log file path (default: console only)'
    )
    
    parser.add_argument(
        '--lot-size',
        type=float,
        default=0.01,
        help='Trade lot size (default: 0.01)'
    )
    
    parser.add_argument(
        '--min-profit',
        type=float,
        default=2.0,
        help='Minimum profit threshold in pips (default: 2.0)'
    )
    
    return parser.parse_args()


def create_settings(args) -> Settings:
    """Create settings from arguments."""
    # Use the provided demo account credentials
    credentials = MT4Credentials(
        server="MetaQuotes-Demo",
        login=112605427,
        password="*1ArTjSj",
        investor_password="6dO_PfId"
    )
    
    # Configure trading parameters
    trading_config = TradingConfig(
        symbols=["EURUSD", "AUDUSD", "EURAUD"],
        min_profit_threshold_pips=args.min_profit,
        max_spread_threshold_pips=3.0,
        lot_size=args.lot_size,
        max_positions=3,
        stop_loss_pips=10.0,
        take_profit_pips=15.0,
        check_interval_seconds=0.5
    )
    
    return Settings(mt4=credentials, trading=trading_config)


def main():
    """Main entry point."""
    args = parse_arguments()
    
    # Setup logging
    log_level = getattr(logging, args.log_level)
    setup_logging(level=log_level, log_file=args.log_file)
    
    logger = logging.getLogger(__name__)
    
    # Validate arguments
    if not args.demo and not args.live:
        print("\nPlease specify either --demo or --live mode\n")
        print("Example: python main.py --demo")
        print("         python main.py --live --duration 300\n")
        sys.exit(1)
    
    if args.live:
        print("\n" + "=" * 60)
        print("WARNING: LIVE TRADING MODE")
        print("=" * 60)
        print("This will execute REAL trades with REAL money!")
        print("Make sure you understand the risks before proceeding.")
        print("=" * 60 + "\n")
        
        # In a production system, you would add confirmation here
        # For safety, we'll exit unless explicitly confirmed
        response = input("Type 'CONFIRM' to proceed with live trading: ")
        if response != 'CONFIRM':
            print("Live trading cancelled.")
            sys.exit(0)
    
    # Create settings
    settings = create_settings(args)
    
    # Initialize bot
    bot = ArbitrageBot(settings=settings)
    
    try:
        if args.demo:
            logger.info("Starting in DEMO mode...")
            bot.run_demo(cycles=args.cycles)
        else:
            logger.info(f"Starting in LIVE mode for {args.duration or 'indefinite'} seconds...")
            bot.start(run_duration_seconds=args.duration)
    
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        sys.exit(1)
    finally:
        logger.info("Application shutdown complete")


if __name__ == '__main__':
    main()
