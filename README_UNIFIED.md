# 🚀 Unified Crypto Trading Application

A modern, all-in-one cryptocurrency trading application with a beautiful web dashboard, advanced technical analysis, and automated monitoring. Everything runs from a single Python file!

## ✨ Features

### 📊 **Real-Time Market Monitoring**
- Live cryptocurrency price tracking
- Multiple trading pairs (BTC, ETH, ADA, SOL, DOGE, LTC)
- 24-hour price change indicators
- Volume and market cap data

### 📈 **Advanced Technical Analysis**
- **RSI (Relative Strength Index)** - Overbought/oversold conditions
- **MACD (Moving Average Convergence Divergence)** - Trend momentum
- **Bollinger Bands** - Price volatility and support/resistance
- **Moving Averages (SMA)** - Trend direction analysis

### 🎯 **Intelligent Trading Signals**
- Automated signal generation (BUY/SELL/HOLD)
- Confidence scoring for each signal
- Multi-indicator analysis for accuracy
- Real-time signal alerts

### 💼 **Portfolio Management**
- Track your holdings and performance
- P&L calculations with percentages
- Position sizing and risk analysis
- Historical trade tracking

### 🔔 **Smart Alert System**
- Price movement alerts
- Technical indicator warnings
- Strong signal notifications
- Real-time dashboard notifications

### 🌐 **Beautiful Web Dashboard**
- Modern glass-morphism design
- Responsive layout for all devices
- Interactive charts with Plotly
- Real-time data updates
- Dark theme with gradient backgrounds

## 🚀 Quick Start

### Option 1: One-Click Launch
```bash
./launch.sh
```

### Option 2: Direct Python Execution
```bash
python3 crypto_app_unified.py
```

### Option 3: Background Service
```bash
nohup python3 crypto_app_unified.py &
```

## 📱 Accessing the Dashboard

Once started, open your browser to:
- **Local Access**: http://localhost:8080
- **Network Access**: http://your-ip:8080

The dashboard will automatically open in your default browser!

## 🛠️ Requirements

### Python Packages (Auto-installed)
- `flask` - Web framework
- `requests` - HTTP client
- `pandas` - Data analysis
- `numpy` - Numerical computing
- `plotly` - Interactive charts
- `schedule` - Task scheduling
- `yfinance` - Yahoo Finance API
- `websocket-client` - WebSocket support

### System Requirements
- Python 3.7+ 
- Internet connection
- Modern web browser

## 📊 Dashboard Overview

### 🏠 **Main Dashboard**
- **Market Overview**: Global crypto market statistics
- **Live Prices**: Real-time price cards with signals
- **Alerts Panel**: Important notifications and warnings
- **Interactive Charts**: Candlestick charts with technical indicators

### 📈 **Technical Analysis Section**
- **Price Chart**: Candlestick chart with moving averages
- **RSI Chart**: Overbought/oversold indicator (0-100 scale)
- **MACD Chart**: Trend momentum and signal crossovers
- **Bollinger Bands**: Volatility and price channels

### 💰 **Portfolio Section**
- **Holdings Summary**: Your current positions
- **P&L Tracking**: Profit/loss calculations
- **Recent Trades**: Transaction history
- **Performance Metrics**: Win rate and statistics

## 🔧 Configuration

The application includes built-in configuration that can be customized by editing the `Config` class in `crypto_app_unified.py`:

```python
@dataclass
class Config:
    # Trading pairs to monitor
    TRADING_PAIRS = ["BTC-USD", "ETH-USD", "ADA-USD", "SOL-USD", "DOGE-USD", "LTC-USD"]
    
    # Technical analysis settings
    RSI_PERIOD = 14
    RSI_OVERBOUGHT = 70
    RSI_OVERSOLD = 30
    
    # Web server settings
    HOST = "0.0.0.0"
    PORT = 8080
```

## 📡 API Endpoints

