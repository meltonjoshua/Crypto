# Crypto Trading Bot

A comprehensive cryptocurrency trading analysis software that provides buy/sell signals for Coinbase trading pairs.

## Features

- **Real-time Price Data**: Connects to Coinbase Pro API for live market data
- **Technical Analysis**: Multiple indicators including RSI, MACD, Moving Averages, Bollinger Bands
- **Trading Signals**: Automated buy/sell recommendations based on technical analysis
- **Web Dashboard**: Interactive dashboard for monitoring prices and signals
- **Risk Management**: Configurable stop-loss and take-profit levels
- **Alert System**: Email and console notifications for trading opportunities
- **Historical Analysis**: Backtesting capabilities for strategy validation

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd Crypto
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure your settings:
```bash
cp config/config.example.json config/config.json
```
Edit the config file with your preferences and API credentials.

## Usage

### Start the Trading Bot
```bash
python main.py
```

### Launch Web Dashboard
```bash
python dashboard.py
```
Then open http://localhost:8050 in your browser.

### Run Backtesting
```bash
python backtest.py --symbol BTC-USD --days 30
```

## Configuration

Edit `config/config.json` to customize:
- Trading pairs to monitor
- Technical indicator parameters
- Risk management settings
- Alert preferences
- API credentials (optional for live trading)

## Components

- `main.py` - Main trading bot application
- `dashboard.py` - Web-based monitoring dashboard
- `src/coinbase_client.py` - Coinbase API integration
- `src/technical_analysis.py` - Technical indicators and signals
- `src/trading_signals.py` - Buy/sell signal generation
- `src/risk_management.py` - Risk management logic
- `src/alerts.py` - Notification system
- `src/database.py` - Data storage and retrieval
- `backtest.py` - Strategy backtesting

## Disclaimer

This software is for educational and analysis purposes only. It does not execute actual trades automatically. Always do your own research and consider your risk tolerance before making any trading decisions.

## License

MIT License