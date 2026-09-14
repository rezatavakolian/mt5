# Forex Triangular Arbitrage Trading Bot

A professional-grade Python application for detecting and executing triangular arbitrage trades in the forex market using MetaTrader 5.

## Overview

This software monitors three currency pairs (EUR/USD, AUD/USD, EUR/AUD) for triangular arbitrage opportunities and automatically executes trades when profitable situations are detected.

### What is Triangular Arbitrage?

Triangular arbitrage exploits price discrepancies between three related currency pairs. For example:
- EUR/USD (Euro vs US Dollar)
- AUD/USD (Australian Dollar vs US Dollar)  
- EUR/AUD (Euro vs Australian Dollar)

The theoretical relationship is: EUR/AUD = EUR/USD ÷ AUD/USD

When market prices deviate from this relationship beyond transaction costs, an arbitrage opportunity exists.

## Project Structure

```
arbitrage_trader/
├── __init__.py              # Package initialization
├── main.py                  # Application entry point
├── arbitrage_bot.py         # Main bot orchestrator
├── config/
│   ├── __init__.py
│   └── settings.py          # Configuration classes
├── models/
│   ├── __init__.py
│   ├── price_data.py        # Price data model
│   └── arbitrage_opportunity.py  # Opportunity model
├── services/
│   ├── __init__.py
│   ├── mt4_service.py       # MetaTrader connection service
│   ├── market_data_service.py   # Market data management
│   ├── arbitrage_detector.py    # Opportunity detection
│   └── trade_executor.py        # Trade execution
└── utils/
    ├── __init__.py
    └── logger_setup.py      # Logging configuration
```

## Features

- **Real-time Price Monitoring**: Fetches live prices from MetaTrader
- **Triangular Arbitrage Detection**: Identifies profitable opportunities across EUR/USD, AUD/USD, EUR/AUD
- **Automatic Trade Execution**: Executes all three legs of the arbitrage simultaneously
- **Risk Management**: Configurable stop-loss, take-profit, and position limits
- **Simulation Mode**: Test strategies without real money
- **Comprehensive Logging**: Detailed logs for auditing and analysis
- **Graceful Shutdown**: Signal handling for safe termination

## Installation

### Prerequisites

- Python 3.8+
- MetaTrader 5 terminal installed (for live trading)
- Forex broker account with MT5 support

### Install Dependencies

```bash
pip install pandas numpy
pip install MetaTrader5  # Only if using live trading on Windows
```

Note: MetaTrader5 package is only available on Windows. The software includes a simulation mode for testing on other platforms.

## Configuration

### Default Account Settings

The demo account credentials you provided are pre-configured:

```python
Server: MetaQuotes-Demo
Login: 112605427
Password: *1ArTjSj
Investor: 6dO_PfId
```

### Trading Parameters

Default settings can be modified in `config/settings.py` or via command-line arguments:

- `lot_size`: 0.01 (trade size)
- `min_profit_threshold_pips`: 2.0 (minimum profit to trigger trade)
- `max_spread_threshold_pips`: 3.0 (maximum acceptable spread)
- `stop_loss_pips`: 10.0
- `take_profit_pips`: 15.0
- `check_interval_seconds`: 0.5 (scan frequency)

## Usage

### Demo Mode (Recommended for Testing)

Run simulated trades without risking real money:

```bash
cd /workspace
PYTHONPATH=/workspace python arbitrage_trader/main.py --demo --cycles 10
```

Options:
- `--cycles N`: Number of demo cycles to run
- `--log-level LEVEL`: DEBUG, INFO, WARNING, ERROR

### Live Trading Mode

⚠️ **WARNING**: This executes REAL trades with REAL money!

```bash
PYTHONPATH=/workspace python arbitrage_trader/main.py --live --duration 300
```

Options:
- `--duration SECONDS`: Trading duration (omit for indefinite)
- `--lot-size SIZE`: Trade lot size
- `--min-profit PIPS`: Minimum profit threshold

### Help

```bash
PYTHONPATH=/workspace python arbitrage_trader/main.py --help
```

## How It Works

### 1. Connection
The bot connects to MetaTrader 5 using your credentials and verifies the connection.

### 2. Price Collection
Fetches real-time bid/ask prices for all three currency pairs simultaneously.

### 3. Opportunity Detection
Calculates synthetic cross rates and compares them with actual market prices:

```
Synthetic EUR/AUD Bid = EUR/USD Bid ÷ AUD/USD Ask
Synthetic EUR/AUD Ask = EUR/USD Ask ÷ AUD/USD Bid
```

If the difference exceeds the minimum profit threshold (after accounting for spreads), an opportunity is flagged.

### 4. Trade Execution
When a valid opportunity is found, the bot executes three simultaneous trades:

**Strategy 1 (Buy Synthetic, Sell Actual):**
- BUY EUR/USD
- SELL AUD/USD
- SELL EUR/AUD

**Strategy 2 (Sell Synthetic, Buy Actual):**
- SELL EUR/USD
- BUY AUD/USD
- BUY EUR/AUD

### 5. Risk Management
Each trade leg includes:
- Stop-loss order (default: 10 pips)
- Take-profit order (default: 15 pips)
- Position size limits

## Architecture

The application follows clean architecture principles with separation of concerns:

- **Models**: Data structures (PriceData, ArbitrageOpportunity, TradeLeg)
- **Services**: Business logic (MT4Service, MarketDataService, ArbitrageDetector, TradeExecutor)
- **Config**: Configuration management
- **Utils**: Helper functions
- **Bot**: Orchestrates all services

## Logging

The application provides comprehensive logging:

```
2026-09-14 10:45:12,792 - arbitrage_trader.services.arbitrage_detector - INFO - Triangular arbitrage opportunity detected: 2.43 pips
Type: triangular
Symbols: EURUSD, AUDUSD, EURAUD
Expected Profit: 2.43 pips
Confidence: 36.27%
Legs: 3
```

Logs can be saved to a file:
```bash
PYTHONPATH=/workspace python arbitrage_trader/main.py --demo --log-file trading.log
```

## Important Considerations

### Latency
True arbitrage requires extremely low latency. This implementation is suitable for:
- Educational purposes
- Strategy research
- Low-frequency statistical arbitrage

For high-frequency arbitrage, you would need:
- Co-located servers near exchange matching engines
- Direct market access (DMA)
- Sub-millisecond execution infrastructure

### Market Reality
- True risk-free arbitrage opportunities are rare in modern forex markets
- Spreads and slippage can eliminate theoretical profits
- Execution risk: One leg may fill while others don't
- Broker restrictions: Some brokers prohibit arbitrage strategies

### Demo Account Limitations
- Demo prices may not reflect real market conditions
- Execution speeds differ from live trading
- No guarantee of similar performance with real money

## Disclaimer

⚠️ **Trading forex carries substantial risk of loss and is not suitable for all investors.**

This software is provided for educational and research purposes only. Past performance does not guarantee future results. Always test thoroughly in a demo environment before considering live trading.

The authors are not responsible for any financial losses incurred through the use of this software.

## License

This project is provided as-is for educational purposes.