The application provides REST API endpoints:

- `GET /` - Main dashboard
- `GET /api/prices` - Live cryptocurrency prices
- `GET /api/alerts` - Recent alerts and notifications
- `GET /api/portfolio` - Portfolio summary
- `GET /api/signals` - Recent trading signals
- `GET /api/chart/{symbol}` - Chart data for specific symbol

## 🔄 Data Sources

- **Price Data**: Yahoo Finance (yfinance)
- **Market Data**: CoinGecko API
- **Technical Analysis**: Custom calculations
- **Storage**: SQLite database (local)

## 📊 Signal Generation Logic

The application uses a sophisticated scoring system:

1. **RSI Analysis**: Oversold (<30) = +2 points, Overbought (>70) = -2 points
2. **MACD Analysis**: Bullish crossover = +1 point, Bearish crossover = -1 point
3. **Moving Average**: Short MA > Long MA = +1 point (bullish trend)
4. **Bollinger Bands**: Price near lower band = +1 point (oversold)

**Signal Recommendations**:
- Score ≥ 3: **STRONG BUY**
- Score ≥ 1: **BUY**
- Score ≤ -3: **STRONG SELL** 
- Score ≤ -1: **SELL**
- Score = 0: **HOLD**

## 🔒 Security Features

- Secure session management
- Input validation and sanitization
- Rate limiting for API calls
- No external API keys required
- Local data storage only

## 📁 File Structure

```
crypto_app_unified.py    # Main application (everything in one file!)
launch.sh               # Easy launcher script
crypto_trading.db       # SQLite database (auto-created)
crypto_app.log          # Application logs
README_UNIFIED.md       # This documentation
```

## 🛡️ Risk Disclaimer

**⚠️ IMPORTANT**: This application is for educational and informational purposes only. 

- **Not Financial Advice**: Signals and analysis should not be considered financial advice
- **Do Your Research**: Always conduct your own analysis before making trades
- **Risk Management**: Never invest more than you can afford to lose
- **Market Volatility**: Cryptocurrency markets are highly volatile and unpredictable

## 🤝 Contributing

This is a single-file application designed for simplicity. To contribute:

1. Fork the repository
2. Make changes to `crypto_app_unified.py`
3. Test thoroughly
4. Submit a pull request

## 📝 License

Open source - feel free to modify and distribute!

## 🆘 Troubleshooting

### Common Issues:

**Port already in use**:
```bash
# Kill existing process
pkill -f crypto_app_unified.py
# Or use different port
python3 crypto_app_unified.py --port 8081
```

**Dependencies not installing**:
```bash
# Manual installation
pip3 install flask requests pandas numpy plotly schedule yfinance
```

**Database errors**:
```bash
# Remove and recreate database
rm crypto_trading.db
python3 crypto_app_unified.py
```

**Network access issues**:
- Check firewall settings
- Ensure port 8080 is open
- Try accessing via localhost first

## 📞 Support

For issues and questions:
1. Check the troubleshooting section above
2. Review the application logs (`crypto_app.log`)
3. Ensure all dependencies are installed
4. Check internet connectivity

## 🎉 What's New

### Version 2.0 Features:
- ✅ **Single File Application** - Everything in one Python file
- ✅ **Modern UI** - Glass-morphism design with gradients
- ✅ **Auto-Installation** - Dependencies install automatically
- ✅ **Real-Time Updates** - Dashboard refreshes every 30 seconds
- ✅ **Mobile Responsive** - Works on phones and tablets
- ✅ **Interactive Charts** - Zoom, pan, and hover for details
- ✅ **Smart Alerts** - Intelligent notification system
- ✅ **Portfolio Tracking** - Complete trading history
- ✅ **Background Monitoring** - Continuous market analysis
- ✅ **One-Click Launch** - Simple startup script

---

**🚀 Ready to start trading? Run `./launch.sh` and visit http://localhost:8080**
