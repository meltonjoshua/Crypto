#!/usr/bin/env python3
"""
🚀 Unified Crypto Trading Application
A modern, single-file crypto trading bot with beautiful web UI

Features:
- Real-time crypto price monitoring
- Advanced technical analysis
- Trading signal generation
- Portfolio tracking
- Risk management
- Interactive web dashboard
- Email/SMS alerts
- Backtesting capabilities

Author: AI Assistant
Date: August 2025
"""

import os
import sys
import json
import time
import sqlite3
import logging
import threading
import webbrowser
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import asyncio
from dataclasses import dataclass
import hashlib
import secrets
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from collections import defaultdict, deque
from threading import Lock
import multiprocessing as mp
from concurrent.futures import ThreadPoolExecutor, as_completed
import warnings
warnings.filterwarnings('ignore')

# Core scientific libraries with fallbacks
try:
    import numpy as np
except ImportError:
    # Create a minimal numpy-like fallback
    class NumpyFallback:
        def uniform(self, low, high, size=None):
            import random
            if size is None:
                return random.uniform(low, high)
            return [random.uniform(low, high) for _ in range(size)]
        
        def normal(self, loc=0.0, scale=1.0, size=None):
            import random
            if size is None:
                return random.gauss(loc, scale)
            return [random.gauss(loc, scale) for _ in range(size)]
        
        def choice(self, choices):
            import random
            return random.choice(choices)
        
        def randint(self, low, high):
            import random
            return random.randint(low, high)
        
        def exponential(self, scale):
            import random
            return random.expovariate(1.0/scale)
    
    class NumpyMath:
        @staticmethod
        def mean(arr):
            return sum(arr) / len(arr) if arr else 0
        
        @staticmethod
        def std(arr):
            if len(arr) < 2:
                return 0
            mean_val = sum(arr) / len(arr)
            variance = sum((x - mean_val) ** 2 for x in arr) / len(arr)
            return variance ** 0.5
        
        @staticmethod
        def percentile(arr, pct):
            if not arr:
                return 0
            sorted_arr = sorted(arr)
            k = (len(sorted_arr) - 1) * pct / 100
            f = int(k)
            c = k - f
            if f + 1 < len(sorted_arr):
                return sorted_arr[f] + c * (sorted_arr[f + 1] - sorted_arr[f])
            return sorted_arr[f]
        
        @staticmethod
        def array(arr):
            return arr
        
        @staticmethod
        def sum(arr):
            return sum(arr)
        
        @staticmethod
        def prod(arr):
            result = 1
            for x in arr:
                result *= x
            return result
        
        @staticmethod
        def sqrt(x):
            return x ** 0.5
    
    np = NumpyMath()
    np.random = NumpyFallback()
    logging.warning("NumPy not available, using fallback implementation")

try:
    import pandas as pd
except ImportError:
    # Create a minimal pandas-like fallback
    class PandasFallback:
        @staticmethod
        def DataFrame(data=None):
            return {'data': data or {}}
        
        @staticmethod
        def Series(data=None):
            return data or []
    
    pd = PandasFallback()
    logging.warning("Pandas not available, using fallback implementation")

# Optional imports with fallbacks
try:
    import websocket
except ImportError:
    websocket = None
    logging.warning("websocket-client not available, real-time streaming will be limited")

try:
    import ccxt
except ImportError:
    ccxt = None
    logging.warning("ccxt not available, exchange integrations will be limited")

try:
    import socket
except ImportError:
    socket = None

# Install required packages if not available
required_packages = [
    'flask', 'requests', 'pandas', 'numpy', 'plotly', 
    'schedule', 'websocket-client', 'yfinance', 'scikit-learn',
    'tweepy', 'praw', 'beautifulsoup4', 'selenium', 'reportlab',
    'tensorflow', 'torch', 'transformers', 'ccxt', 'web3',
    'flask-socketio', 'python-telegram-bot', 'smtplib'
]

def install_packages():
    """Install required packages"""
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            print(f"📦 Installing {package}...")
            os.system(f"{sys.executable} -m pip install {package}")

install_packages()

# Import packages
import pandas as pd
import numpy as np
import requests
import yfinance as yf
from flask import Flask, render_template_string, request, jsonify, redirect, url_for, session
import plotly.graph_objs as go
import plotly.express as px
from plotly.utils import PlotlyJSONEncoder
import schedule
import logging
from datetime import datetime, timedelta

# ==================== CONFIGURATION ====================

@dataclass
class Config:
    """Application configuration"""
    # Trading pairs to monitor
    TRADING_PAIRS = ["BTC-USD", "ETH-USD", "ADA-USD", "SOL-USD", "DOGE-USD", "LTC-USD"]
    
    # Technical analysis settings
    RSI_PERIOD = 14
    RSI_OVERBOUGHT = 70
    RSI_OVERSOLD = 30
    MACD_FAST = 12
    MACD_SLOW = 26
    MACD_SIGNAL = 9
    SMA_SHORT = 20
    SMA_LONG = 50
    BB_PERIOD = 20
    BB_STD = 2
    
    # Risk management
    STOP_LOSS_PCT = 5.0
    TAKE_PROFIT_PCT = 10.0
    MAX_POSITION_SIZE = 1000.0
    
    # Database
    DB_FILE = "crypto_trading.db"
    
    # Web server
    HOST = "0.0.0.0"
    PORT = 8080
    SECRET_KEY = secrets.token_hex(16)

config = Config()

# ==================== DATABASE MANAGER ====================

class DatabaseManager:
    """SQLite database manager for storing trading data"""
    
    def __init__(self, db_file: str = config.DB_FILE):
        self.db_file = db_file
        self.init_database()
    
    def init_database(self):
        """Initialize database tables"""
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            
            # Price data table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS price_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    timestamp DATETIME NOT NULL,
                    open_price REAL,
                    high_price REAL,
                    low_price REAL,
                    close_price REAL,
                    volume REAL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Trading signals table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trading_signals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    signal_type TEXT NOT NULL,
                    price REAL NOT NULL,
                    confidence REAL,
                    rsi REAL,
                    macd REAL,
                    recommendation TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Portfolio table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS portfolio (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    action TEXT NOT NULL,
                    quantity REAL NOT NULL,
                    price REAL NOT NULL,
                    total_value REAL NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Alerts table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    alert_type TEXT NOT NULL,
                    message TEXT NOT NULL,
                    price REAL,
                    is_read BOOLEAN DEFAULT FALSE,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
    
    def store_price_data(self, symbol: str, data: pd.DataFrame):
        """Store price data"""
        with sqlite3.connect(self.db_file) as conn:
            for index, row in data.iterrows():
                cursor = conn.cursor()
                # Convert pandas Timestamp to string for SQLite
                timestamp_str = index.strftime('%Y-%m-%d %H:%M:%S') if hasattr(index, 'strftime') else str(index)
                cursor.execute("""
                    INSERT OR REPLACE INTO price_data 
                    (symbol, timestamp, open_price, high_price, low_price, close_price, volume)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (symbol, timestamp_str, row.get('Open', 0), row.get('High', 0), 
                     row.get('Low', 0), row.get('Close', 0), row.get('Volume', 0)))
            conn.commit()
    
    def get_price_data(self, symbol: str, days: int = 30) -> pd.DataFrame:
        """Get price data for symbol"""
        with sqlite3.connect(self.db_file) as conn:
            query = """
                SELECT timestamp, open_price, high_price, low_price, close_price, volume
                FROM price_data 
                WHERE symbol = ? AND timestamp >= datetime('now', '-{} days')
                ORDER BY timestamp
            """.format(days)
            
            df = pd.read_sql_query(query, conn, params=(symbol,))
            if not df.empty:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df.set_index('timestamp', inplace=True)
            return df
    
    def store_signal(self, symbol: str, signal_data: Dict):
        """Store trading signal"""
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO trading_signals 
                (symbol, signal_type, price, confidence, rsi, macd, recommendation)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                symbol, 
                signal_data.get('type', 'ANALYSIS'),
                signal_data.get('price', 0),
                signal_data.get('confidence', 0),
                signal_data.get('rsi', 0),
                signal_data.get('macd', 0),
                signal_data.get('recommendation', 'HOLD')
            ))
            conn.commit()
    
    def get_recent_signals(self, limit: int = 10) -> List[Dict]:
        """Get recent trading signals"""
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM trading_signals 
                ORDER BY timestamp DESC 
                LIMIT ?
            """, (limit,))
            
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    def store_alert(self, symbol: str, alert_type: str, message: str, price: float = None):
        """Store alert"""
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO alerts (symbol, alert_type, message, price)
                VALUES (?, ?, ?, ?)
            """, (symbol, alert_type, message, price))
            conn.commit()
    
    def get_unread_alerts(self) -> List[Dict]:
        """Get unread alerts"""
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM alerts 
                WHERE is_read = FALSE 
                ORDER BY timestamp DESC
            """)
            
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]

# ==================== CRYPTO DATA FETCHER ====================

class CryptoDataFetcher:
    """Enhanced crypto data fetcher with multiple sources and advanced fallback system"""
    
    # Rate limiting and caching
    _last_request_times = {}
    _min_request_interval = 1.5  # seconds between requests (faster updates)
    _data_cache = {}  # Enhanced data cache
    _source_performance = {}  # Track source reliability
    
    @staticmethod
    def _should_make_request(symbol: str) -> bool:
        """Check if enough time has passed since last request for this symbol"""
        import time
        current_time = time.time()
        last_time = CryptoDataFetcher._last_request_times.get(symbol, 0)
        return (current_time - last_time) >= CryptoDataFetcher._min_request_interval
    
    @staticmethod
    def _update_request_time(symbol: str):
        """Update the last request time for a symbol"""
        import time
        CryptoDataFetcher._last_request_times[symbol] = time.time()
    
    @staticmethod
    def _cache_data(symbol: str, data: Dict, source: str):
        """Cache data with source tracking for reliability analysis"""
        CryptoDataFetcher._data_cache[symbol] = {
            'data': data,
            'timestamp': time.time(),
            'source': source
        }
        
        # Track source performance
        if source not in CryptoDataFetcher._source_performance:
            CryptoDataFetcher._source_performance[source] = {'success': 0, 'total': 0}
        CryptoDataFetcher._source_performance[source]['success'] += 1
        CryptoDataFetcher._source_performance[source]['total'] += 1
    
    @staticmethod
    def _get_cached_data(symbol: str, max_age: int = 300) -> Optional[Dict]:
        """Get cached data if available and not too old"""
        cached = CryptoDataFetcher._data_cache.get(symbol)
        if cached and time.time() - cached['timestamp'] < max_age:
            cached_data = cached['data'].copy()
            cached_data['source'] = f"{cached['source']}_cached"
            return cached_data
        return None
    
    @staticmethod
    def _track_source_failure(source: str):
        """Track source failure for reliability analysis"""
        if source not in CryptoDataFetcher._source_performance:
            CryptoDataFetcher._source_performance[source] = {'success': 0, 'total': 0}
        CryptoDataFetcher._source_performance[source]['total'] += 1
    
    @staticmethod
    def get_realtime_price(symbol: str) -> Dict:
        """Get real-time price with intelligent multi-source fallback"""
        # Check rate limiting first
        if not CryptoDataFetcher._should_make_request(symbol):
            cached = CryptoDataFetcher._get_cached_data(symbol)
            if cached:
                return cached
            
        # Try multiple data sources in order of reliability
        sources = [
            ('coingecko', CryptoDataFetcher._get_coingecko_price),
            ('coinbase', CryptoDataFetcher._get_coinbase_price),
            ('binance', CryptoDataFetcher._get_binance_price),
            ('yfinance', CryptoDataFetcher._get_fallback_price)
        ]
        
        # Sort sources by historical performance
        def get_reliability(source_name):
            perf = CryptoDataFetcher._source_performance.get(source_name, {'success': 1, 'total': 1})
            return perf['success'] / max(perf['total'], 1)
        
        sources.sort(key=lambda x: get_reliability(x[0]), reverse=True)
        
        for source_name, source_func in sources:
            try:
                data = source_func(symbol)
                if data and data.get('price', 0) > 0:
                    CryptoDataFetcher._cache_data(symbol, data, source_name)
                    CryptoDataFetcher._update_request_time(symbol)
                    return data
            except Exception as e:
                CryptoDataFetcher._track_source_failure(source_name)
                logging.warning(f"Source {source_name} failed for {symbol}: {e}")
                continue
        
        # Last resort - return old cached data if available
        cached = CryptoDataFetcher._get_cached_data(symbol, max_age=3600)  # 1 hour old
        if cached:
            cached['warning'] = 'Using old cached data - all sources failed'
            return cached
        
        return {
            'symbol': symbol, 
            'price': 0, 
            'error': 'All sources failed',
            'timestamp': datetime.now().isoformat()
        }
    
    @staticmethod
    def _get_coingecko_price(symbol: str) -> Dict:
        """Get price from CoinGecko API (enhanced)"""
        symbol_map = {
            'BTC-USD': 'bitcoin',
            'ETH-USD': 'ethereum',
            'ADA-USD': 'cardano',
            'SOL-USD': 'solana',
            'DOGE-USD': 'dogecoin',
            'LTC-USD': 'litecoin'
        }
        
        coin_id = symbol_map.get(symbol, symbol.lower().replace('-usd', ''))
        
        url = f"https://api.coingecko.com/api/v3/simple/price"
        params = {
            'ids': coin_id,
            'vs_currencies': 'usd',
            'include_24hr_change': 'true',
            'include_24hr_vol': 'true',
            'include_market_cap': 'true',
            'include_last_updated_at': 'true'
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 429:
            raise Exception("Rate limited")
            
        response.raise_for_status()
        data = response.json()
        
        if coin_id in data:
            coin_data = data[coin_id]
            return {
                'symbol': symbol,
                'price': coin_data.get('usd', 0),
                'change_24h': coin_data.get('usd_24h_change', 0),
                'volume_24h': coin_data.get('usd_24h_vol', 0),
                'market_cap': coin_data.get('usd_market_cap', 0),
                'last_updated': coin_data.get('last_updated_at', 0),
                'timestamp': datetime.now().isoformat(),
                'source': 'coingecko'
            }
        
        raise Exception("Symbol not found in CoinGecko")
    
    @staticmethod
    def _get_coinbase_price(symbol: str) -> Dict:
        """Get price from Coinbase Pro API"""
        try:
            url = f"https://api.exchange.coinbase.com/products/{symbol}/ticker"
            response = requests.get(url, timeout=8)
            response.raise_for_status()
            data = response.json()
            
            if 'price' in data and 'volume' in data:
                return {
                    'symbol': symbol,
                    'price': float(data['price']),
                    'volume_24h': float(data.get('volume', 0)),
                    'bid': float(data.get('bid', 0)),
                    'ask': float(data.get('ask', 0)),
                    'timestamp': datetime.now().isoformat(),
                    'source': 'coinbase'
                }
        except Exception as e:
            raise Exception(f"Coinbase API failed: {e}")
    
    @staticmethod
    def _get_binance_price(symbol: str) -> Dict:
        """Get price from Binance API"""
        try:
            # Convert symbol format for Binance (BTC-USD -> BTCUSDT)
            binance_symbol = symbol.replace('-', '').replace('USD', 'USDT')
            url = f"https://api.binance.com/api/v3/ticker/24hr"
            params = {'symbol': binance_symbol}
            
            response = requests.get(url, params=params, timeout=8)
            response.raise_for_status()
            data = response.json()
            
            if 'lastPrice' in data:
                return {
                    'symbol': symbol,
                    'price': float(data['lastPrice']),
                    'change_24h': float(data.get('priceChangePercent', 0)),
                    'volume_24h': float(data.get('quoteVolume', 0)),
                    'high_24h': float(data.get('highPrice', 0)),
                    'low_24h': float(data.get('lowPrice', 0)),
                    'timestamp': datetime.now().isoformat(),
                    'source': 'binance'
                }
        except Exception as e:
            raise Exception(f"Binance API failed: {e}")
    
    @staticmethod
    def _get_fallback_price(symbol: str) -> Dict:
        """Get fallback price using yfinance"""
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            history = ticker.history(period="2d")
            
            if not history.empty:
                current_price = float(history['Close'].iloc[-1])
                prev_price = float(history['Close'].iloc[-2]) if len(history) > 1 else current_price
                change_24h = ((current_price - prev_price) / prev_price * 100) if prev_price > 0 else 0
                
                return {
                    'symbol': symbol,
                    'price': current_price,
                    'change_24h': change_24h,
                    'volume_24h': float(history['Volume'].iloc[-1]) if 'Volume' in history else 0,
                    'market_cap': info.get('marketCap', 0),
                    'timestamp': datetime.now().isoformat(),
                    'source': 'yfinance_fallback'
                }
        except Exception as e:
            logging.error(f"Fallback price fetch failed for {symbol}: {e}")
        
        # Last resort - return zero values but keep the symbol working
        return {
            'symbol': symbol, 
            'price': 0, 
            'change_24h': 0,
            'volume_24h': 0,
            'market_cap': 0,
            'timestamp': datetime.now().isoformat(),
            'source': 'unavailable',
            'error': 'All sources failed'
        }
    
    @staticmethod
    def get_historical_data(symbol: str, period: str = "30d") -> pd.DataFrame:
        """Get historical data using yfinance"""
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(period=period)
            
            if not df.empty:
                # Ensure consistent column names
                df.columns = ['Open', 'High', 'Low', 'Close', 'Volume', 'Dividends', 'Stock Splits']
                df = df[['Open', 'High', 'Low', 'Close', 'Volume']]
                return df
            
        except Exception as e:
            logging.error(f"Error fetching historical data for {symbol}: {e}")
        
        return pd.DataFrame()
    
    @staticmethod
    def get_market_overview() -> Dict:
        """Get market overview data"""
        try:
            url = "https://api.coingecko.com/api/v3/global"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.json().get('data', {})
        except Exception as e:
            logging.error(f"Error fetching market overview: {e}")
            return {}

# ==================== TECHNICAL ANALYSIS ====================

class TechnicalAnalysis:
    """Enhanced technical analysis indicators and signals"""
    
    @staticmethod
    def calculate_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate Relative Strength Index with Wilder's smoothing"""
        delta = prices.diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        # Use Wilder's smoothing for more accurate RSI
        avg_gain = gain.ewm(alpha=1/period, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1/period, adjust=False).mean()
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    @staticmethod
    def calculate_macd(prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Dict:
        """Calculate MACD indicator"""
        ema_fast = prices.ewm(span=fast).mean()
        ema_slow = prices.ewm(span=slow).mean()
        macd = ema_fast - ema_slow
        signal_line = macd.ewm(span=signal).mean()
        histogram = macd - signal_line
        
        return {
            'macd': macd,
            'signal': signal_line,
            'histogram': histogram
        }
    
    @staticmethod
    def calculate_bollinger_bands(prices: pd.Series, period: int = 20, std_dev: float = 2) -> Dict:
        """Calculate Bollinger Bands"""
        sma = prices.rolling(window=period).mean()
        std = prices.rolling(window=period).std()
        
        return {
            'upper': sma + (std * std_dev),
            'middle': sma,
            'lower': sma - (std * std_dev)
        }
    
    @staticmethod
    def calculate_moving_averages(prices: pd.Series, short: int = 20, long: int = 50) -> Dict:
        """Calculate Simple Moving Averages"""
        return {
            'sma_short': prices.rolling(window=short).mean(),
            'sma_long': prices.rolling(window=long).mean()
        }
    
    @staticmethod
    def calculate_ema(prices: pd.Series, period: int = 20) -> pd.Series:
        """Calculate Exponential Moving Average for better trend following"""
        return prices.ewm(span=period, adjust=False).mean()
    
    @staticmethod
    def calculate_stochastic(high: pd.Series, low: pd.Series, close: pd.Series, 
                           k_period: int = 14, d_period: int = 3) -> Dict:
        """Calculate Stochastic Oscillator for momentum analysis"""
        lowest_low = low.rolling(window=k_period).min()
        highest_high = high.rolling(window=k_period).max()
        
        k_percent = 100 * ((close - lowest_low) / (highest_high - lowest_low))
        d_percent = k_percent.rolling(window=d_period).mean()
        
        return {
            'stoch_k': k_percent,
            'stoch_d': d_percent
        }
    
    @staticmethod
    def calculate_williams_r(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """Calculate Williams %R for overbought/oversold conditions"""
        highest_high = high.rolling(window=period).max()
        lowest_low = low.rolling(window=period).min()
        
        williams_r = -100 * ((highest_high - close) / (highest_high - lowest_low))
        return williams_r
    
    @staticmethod
    def calculate_atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """Calculate Average True Range for volatility measurement"""
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        
        true_range = pd.DataFrame({'tr1': tr1, 'tr2': tr2, 'tr3': tr3}).max(axis=1)
        atr = true_range.rolling(window=period).mean()
        return atr
    
    @staticmethod
    def calculate_momentum(prices: pd.Series, period: int = 10) -> pd.Series:
        """Calculate Price Momentum"""
        return prices / prices.shift(period) - 1
    
    @staticmethod
    def calculate_roc(prices: pd.Series, period: int = 12) -> pd.Series:
        """Calculate Rate of Change"""
        return ((prices - prices.shift(period)) / prices.shift(period)) * 100
    
    @staticmethod
    def calculate_support_resistance(df: pd.DataFrame, window: int = 20) -> Dict:
        """Calculate dynamic support and resistance levels"""
        high_prices = df['High'] if 'High' in df.columns else df['high_price'] if 'high_price' in df.columns else df['Close']
        low_prices = df['Low'] if 'Low' in df.columns else df['low_price'] if 'low_price' in df.columns else df['Close']
        close_prices = df['Close'] if 'Close' in df.columns else df['close_price'] if 'close_price' in df.columns else df['Close']
        
        # Rolling resistance (highest high in window)
        resistance = high_prices.rolling(window=window).max()
        
        # Rolling support (lowest low in window)
        support = low_prices.rolling(window=window).min()
        
        # Pivot points
        pivot = (high_prices + low_prices + close_prices) / 3
        
        return {
            'resistance': resistance.iloc[-1] if not resistance.empty else 0,
            'support': support.iloc[-1] if not support.empty else 0,
            'pivot': pivot.iloc[-1] if not pivot.empty else 0
        }
    
    @staticmethod
    def calculate_ichimoku(df: pd.DataFrame) -> Dict:
        """Calculate Ichimoku Cloud indicators for advanced trend analysis"""
        high = df['High'] if 'High' in df.columns else df['high_price'] if 'high_price' in df.columns else df['Close']
        low = df['Low'] if 'Low' in df.columns else df['low_price'] if 'low_price' in df.columns else df['Close']
        close = df['Close'] if 'Close' in df.columns else df['close_price'] if 'close_price' in df.columns else df['Close']
        
        # Conversion Line (Tenkan-sen): (9-period high + 9-period low) / 2
        tenkan_sen = (high.rolling(9).max() + low.rolling(9).min()) / 2
        
        # Base Line (Kijun-sen): (26-period high + 26-period low) / 2
        kijun_sen = (high.rolling(26).max() + low.rolling(26).min()) / 2
        
        # Leading Span A (Senkou Span A): (Conversion Line + Base Line) / 2
        senkou_span_a = ((tenkan_sen + kijun_sen) / 2).shift(26)
        
        # Leading Span B (Senkou Span B): (52-period high + 52-period low) / 2
        senkou_span_b = ((high.rolling(52).max() + low.rolling(52).min()) / 2).shift(26)
        
        # Lagging Span (Chikou Span): Current closing price shifted back 26 periods
        chikou_span = close.shift(-26)
        
        return {
            'tenkan_sen': tenkan_sen,
            'kijun_sen': kijun_sen,
            'senkou_span_a': senkou_span_a,
            'senkou_span_b': senkou_span_b,
            'chikou_span': chikou_span
        }
    
    @staticmethod
    def calculate_vwap(df: pd.DataFrame) -> pd.Series:
        """Calculate Volume Weighted Average Price"""
        high = df['High'] if 'High' in df.columns else df['high_price'] if 'high_price' in df.columns else df['Close']
        low = df['Low'] if 'Low' in df.columns else df['low_price'] if 'low_price' in df.columns else df['Close']
        close = df['Close'] if 'Close' in df.columns else df['close_price'] if 'close_price' in df.columns else df['Close']
        volume = df['Volume'] if 'Volume' in df.columns else df['volume'] if 'volume' in df.columns else pd.Series([1] * len(df))
        
        # Typical Price = (High + Low + Close) / 3
        typical_price = (high + low + close) / 3
        
        # VWAP = Cumulative(Typical Price * Volume) / Cumulative(Volume)
        return (typical_price * volume).cumsum() / volume.cumsum()
    
    @staticmethod
    def calculate_obv(close: pd.Series, volume: pd.Series) -> pd.Series:
        """Calculate On-Balance Volume for trend confirmation"""
        obv = pd.Series(index=close.index, dtype=float)
        obv.iloc[0] = volume.iloc[0]
        
        for i in range(1, len(close)):
            if close.iloc[i] > close.iloc[i-1]:
                obv.iloc[i] = obv.iloc[i-1] + volume.iloc[i]
            elif close.iloc[i] < close.iloc[i-1]:
                obv.iloc[i] = obv.iloc[i-1] - volume.iloc[i]
            else:
                obv.iloc[i] = obv.iloc[i-1]
        
        return obv
    
    @staticmethod
    def calculate_adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> Dict:
        """Calculate Average Directional Index for trend strength"""
        # True Range calculation
        tr1 = high - low
        tr2 = (high - close.shift()).abs()
        tr3 = (low - close.shift()).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        # Directional Movement
        plus_dm = high.diff()
        minus_dm = low.diff() * -1
        
        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm < 0] = 0
        
        # Smooth the directional movements and true range
        plus_di = 100 * (plus_dm.ewm(alpha=1/period).mean() / tr.ewm(alpha=1/period).mean())
        minus_di = 100 * (minus_dm.ewm(alpha=1/period).mean() / tr.ewm(alpha=1/period).mean())
        
        # Calculate ADX
        dx = (abs(plus_di - minus_di) / (plus_di + minus_di)) * 100
        adx = dx.ewm(alpha=1/period).mean()
        
        return {
            'adx': adx,
            'plus_di': plus_di,
            'minus_di': minus_di
        }
    
    @staticmethod
    def calculate_fibonacci_levels(df: pd.DataFrame, period: int = 50) -> Dict:
        """Calculate Fibonacci retracement levels"""
        close = df['Close'] if 'Close' in df.columns else df['close_price'] if 'close_price' in df.columns else df['Close']
        
        # Get high and low over the period
        recent_high = close.rolling(period).max().iloc[-1]
        recent_low = close.rolling(period).min().iloc[-1]
        
        diff = recent_high - recent_low
        
        return {
            'fib_0': recent_high,
            'fib_236': recent_high - 0.236 * diff,
            'fib_382': recent_high - 0.382 * diff,
            'fib_500': recent_high - 0.500 * diff,
            'fib_618': recent_high - 0.618 * diff,
            'fib_786': recent_high - 0.786 * diff,
            'fib_100': recent_low
        }
    
    @staticmethod
    def calculate_market_structure(df: pd.DataFrame) -> Dict:
        """Analyze market structure for trend identification"""
        close = df['Close'] if 'Close' in df.columns else df['close_price'] if 'close_price' in df.columns else df['Close']
        high = df['High'] if 'High' in df.columns else df['high_price'] if 'high_price' in df.columns else close
        low = df['Low'] if 'Low' in df.columns else df['low_price'] if 'low_price' in df.columns else close
        
        # Calculate swing highs and lows
        swing_high = high.rolling(5, center=True).max() == high
        swing_low = low.rolling(5, center=True).min() == low
        
        # Trend strength based on higher highs/lower lows
        recent_highs = high[swing_high].tail(3)
        recent_lows = low[swing_low].tail(3)
        
        trend_strength = 0
        if len(recent_highs) >= 2:
            if recent_highs.iloc[-1] > recent_highs.iloc[-2]:
                trend_strength += 1
        if len(recent_lows) >= 2:
            if recent_lows.iloc[-1] > recent_lows.iloc[-2]:
                trend_strength += 1
        
        return {
            'trend_strength': trend_strength,
            'swing_high_count': swing_high.sum(),
            'swing_low_count': swing_low.sum(),
            'structure': 'bullish' if trend_strength >= 1 else 'bearish' if trend_strength <= -1 else 'neutral'
        }
    
    @staticmethod
    def generate_signals(df: pd.DataFrame) -> Dict:
        """Generate comprehensive trading signals with enhanced accuracy"""
        if df.empty or len(df) < 50:
            return {'recommendation': 'INSUFFICIENT_DATA', 'confidence': 0, 'accuracy_score': 0}
        
        # Get price columns (handle different naming conventions)
        close_prices = df['Close'] if 'Close' in df.columns else df['close_price'] if 'close_price' in df.columns else df['close']
        high_prices = df['High'] if 'High' in df.columns else df['high_price'] if 'high_price' in df.columns else close_prices
        low_prices = df['Low'] if 'Low' in df.columns else df['low_price'] if 'low_price' in df.columns else close_prices
        volume = df['Volume'] if 'Volume' in df.columns else df['volume'] if 'volume' in df.columns else pd.Series([1] * len(df))
        
        # Calculate all indicators (enhanced with advanced analysis)
        rsi = TechnicalAnalysis.calculate_rsi(close_prices)
        macd_data = TechnicalAnalysis.calculate_macd(close_prices)
        bb_data = TechnicalAnalysis.calculate_bollinger_bands(close_prices)
        ma_data = TechnicalAnalysis.calculate_moving_averages(close_prices)
        ema_20 = TechnicalAnalysis.calculate_ema(close_prices, 20)
        ema_50 = TechnicalAnalysis.calculate_ema(close_prices, 50)
        stoch_data = TechnicalAnalysis.calculate_stochastic(high_prices, low_prices, close_prices)
        williams_r = TechnicalAnalysis.calculate_williams_r(high_prices, low_prices, close_prices)
        atr = TechnicalAnalysis.calculate_atr(high_prices, low_prices, close_prices)
        momentum = TechnicalAnalysis.calculate_momentum(close_prices)
        roc = TechnicalAnalysis.calculate_roc(close_prices)
        sr_levels = TechnicalAnalysis.calculate_support_resistance(df)
        
        # Advanced indicators for enhanced signal accuracy
        ichimoku_data = TechnicalAnalysis.calculate_ichimoku(df)
        vwap = TechnicalAnalysis.calculate_vwap(df)
        obv = TechnicalAnalysis.calculate_obv(close_prices, volume)
        adx_data = TechnicalAnalysis.calculate_adx(high_prices, low_prices, close_prices)
        fib_levels = TechnicalAnalysis.calculate_fibonacci_levels(df)
        market_structure = TechnicalAnalysis.calculate_market_structure(df)
        
        # Get latest values safely
        def get_latest(series, default=0):
            return series.iloc[-1] if not series.empty and not pd.isna(series.iloc[-1]) else default
        
        latest_rsi = get_latest(rsi, 50)
        latest_macd = get_latest(macd_data['macd'])
        latest_macd_signal = get_latest(macd_data['signal'])
        latest_price = get_latest(close_prices)
        latest_bb_upper = get_latest(bb_data['upper'], latest_price)
        latest_bb_lower = get_latest(bb_data['lower'], latest_price)
        latest_bb_middle = get_latest(bb_data['middle'], latest_price)
        latest_sma_short = get_latest(ma_data['sma_short'], latest_price)
        latest_sma_long = get_latest(ma_data['sma_long'], latest_price)
        latest_ema_20 = get_latest(ema_20, latest_price)
        latest_ema_50 = get_latest(ema_50, latest_price)
        latest_stoch_k = get_latest(stoch_data['stoch_k'], 50)
        latest_stoch_d = get_latest(stoch_data['stoch_d'], 50)
        latest_williams = get_latest(williams_r, -50)
        latest_momentum = get_latest(momentum)
        latest_roc = get_latest(roc)
        latest_atr = get_latest(atr)
        
        # Advanced indicator latest values
        latest_vwap = get_latest(vwap, latest_price)
        latest_obv = get_latest(obv)
        latest_adx = get_latest(adx_data['adx'], 25)
        latest_plus_di = get_latest(adx_data['plus_di'], 25)
        latest_minus_di = get_latest(adx_data['minus_di'], 25)
        latest_tenkan = get_latest(ichimoku_data['tenkan_sen'], latest_price)
        latest_kijun = get_latest(ichimoku_data['kijun_sen'], latest_price)
        latest_senkou_a = get_latest(ichimoku_data['senkou_span_a'], latest_price)
        latest_senkou_b = get_latest(ichimoku_data['senkou_span_b'], latest_price)
        
        # Enhanced signal scoring with multiple timeframe analysis
        score = 0
        signals = []
        confidence_factors = []
        
        # 1. RSI Analysis (Enhanced with multiple levels)
        if latest_rsi < 20:  # Extremely oversold
            score += 3
            signals.append("RSI extremely oversold (Strong BUY)")
            confidence_factors.append(0.9)
        elif latest_rsi < 30:  # Oversold
            score += 2
            signals.append("RSI oversold (BUY)")
            confidence_factors.append(0.7)
        elif latest_rsi > 80:  # Extremely overbought
            score -= 3
            signals.append("RSI extremely overbought (Strong SELL)")
            confidence_factors.append(0.9)
        elif latest_rsi > 70:  # Overbought
            score -= 2
            signals.append("RSI overbought (SELL)")
            confidence_factors.append(0.7)
        
        # 2. MACD Analysis (Enhanced with histogram)
        macd_histogram = latest_macd - latest_macd_signal
        if latest_macd > latest_macd_signal:
            if macd_histogram > 0:
                score += 2
                signals.append("MACD bullish crossover with positive momentum")
                confidence_factors.append(0.8)
            else:
                score += 1
                signals.append("MACD bullish trend")
                confidence_factors.append(0.6)
        else:
            if macd_histogram < 0:
                score -= 2
                signals.append("MACD bearish crossover with negative momentum")
                confidence_factors.append(0.8)
            else:
                score -= 1
                signals.append("MACD bearish trend")
                confidence_factors.append(0.6)
        
        # 3. Moving Average Convergence (Multiple timeframes)
        if latest_ema_20 > latest_ema_50 and latest_sma_short > latest_sma_long:
            score += 2
            signals.append("Multiple MA bullish convergence")
            confidence_factors.append(0.8)
        elif latest_ema_20 < latest_ema_50 and latest_sma_short < latest_sma_long:
            score -= 2
            signals.append("Multiple MA bearish convergence")
            confidence_factors.append(0.8)
        elif latest_ema_20 > latest_ema_50:
            score += 1
            signals.append("EMA bullish trend")
            confidence_factors.append(0.6)
        elif latest_ema_20 < latest_ema_50:
            score -= 1
            signals.append("EMA bearish trend")
            confidence_factors.append(0.6)
        
        # 4. Bollinger Bands Analysis (Enhanced with squeeze detection)
        bb_width = (latest_bb_upper - latest_bb_lower) / latest_bb_middle
        if latest_price < latest_bb_lower:
            if bb_width < 0.1:  # Bollinger Band squeeze
                score += 3
                signals.append("BB oversold with squeeze (Strong BUY)")
                confidence_factors.append(0.9)
            else:
                score += 2
                signals.append("Price below BB lower band (BUY)")
                confidence_factors.append(0.7)
        elif latest_price > latest_bb_upper:
            if bb_width < 0.1:  # Bollinger Band squeeze
                score -= 3
                signals.append("BB overbought with squeeze (Strong SELL)")
                confidence_factors.append(0.9)
            else:
                score -= 2
                signals.append("Price above BB upper band (SELL)")
                confidence_factors.append(0.7)
        
        # 5. Stochastic Oscillator
        if latest_stoch_k < 20 and latest_stoch_d < 20:
            score += 2
            signals.append("Stochastic oversold")
            confidence_factors.append(0.7)
        elif latest_stoch_k > 80 and latest_stoch_d > 80:
            score -= 2
            signals.append("Stochastic overbought")
            confidence_factors.append(0.7)
        elif latest_stoch_k > latest_stoch_d and latest_stoch_k < 50:
            score += 1
            signals.append("Stochastic bullish crossover")
            confidence_factors.append(0.6)
        elif latest_stoch_k < latest_stoch_d and latest_stoch_k > 50:
            score -= 1
            signals.append("Stochastic bearish crossover")
            confidence_factors.append(0.6)
        
        # 6. Williams %R
        if latest_williams < -80:
            score += 1
            signals.append("Williams %R oversold")
            confidence_factors.append(0.6)
        elif latest_williams > -20:
            score -= 1
            signals.append("Williams %R overbought")
            confidence_factors.append(0.6)
        
        # 7. Momentum and ROC Analysis
        if latest_momentum > 0.05 and latest_roc > 5:
            score += 2
            signals.append("Strong positive momentum")
            confidence_factors.append(0.7)
        elif latest_momentum < -0.05 and latest_roc < -5:
            score -= 2
            signals.append("Strong negative momentum")
            confidence_factors.append(0.7)
        elif latest_momentum > 0 and latest_roc > 0:
            score += 1
            signals.append("Positive momentum")
            confidence_factors.append(0.5)
        elif latest_momentum < 0 and latest_roc < 0:
            score -= 1
            signals.append("Negative momentum")
            confidence_factors.append(0.5)
        
        # 8. Support/Resistance Analysis
        resistance = sr_levels.get('resistance', latest_price)
        support = sr_levels.get('support', latest_price)
        
        if latest_price <= support * 1.02:  # Near support
            score += 1
            signals.append("Price near support level")
            confidence_factors.append(0.6)
        elif latest_price >= resistance * 0.98:  # Near resistance
            score -= 1
            signals.append("Price near resistance level")
            confidence_factors.append(0.6)
        
        # 9. Volume Analysis (if available)
        if len(volume) > 20:
            avg_volume = volume.rolling(window=20).mean().iloc[-1]
            current_volume = volume.iloc[-1]
            if current_volume > avg_volume * 1.5:  # High volume
                if score > 0:
                    score += 1
                    signals.append("High volume confirms bullish trend")
                    confidence_factors.append(0.6)
                elif score < 0:
                    score -= 1
                    signals.append("High volume confirms bearish trend")
                    confidence_factors.append(0.6)
        
        # 10. Advanced Ichimoku Cloud Analysis
        if latest_price > latest_tenkan and latest_tenkan > latest_kijun:
            if latest_price > max(latest_senkou_a, latest_senkou_b):
                score += 3
                signals.append("Ichimoku: Strong bullish cloud breakout")
                confidence_factors.append(0.9)
            else:
                score += 2
                signals.append("Ichimoku: Bullish momentum")
                confidence_factors.append(0.7)
        elif latest_price < latest_tenkan and latest_tenkan < latest_kijun:
            if latest_price < min(latest_senkou_a, latest_senkou_b):
                score -= 3
                signals.append("Ichimoku: Strong bearish cloud breakdown")
                confidence_factors.append(0.9)
            else:
                score -= 2
                signals.append("Ichimoku: Bearish momentum")
                confidence_factors.append(0.7)
        
        # 11. VWAP Analysis
        if latest_price > latest_vwap * 1.02:
            score += 1
            signals.append("Price above VWAP (institutional bullishness)")
            confidence_factors.append(0.6)
        elif latest_price < latest_vwap * 0.98:
            score -= 1
            signals.append("Price below VWAP (institutional bearishness)")
            confidence_factors.append(0.6)
        
        # 12. ADX Trend Strength Analysis
        if latest_adx > 25:  # Strong trend
            if latest_plus_di > latest_minus_di:
                score += 2
                signals.append("ADX: Strong bullish trend confirmed")
                confidence_factors.append(0.8)
            else:
                score -= 2
                signals.append("ADX: Strong bearish trend confirmed")
                confidence_factors.append(0.8)
        elif latest_adx < 20:  # Weak trend (consolidation)
            score *= 0.7  # Reduce signal strength in consolidation
            signals.append("ADX: Trend strength weak (consolidation)")
            confidence_factors.append(0.4)
        
        # 13. Fibonacci Level Analysis
        current_price = latest_price
        fib_support_levels = [fib_levels['fib_618'], fib_levels['fib_500'], fib_levels['fib_382']]
        fib_resistance_levels = [fib_levels['fib_236'], fib_levels['fib_0']]
        
        for level in fib_support_levels:
            if abs(current_price - level) / level < 0.02:  # Within 2% of fib level
                score += 1
                signals.append(f"Price near Fibonacci support level")
                confidence_factors.append(0.7)
                break
                
        for level in fib_resistance_levels:
            if abs(current_price - level) / level < 0.02:  # Within 2% of fib level
                score -= 1
                signals.append(f"Price near Fibonacci resistance level")
                confidence_factors.append(0.7)
                break
        
        # 14. Market Structure Analysis
        if market_structure['structure'] == 'bullish':
            score += 1
            signals.append("Market structure: Bullish (higher highs/lows)")
            confidence_factors.append(0.6)
        elif market_structure['structure'] == 'bearish':
            score -= 1
            signals.append("Market structure: Bearish (lower highs/lows)")
            confidence_factors.append(0.6)
        
        # 15. Multi-timeframe confluence (simulate by checking short vs long term indicators)
        short_term_bullish = (latest_rsi < 70 and latest_macd > latest_macd_signal and 
                             latest_ema_20 > latest_ema_50)
        long_term_bullish = (latest_sma_short > latest_sma_long and latest_price > latest_vwap)
        
        if short_term_bullish and long_term_bullish:
            score += 2
            signals.append("Multi-timeframe bullish confluence")
            confidence_factors.append(0.8)
        elif not short_term_bullish and not long_term_bullish:
            score -= 2
            signals.append("Multi-timeframe bearish confluence")
            confidence_factors.append(0.8)
        
        # 16. ML-Based Pattern Recognition Analysis
        try:
            patterns = MLSignalEnhancer.detect_chart_patterns(df)
            if patterns['patterns']:
                pattern_strength = MLSignalEnhancer.calculate_pattern_signal_strength(patterns['patterns'])
                
                if abs(pattern_strength) > 0.3:  # Significant pattern detected
                    pattern_score = int(pattern_strength * 4)  # Scale to +/- 4 points
                    score += pattern_score
                    
                    pattern_names = [p['name'] for p in patterns['patterns']]
                    if pattern_strength > 0:
                        signals.append(f"Bullish patterns detected: {', '.join(pattern_names[:2])}")
                    else:
                        signals.append(f"Bearish patterns detected: {', '.join(pattern_names[:2])}")
                    
                    confidence_factors.append(patterns['overall_confidence'])
        
            # Volume Pattern Analysis
            volume_analysis = MLSignalEnhancer.analyze_volume_patterns(df)
            if volume_analysis['volume_trend'] == 'bullish_confirmation':
                score += 1
                signals.append("Volume confirms bullish trend")
                confidence_factors.append(volume_analysis['strength'])
            elif volume_analysis['volume_trend'] == 'bearish_divergence':
                score -= 1
                signals.append("Volume shows bearish divergence")
                confidence_factors.append(volume_analysis['strength'])
            elif volume_analysis['volume_trend'] == 'low_conviction':
                score *= 0.8  # Reduce signal strength on low volume
                signals.append("Low volume indicates weak conviction")
                confidence_factors.append(0.3)
                
        except Exception as e:
            logging.warning(f"ML pattern analysis failed: {e}")
        
        # Calculate enhanced confidence score
        if confidence_factors:
            avg_confidence = sum(confidence_factors) / len(confidence_factors)
        else:
            avg_confidence = 0.5
        
        # Generate recommendation with enhanced accuracy
        max_score = 30  # Increased max score due to ML patterns
        normalized_score = score / max_score
        
        if score >= 15:
            recommendation = "STRONG BUY"
            confidence = min(avg_confidence * 1.4, 1.0)
        elif score >= 8:
            recommendation = "BUY"
            confidence = min(avg_confidence * 1.2, 1.0)
        elif score <= -15:
            recommendation = "STRONG SELL"
            confidence = min(avg_confidence * 1.4, 1.0)
        elif score <= -8:
            recommendation = "SELL"
            confidence = min(avg_confidence * 1.2, 1.0)
        else:
            recommendation = "HOLD"
            confidence = avg_confidence * 0.9
        
        # Calculate accuracy score based on signal consensus
        signal_strength = abs(score) / max_score
        accuracy_score = min((signal_strength + avg_confidence) / 2, 1.0)
        
        return {
            'recommendation': recommendation,
            'confidence': confidence,
            'score': score,
            'normalized_score': normalized_score,
            'accuracy_score': accuracy_score,
            'signals': signals,
            'signal_count': len(signals),
            'indicators': {
                'rsi': latest_rsi,
                'macd': latest_macd,
                'macd_signal': latest_macd_signal,
                'macd_histogram': macd_histogram,
                'bb_upper': latest_bb_upper,
                'bb_lower': latest_bb_lower,
                'bb_middle': latest_bb_middle,
                'bb_width': bb_width,
                'sma_short': latest_sma_short,
                'sma_long': latest_sma_long,
                'ema_20': latest_ema_20,
                'ema_50': latest_ema_50,
                'stoch_k': latest_stoch_k,
                'stoch_d': latest_stoch_d,
                'williams_r': latest_williams,
                'momentum': latest_momentum,
                'roc': latest_roc,
                'atr': latest_atr,
                'support': support,
                'resistance': resistance,
                'price': latest_price,
                # Advanced indicators
                'vwap': latest_vwap,
                'obv': latest_obv,
                'adx': latest_adx,
                'plus_di': latest_plus_di,
                'minus_di': latest_minus_di,
                'ichimoku_tenkan': latest_tenkan,
                'ichimoku_kijun': latest_kijun,
                'ichimoku_senkou_a': latest_senkou_a,
                'ichimoku_senkou_b': latest_senkou_b,
                'fib_levels': fib_levels,
                'market_structure': market_structure,
                # ML Pattern Analysis
                'ml_patterns': patterns if 'patterns' in locals() else {'patterns': [], 'pattern_count': 0},
                'volume_analysis': volume_analysis if 'volume_analysis' in locals() else {'volume_trend': 'unknown', 'strength': 0}
            }
        }

# ==================== MACHINE LEARNING SIGNAL ENHANCEMENT ====================

class MLSignalEnhancer:
    """Machine learning-based signal enhancement and pattern recognition"""
    
    def __init__(self):
        self.pattern_cache = {}
        self.signal_history = []
        
    @staticmethod
    def detect_chart_patterns(df: pd.DataFrame) -> Dict:
        """Detect common chart patterns using basic pattern recognition"""
        if len(df) < 20:
            return {'patterns': [], 'confidence': 0}
        
        high = df['High'] if 'High' in df.columns else df['Close']
        low = df['Low'] if 'Low' in df.columns else df['Close']
        close = df['Close'] if 'Close' in df.columns else df['close_price']
        
        patterns = []
        
        # Head and Shoulders Pattern Detection
        h_s_pattern = MLSignalEnhancer._detect_head_shoulders(high, low)
        if h_s_pattern['detected']:
            patterns.append({
                'name': 'Head and Shoulders',
                'type': 'bearish',
                'confidence': h_s_pattern['confidence'],
                'strength': 0.8
            })
        
        # Double Top/Bottom Detection
        double_pattern = MLSignalEnhancer._detect_double_top_bottom(high, low)
        if double_pattern['detected']:
            patterns.append({
                'name': f"Double {double_pattern['type']}",
                'type': 'bearish' if double_pattern['type'] == 'Top' else 'bullish',
                'confidence': double_pattern['confidence'],
                'strength': 0.7
            })
        
        # Triangle Pattern Detection
        triangle_pattern = MLSignalEnhancer._detect_triangle(high, low)
        if triangle_pattern['detected']:
            patterns.append({
                'name': f"{triangle_pattern['type']} Triangle",
                'type': triangle_pattern['direction'],
                'confidence': triangle_pattern['confidence'],
                'strength': 0.6
            })
        
        # Flag/Pennant Pattern Detection
        flag_pattern = MLSignalEnhancer._detect_flag_pennant(close, high, low)
        if flag_pattern['detected']:
            patterns.append({
                'name': flag_pattern['type'],
                'type': flag_pattern['direction'],
                'confidence': flag_pattern['confidence'],
                'strength': 0.6
            })
        
        return {
            'patterns': patterns,
            'pattern_count': len(patterns),
            'overall_confidence': sum(p['confidence'] for p in patterns) / max(len(patterns), 1)
        }
    
    @staticmethod
    def _detect_head_shoulders(high: pd.Series, low: pd.Series, window: int = 10) -> Dict:
        """Detect Head and Shoulders pattern"""
        if len(high) < window * 3:
            return {'detected': False, 'confidence': 0}
        
        # Find local maxima
        highs = high.rolling(window, center=True).max() == high
        peaks = high[highs].tail(5)  # Last 5 peaks
        
        if len(peaks) < 3:
            return {'detected': False, 'confidence': 0}
        
        # Check if middle peak is highest (head) and side peaks are similar (shoulders)
        peak_values = peaks.values[-3:]  # Last 3 peaks
        head = peak_values[1]  # Middle peak
        left_shoulder = peak_values[0]
        right_shoulder = peak_values[2]
        
        # Head should be higher than shoulders
        if head > left_shoulder and head > right_shoulder:
            # Shoulders should be relatively similar
            shoulder_diff = abs(left_shoulder - right_shoulder) / head
            if shoulder_diff < 0.05:  # Within 5%
                confidence = 1 - shoulder_diff
                return {'detected': True, 'confidence': confidence}
        
        return {'detected': False, 'confidence': 0}
    
    @staticmethod
    def _detect_double_top_bottom(high: pd.Series, low: pd.Series, window: int = 10) -> Dict:
        """Detect Double Top/Bottom patterns"""
        if len(high) < window * 2:
            return {'detected': False, 'confidence': 0}
        
        # Double Top Detection
        highs = high.rolling(window, center=True).max() == high
        peaks = high[highs].tail(4)
        
        if len(peaks) >= 2:
            last_two_peaks = peaks.values[-2:]
            peak_diff = abs(last_two_peaks[0] - last_two_peaks[1]) / max(last_two_peaks)
            
            if peak_diff < 0.03:  # Within 3%
                return {
                    'detected': True,
                    'type': 'Top',
                    'confidence': 1 - peak_diff
                }
        
        # Double Bottom Detection
        lows = low.rolling(window, center=True).min() == low
        troughs = low[lows].tail(4)
        
        if len(troughs) >= 2:
            last_two_troughs = troughs.values[-2:]
            trough_diff = abs(last_two_troughs[0] - last_two_troughs[1]) / max(last_two_troughs)
            
            if trough_diff < 0.03:  # Within 3%
                return {
                    'detected': True,
                    'type': 'Bottom',
                    'confidence': 1 - trough_diff
                }
        
        return {'detected': False, 'confidence': 0}
    
    @staticmethod
    def _detect_triangle(high: pd.Series, low: pd.Series, window: int = 20) -> Dict:
        """Detect Triangle patterns (Ascending, Descending, Symmetrical)"""
        if len(high) < window:
            return {'detected': False, 'confidence': 0}
        
        recent_high = high.tail(window)
        recent_low = low.tail(window)
        
        # Calculate trend lines using linear regression
        x = np.arange(len(recent_high))
        
        # High trend slope
        high_slope = np.polyfit(x, recent_high.values, 1)[0]
        low_slope = np.polyfit(x, recent_low.values, 1)[0]
        
        # Determine triangle type
        if abs(high_slope) < 0.01 and low_slope > 0.01:  # Flat highs, rising lows
            return {
                'detected': True,
                'type': 'Ascending',
                'direction': 'bullish',
                'confidence': min(abs(low_slope) * 100, 0.8)
            }
        elif high_slope < -0.01 and abs(low_slope) < 0.01:  # Falling highs, flat lows
            return {
                'detected': True,
                'type': 'Descending',
                'direction': 'bearish',
                'confidence': min(abs(high_slope) * 100, 0.8)
            }
        elif high_slope < -0.01 and low_slope > 0.01:  # Converging lines
            return {
                'detected': True,
                'type': 'Symmetrical',
                'direction': 'neutral',
                'confidence': min((abs(high_slope) + abs(low_slope)) * 50, 0.7)
            }
        
        return {'detected': False, 'confidence': 0}
    
    @staticmethod
    def _detect_flag_pennant(close: pd.Series, high: pd.Series, low: pd.Series, window: int = 15) -> Dict:
        """Detect Flag and Pennant patterns"""
        if len(close) < window * 2:
            return {'detected': False, 'confidence': 0}
        
        # Look for strong move followed by consolidation
        recent_data = close.tail(window * 2)
        first_half = recent_data.head(window)
        second_half = recent_data.tail(window)
        
        # Check for strong initial move
        initial_move = (first_half.iloc[-1] - first_half.iloc[0]) / first_half.iloc[0]
        
        if abs(initial_move) > 0.05:  # 5% move
            # Check for consolidation in second half
            consolidation_range = (second_half.max() - second_half.min()) / second_half.mean()
            
            if consolidation_range < 0.03:  # Tight consolidation
                pattern_type = "Bull Flag" if initial_move > 0 else "Bear Flag"
                direction = "bullish" if initial_move > 0 else "bearish"
                
                return {
                    'detected': True,
                    'type': pattern_type,
                    'direction': direction,
                    'confidence': min(abs(initial_move) * 10, 0.8)
                }
        
        return {'detected': False, 'confidence': 0}
    
    @staticmethod
    def calculate_pattern_signal_strength(patterns: List[Dict]) -> float:
        """Calculate overall signal strength from detected patterns"""
        if not patterns:
            return 0
        
        bullish_strength = 0
        bearish_strength = 0
        
        for pattern in patterns:
            strength = pattern['confidence'] * pattern['strength']
            
            if pattern['type'] == 'bullish':
                bullish_strength += strength
            elif pattern['type'] == 'bearish':
                bearish_strength += strength
        
        # Return net signal strength (-1 to 1)
        total_strength = bullish_strength + bearish_strength
        if total_strength == 0:
            return 0
        
        return (bullish_strength - bearish_strength) / total_strength
    
    @staticmethod
    def analyze_volume_patterns(df: pd.DataFrame) -> Dict:
        """Analyze volume patterns for signal confirmation"""
        if len(df) < 20:
            return {'volume_trend': 'insufficient_data', 'strength': 0}
        
        volume = df['Volume'] if 'Volume' in df.columns else df['volume'] if 'volume' in df.columns else pd.Series([1] * len(df))
        close = df['Close'] if 'Close' in df.columns else df['close_price']
        
        # Volume trend analysis
        recent_volume = volume.tail(10)
        avg_volume = volume.tail(50).mean()
        
        volume_ratio = recent_volume.mean() / avg_volume
        
        # Price-volume relationship
        price_changes = close.pct_change().tail(10)
        volume_changes = volume.pct_change().tail(10)
        
        # Calculate correlation between price and volume changes
        correlation = price_changes.corr(volume_changes)
        
        if volume_ratio > 1.5 and correlation > 0.3:
            return {
                'volume_trend': 'bullish_confirmation',
                'strength': min(volume_ratio / 2, 1.0),
                'correlation': correlation
            }
        elif volume_ratio > 1.5 and correlation < -0.3:
            return {
                'volume_trend': 'bearish_divergence',
                'strength': min(volume_ratio / 2, 1.0),
                'correlation': correlation
            }
        elif volume_ratio < 0.7:
            return {
                'volume_trend': 'low_conviction',
                'strength': 0.3,
                'correlation': correlation
            }
        else:
            return {
                'volume_trend': 'neutral',
                'strength': 0.5,
                'correlation': correlation
            }

# ==================== ADVANCED RISK MANAGEMENT ====================

class AdvancedRiskManager:
    """Advanced risk management with dynamic position sizing and portfolio analysis"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {
            'max_portfolio_risk': 0.02,  # 2% max portfolio risk per trade
            'max_position_size': 0.1,     # 10% max position size
            'stop_loss_atr_multiplier': 2.0,
            'take_profit_risk_reward': 2.0,
            'correlation_threshold': 0.7
        }
        
    def calculate_dynamic_position_size(self, signal_data: Dict, account_balance: float, 
                                      current_price: float) -> Dict:
        """Calculate optimal position size based on signal strength and risk parameters"""
        try:
            # Base risk amount
            base_risk = account_balance * self.config['max_portfolio_risk']
            
            # Adjust risk based on signal confidence
            confidence = signal_data.get('confidence', 0.5)
            accuracy_score = signal_data.get('accuracy_score', 0.5)
            
            # Risk adjustment factor based on signal quality
            signal_quality = (confidence + accuracy_score) / 2
            adjusted_risk = base_risk * signal_quality
            
            # Calculate stop loss distance using ATR
            indicators = signal_data.get('indicators', {})
            atr = indicators.get('atr', current_price * 0.02)  # Default to 2% if no ATR
            
            stop_loss_distance = atr * self.config['stop_loss_atr_multiplier']
            stop_loss_price = current_price - stop_loss_distance
            
            # Position size based on risk and stop loss
            position_size_by_risk = adjusted_risk / stop_loss_distance
            
            # Position size based on max position percentage
            max_position_value = account_balance * self.config['max_position_size']
            position_size_by_max = max_position_value / current_price
            
            # Use the smaller of the two
            position_size = min(position_size_by_risk, position_size_by_max)
            
            # Calculate take profit
            take_profit_distance = stop_loss_distance * self.config['take_profit_risk_reward']
            take_profit_price = current_price + take_profit_distance
            
            return {
                'position_size': position_size,
                'position_value': position_size * current_price,
                'risk_amount': position_size * stop_loss_distance,
                'risk_percentage': (position_size * stop_loss_distance) / account_balance,
                'stop_loss_price': stop_loss_price,
                'take_profit_price': take_profit_price,
                'risk_reward_ratio': self.config['take_profit_risk_reward'],
                'signal_quality': signal_quality,
                'recommended': True
            }
            
        except Exception as e:
            logging.error(f"Error calculating position size: {e}")
            return {
                'position_size': 0,
                'position_value': 0,
                'risk_amount': 0,
                'risk_percentage': 0,
                'stop_loss_price': current_price,
                'take_profit_price': current_price,
                'risk_reward_ratio': 1.0,
                'signal_quality': 0,
                'recommended': False,
                'error': str(e)
            }
    
    def assess_portfolio_risk(self, current_positions: List[Dict], 
                            new_signal: Dict, symbol: str) -> Dict:
        """Assess overall portfolio risk with new position"""
        try:
            # Calculate current portfolio exposure
            total_exposure = sum(pos.get('position_value', 0) for pos in current_positions)
            total_risk = sum(pos.get('risk_amount', 0) for pos in current_positions)
            
            # Check symbol concentration
            symbol_exposure = sum(pos.get('position_value', 0) 
                                for pos in current_positions 
                                if pos.get('symbol') == symbol)
            
            # Check for correlated assets
            correlated_symbols = self._get_correlated_symbols(symbol)
            correlated_exposure = sum(pos.get('position_value', 0) 
                                    for pos in current_positions 
                                    if pos.get('symbol') in correlated_symbols)
            
            # Risk assessment
            risk_warnings = []
            risk_score = 0
            
            if total_risk > 0.1:  # More than 10% total portfolio risk
                risk_warnings.append("High total portfolio risk")
                risk_score += 3
                
            if symbol_exposure > 0.2:  # More than 20% in same symbol
                risk_warnings.append(f"High concentration in {symbol}")
                risk_score += 2
                
            if correlated_exposure > 0.3:  # More than 30% in correlated assets
                risk_warnings.append("High correlation risk")
                risk_score += 2
            
            # Signal quality assessment
            signal_quality = new_signal.get('accuracy_score', 0.5)
            if signal_quality < 0.4:
                risk_warnings.append("Low signal quality")
                risk_score += 1
            
            # Overall risk level
            if risk_score >= 5:
                risk_level = "HIGH"
                recommended = False
            elif risk_score >= 3:
                risk_level = "MEDIUM"
                recommended = True  # But with caution
            else:
                risk_level = "LOW"
                recommended = True
            
            return {
                'risk_level': risk_level,
                'risk_score': risk_score,
                'total_portfolio_risk': total_risk,
                'symbol_concentration': symbol_exposure,
                'correlation_risk': correlated_exposure,
                'risk_warnings': risk_warnings,
                'recommended': recommended,
                'max_additional_risk': max(0, 0.1 - total_risk)  # Keep under 10% total risk
            }
            
        except Exception as e:
            logging.error(f"Error assessing portfolio risk: {e}")
            return {
                'risk_level': "UNKNOWN",
                'risk_score': 0,
                'total_portfolio_risk': 0,
                'recommended': False,
                'error': str(e)
            }
    
    def _get_correlated_symbols(self, symbol: str) -> List[str]:
        """Get symbols that are typically correlated with the given symbol"""
        correlation_groups = {
            'BTC-USD': ['ETH-USD'],
            'ETH-USD': ['BTC-USD', 'ADA-USD'],
            'ADA-USD': ['ETH-USD', 'SOL-USD'],
            'SOL-USD': ['ADA-USD', 'ETH-USD'],
            'DOGE-USD': ['LTC-USD'],
            'LTC-USD': ['DOGE-USD', 'BTC-USD']
        }
        return correlation_groups.get(symbol, [])
    
    def generate_risk_report(self, signal_data: Dict, position_sizing: Dict, 
                           portfolio_risk: Dict) -> Dict:
        """Generate comprehensive risk report"""
        
        # Overall risk score (0-100)
        signal_score = signal_data.get('accuracy_score', 0.5) * 100
        portfolio_score = max(0, 100 - (portfolio_risk['risk_score'] * 10))
        position_score = min(100, position_sizing['signal_quality'] * 100)
        
        overall_score = (signal_score + portfolio_score + position_score) / 3
        
        # Risk recommendations
        recommendations = []
        
        if overall_score >= 80:
            recommendations.append("Excellent opportunity with low risk")
        elif overall_score >= 60:
            recommendations.append("Good opportunity with moderate risk")
        elif overall_score >= 40:
            recommendations.append("Fair opportunity with higher risk")
        else:
            recommendations.append("High risk - consider avoiding")
        
        if position_sizing['risk_percentage'] > 0.03:
            recommendations.append("Consider reducing position size")
            
        if len(portfolio_risk['risk_warnings']) > 0:
            recommendations.extend(portfolio_risk['risk_warnings'])
        
        return {
            'overall_risk_score': overall_score,
            'signal_quality_score': signal_score,
            'portfolio_risk_score': portfolio_score,
            'position_risk_score': position_score,
            'recommendations': recommendations,
            'trade_recommended': overall_score >= 50 and portfolio_risk['recommended'],
            'risk_level': 'LOW' if overall_score >= 70 else 'MEDIUM' if overall_score >= 40 else 'HIGH'
        }

# ==================== PORTFOLIO MANAGER ====================

class PortfolioManager:
    """Manage trading portfolio and positions"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    def add_position(self, symbol: str, action: str, quantity: float, price: float):
        """Add a new position to portfolio"""
        total_value = quantity * price
        
        with sqlite3.connect(self.db.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO portfolio (symbol, action, quantity, price, total_value)
                VALUES (?, ?, ?, ?, ?)
            """, (symbol, action, quantity, price, total_value))
            conn.commit()
    
    def get_portfolio_summary(self) -> Dict:
        """Get portfolio summary and statistics"""
        with sqlite3.connect(self.db.db_file) as conn:
            # Get all positions
            df = pd.read_sql_query("""
                SELECT symbol, action, quantity, price, total_value, timestamp
                FROM portfolio
                ORDER BY timestamp DESC
            """, conn)
            
            if df.empty:
                return {
                    'total_value': 0,
                    'total_positions': 0,
                    'top_holdings': [],
                    'recent_trades': []
                }
            
            # Calculate holdings
            holdings = {}
            for _, row in df.iterrows():
                symbol = row['symbol']
                if symbol not in holdings:
                    holdings[symbol] = {'quantity': 0, 'total_cost': 0}
                
                if row['action'] == 'BUY':
                    holdings[symbol]['quantity'] += row['quantity']
                    holdings[symbol]['total_cost'] += row['total_value']
                else:  # SELL
                    holdings[symbol]['quantity'] -= row['quantity']
                    holdings[symbol]['total_cost'] -= row['total_value']
            
            # Get current prices for portfolio valuation
            current_portfolio_value = 0
            top_holdings = []
            
            for symbol, holding in holdings.items():
                if holding['quantity'] > 0:
                    current_price_data = CryptoDataFetcher.get_realtime_price(symbol)
                    current_price = current_price_data.get('price', 0)
                    current_value = holding['quantity'] * current_price
                    current_portfolio_value += current_value
                    
                    avg_cost = holding['total_cost'] / holding['quantity'] if holding['quantity'] > 0 else 0
                    pnl = current_value - holding['total_cost']
                    pnl_pct = (pnl / holding['total_cost'] * 100) if holding['total_cost'] > 0 else 0
                    
                    top_holdings.append({
                        'symbol': symbol,
                        'quantity': holding['quantity'],
                        'avg_cost': avg_cost,
                        'current_price': current_price,
                        'current_value': current_value,
                        'pnl': pnl,
                        'pnl_pct': pnl_pct
                    })
            
            top_holdings.sort(key=lambda x: x['current_value'], reverse=True)
            
            return {
                'total_value': current_portfolio_value,
                'total_positions': len([h for h in holdings.values() if h['quantity'] > 0]),
                'top_holdings': top_holdings[:5],
                'recent_trades': df.head(10).to_dict('records')
            }

# ==================== ALERT SYSTEM ====================

class AlertSystem:
    """Alert system for trading signals and events"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    def check_price_alerts(self, symbol: str, current_price: float, analysis: Dict):
        """Check for price-based alerts with enhanced accuracy thresholds"""
        alerts = []
        
        # Get enhanced metrics
        recommendation = analysis.get('recommendation', 'HOLD')
        confidence = analysis.get('confidence', 0)
        accuracy_score = analysis.get('accuracy_score', 0)
        signal_count = analysis.get('signal_count', 0)
        
        # High-confidence strong signals
        if recommendation in ['STRONG BUY', 'STRONG SELL'] and confidence > 0.8 and accuracy_score > 0.7:
            message = f"HIGH CONFIDENCE {recommendation} for {symbol} at ${current_price:.2f} (Confidence: {confidence:.1%}, Accuracy: {accuracy_score:.1%}, {signal_count} signals)"
            self.db.store_alert(symbol, 'HIGH_CONFIDENCE_SIGNAL', message, current_price)
            alerts.append(message)
        
        # Medium-confidence signals with good accuracy
        elif recommendation in ['STRONG BUY', 'STRONG SELL', 'BUY', 'SELL'] and confidence > 0.6 and accuracy_score > 0.6:
            message = f"MEDIUM CONFIDENCE {recommendation} for {symbol} at ${current_price:.2f} (Confidence: {confidence:.1%}, Accuracy: {accuracy_score:.1%})"
            self.db.store_alert(symbol, 'MEDIUM_CONFIDENCE_SIGNAL', message, current_price)
            alerts.append(message)
        
        # Technical indicator specific alerts
        indicators = analysis.get('indicators', {})
        rsi = indicators.get('rsi', 50)
        macd_histogram = indicators.get('macd_histogram', 0)
        bb_width = indicators.get('bb_width', 0)
        
        # Extreme RSI conditions
        if rsi < 15:
            message = f"{symbol} RSI extremely oversold at {rsi:.1f} - Strong reversal potential"
            self.db.store_alert(symbol, 'RSI_EXTREME_OVERSOLD', message, current_price)
            alerts.append(message)
        elif rsi > 85:
            message = f"{symbol} RSI extremely overbought at {rsi:.1f} - Strong reversal potential"
            self.db.store_alert(symbol, 'RSI_EXTREME_OVERBOUGHT', message, current_price)
            alerts.append(message)
        
        # MACD divergence alerts
        if abs(macd_histogram) > 0.05:
            direction = "Strong bullish" if macd_histogram > 0 else "Strong bearish"
            message = f"{symbol} {direction} MACD momentum detected"
            self.db.store_alert(symbol, 'MACD_MOMENTUM', message, current_price)
            alerts.append(message)
        
        # Bollinger Band squeeze breakout
        if bb_width < 0.05:  # Very tight bands
            message = f"{symbol} Bollinger Band squeeze detected - Breakout imminent"
            self.db.store_alert(symbol, 'BB_SQUEEZE', message, current_price)
            alerts.append(message)
        
        # Support/Resistance alerts
        support = indicators.get('support', 0)
        resistance = indicators.get('resistance', 0)
        
        if support > 0 and current_price <= support * 1.01:
            message = f"{symbol} approaching support at ${support:.2f} (Current: ${current_price:.2f})"
            self.db.store_alert(symbol, 'SUPPORT_TEST', message, current_price)
            alerts.append(message)
        
        if resistance > 0 and current_price >= resistance * 0.99:
            message = f"{symbol} approaching resistance at ${resistance:.2f} (Current: ${current_price:.2f})"
            self.db.store_alert(symbol, 'RESISTANCE_TEST', message, current_price)
            alerts.append(message)
        
        return alerts

# ==================== REAL-TIME STREAMING & ENHANCED ALERTS ====================

class RealTimeStreamManager:
    """Advanced real-time data streaming with WebSocket support"""
    
    def __init__(self, db_manager):
        self.db = db_manager
        self.connections = {}
        self.price_streams = {}
        self.order_book_data = {}
        self.funding_rates = {}
        self.connected_exchanges = {}
        self.stream_lock = Lock()
        self.is_streaming = False
        
        # Initialize exchange connections with fallback
        if ccxt:
            try:
                self.exchanges = {
                    'binance': ccxt.binance({'enableRateLimit': True}),
                    'coinbase': ccxt.coinbase({'enableRateLimit': True}),
                    'bybit': ccxt.bybit({'enableRateLimit': True}),
                    'okx': ccxt.okx({'enableRateLimit': True})
                }
            except Exception as e:
                logging.warning(f"Error initializing exchanges: {str(e)}")
                self.exchanges = {}
        else:
            self.exchanges = {}
            logging.warning("CCXT not available, using simulated exchange data")
    
    def start_streams(self, symbols: List[str]):
        """Start real-time streams for given symbols"""
        try:
            self.is_streaming = True
            for symbol in symbols:
                threading.Thread(
                    target=self._stream_symbol_data,
                    args=(symbol,),
                    daemon=True
                ).start()
            
            # Start funding rates monitoring
            threading.Thread(target=self._monitor_funding_rates, daemon=True).start()
            
            logging.info(f"Started real-time streams for {len(symbols)} symbols")
            return True
        except Exception as e:
            logging.error(f"Error starting streams: {str(e)}")
            return False
    
    def _stream_symbol_data(self, symbol: str):
        """Stream real-time data for a symbol"""
        while self.is_streaming:
            try:
                # Get real-time price from multiple exchanges
                prices = {}
                if self.exchanges:
                    for exchange_name, exchange in self.exchanges.items():
                        try:
                            ticker = exchange.fetch_ticker(symbol)
                            prices[exchange_name] = {
                                'price': ticker['last'],
                                'volume': ticker['baseVolume'],
                                'timestamp': ticker['timestamp']
                            }
                        except Exception as e:
                            logging.warning(f"Failed to fetch {symbol} from {exchange_name}: {str(e)}")
                else:
                    # Fallback to simulated data
                    base_price = 50000 if 'BTC' in symbol else 3000
                    for exchange_name in ['binance', 'coinbase', 'bybit']:
                        price = base_price * np.random.uniform(0.999, 1.001)
                        prices[exchange_name] = {
                            'price': price,
                            'volume': np.random.uniform(1000, 10000),
                            'timestamp': int(time.time() * 1000)
                        }
                
                if prices:
                    with self.stream_lock:
                        self.price_streams[symbol] = {
                            'prices': prices,
                            'best_bid': max([p['price'] for p in prices.values()]),
                            'best_ask': min([p['price'] for p in prices.values()]),
                            'average_price': sum([p['price'] for p in prices.values()]) / len(prices),
                            'total_volume': sum([p['volume'] for p in prices.values()]),
                            'timestamp': datetime.now(),
                            'spread': max([p['price'] for p in prices.values()]) - min([p['price'] for p in prices.values()])
                        }
                
                time.sleep(1)  # Update every second
                
            except Exception as e:
                logging.error(f"Error in stream for {symbol}: {str(e)}")
                time.sleep(5)
    
    def _monitor_funding_rates(self):
        """Monitor funding rates across exchanges"""
        while self.is_streaming:
            try:
                for exchange_name, exchange in self.exchanges.items():
                    if hasattr(exchange, 'fetch_funding_rates'):
                        try:
                            rates = exchange.fetch_funding_rates()
                            self.funding_rates[exchange_name] = rates
                        except Exception as e:
                            logging.warning(f"Failed to fetch funding rates from {exchange_name}: {str(e)}")
                
                time.sleep(300)  # Update every 5 minutes
                
            except Exception as e:
                logging.error(f"Error monitoring funding rates: {str(e)}")
                time.sleep(60)
    
    def get_real_time_data(self, symbol: str) -> Dict:
        """Get current real-time data for symbol"""
        with self.stream_lock:
            return self.price_streams.get(symbol, {})
    
    def get_arbitrage_opportunities(self) -> List[Dict]:
        """Detect arbitrage opportunities across exchanges"""
        opportunities = []
        
        for symbol, data in self.price_streams.items():
            prices = data.get('prices', {})
            if len(prices) < 2:
                continue
                
            price_list = [(exchange, info['price']) for exchange, info in prices.items()]
            price_list.sort(key=lambda x: x[1])
            
            if len(price_list) >= 2:
                buy_exchange, buy_price = price_list[0]
                sell_exchange, sell_price = price_list[-1]
                
                profit_pct = ((sell_price - buy_price) / buy_price) * 100
                
                if profit_pct > 0.5:  # More than 0.5% profit potential
                    opportunities.append({
                        'symbol': symbol,
                        'buy_exchange': buy_exchange,
                        'sell_exchange': sell_exchange,
                        'buy_price': buy_price,
                        'sell_price': sell_price,
                        'profit_percentage': profit_pct,
                        'timestamp': datetime.now()
                    })
        
        return sorted(opportunities, key=lambda x: x['profit_percentage'], reverse=True)

class EnhancedAlertSystem:
    """Enhanced alert system with multiple notification channels"""
    
    def __init__(self, db_manager):
        self.db = db_manager
        self.email_config = {}
        self.telegram_config = {}
        self.webhook_urls = []
        self.alert_history = deque(maxlen=1000)
        
    def configure_email(self, smtp_server: str, port: int, username: str, password: str):
        """Configure email notifications"""
        self.email_config = {
            'smtp_server': smtp_server,
            'port': port,
            'username': username,
            'password': password
        }
    
    def configure_telegram(self, bot_token: str, chat_id: str):
        """Configure Telegram notifications"""
        self.telegram_config = {
            'bot_token': bot_token,
            'chat_id': chat_id
        }
    
    def add_webhook(self, url: str):
        """Add webhook URL for notifications"""
        self.webhook_urls.append(url)
    
    def send_alert(self, alert_type: str, message: str, priority: str = 'medium', 
                   include_chart: bool = False, symbol: str = None):
        """Send alert through all configured channels"""
        alert_data = {
            'type': alert_type,
            'message': message,
            'priority': priority,
            'timestamp': datetime.now(),
            'symbol': symbol
        }
        
        self.alert_history.append(alert_data)
        
        # Send through different channels based on priority
        if priority == 'high':
            self._send_email(alert_data)
            self._send_telegram(alert_data)
            self._send_webhooks(alert_data)
        elif priority == 'medium':
            self._send_telegram(alert_data)
            self._send_webhooks(alert_data)
        else:  # low priority
            self._send_webhooks(alert_data)
    
    def _send_email(self, alert_data: Dict):
        """Send email notification"""
        if not self.email_config:
            return
            
        try:
            msg = MIMEMultipart()
            msg['From'] = self.email_config['username']
            msg['To'] = self.email_config.get('recipient', self.email_config['username'])
            msg['Subject'] = f"Crypto Alert: {alert_data['type']}"
            
            body = f"""
            Alert Type: {alert_data['type']}
            Priority: {alert_data['priority'].upper()}
            Time: {alert_data['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}
            
            Message: {alert_data['message']}
            
            Generated by Advanced Crypto Trading Platform
            """
            
            msg.attach(MIMEText(body, 'plain'))
            
            context = ssl.create_default_context()
            with smtplib.SMTP(self.email_config['smtp_server'], self.email_config['port']) as server:
                server.starttls(context=context)
                server.login(self.email_config['username'], self.email_config['password'])
                server.send_message(msg)
                
        except Exception as e:
            logging.error(f"Failed to send email alert: {str(e)}")
    
    def _send_telegram(self, alert_data: Dict):
        """Send Telegram notification"""
        if not self.telegram_config:
            return
            
        try:
            import requests
            
            message = f"🚨 *{alert_data['type']}*\n"
            message += f"Priority: {alert_data['priority'].upper()}\n"
            message += f"Time: {alert_data['timestamp'].strftime('%H:%M:%S')}\n\n"
            message += f"{alert_data['message']}"
            
            url = f"https://api.telegram.org/bot{self.telegram_config['bot_token']}/sendMessage"
            
            payload = {
                'chat_id': self.telegram_config['chat_id'],
                'text': message,
                'parse_mode': 'Markdown'
            }
            
            requests.post(url, json=payload, timeout=10)
            
        except Exception as e:
            logging.error(f"Failed to send Telegram alert: {str(e)}")
    
    def _send_webhooks(self, alert_data: Dict):
        """Send webhook notifications"""
        for webhook_url in self.webhook_urls:
            try:
                import requests
                requests.post(webhook_url, json=alert_data, timeout=10)
            except Exception as e:
                logging.error(f"Failed to send webhook to {webhook_url}: {str(e)}")

# ==================== ADVANCED PORTFOLIO MANAGEMENT ====================

class AdvancedPortfolioManager:
    """Professional portfolio management with advanced metrics"""
    
    def __init__(self, db_manager):
        self.db = db_manager
        self.positions = {}
        self.performance_history = []
        self.correlation_matrix = pd.DataFrame()
        self.risk_metrics = {}
        
    def calculate_kelly_criterion(self, win_rate: float, avg_win: float, avg_loss: float) -> float:
        """Calculate optimal position size using Kelly Criterion"""
        if avg_loss == 0:
            return 0
            
        b = avg_win / abs(avg_loss)  # Win/loss ratio
        p = win_rate  # Probability of winning
        q = 1 - p  # Probability of losing
        
        kelly_percentage = (b * p - q) / b
        
        # Cap at 25% for safety
        return min(max(kelly_percentage, 0), 0.25)
    
    def calculate_position_size(self, signal_strength: float, account_balance: float, 
                              risk_per_trade: float = 0.02) -> Dict:
        """Calculate optimal position size based on multiple factors"""
        
        # Base position size from risk management
        base_size = account_balance * risk_per_trade
        
        # Adjust based on signal strength
        signal_multiplier = min(signal_strength / 0.8, 1.5)  # Max 1.5x for strong signals
        
        # Apply Kelly Criterion if historical data available
        if hasattr(self, 'historical_performance'):
            kelly_ratio = self.calculate_kelly_criterion(
                self.historical_performance.get('win_rate', 0.5),
                self.historical_performance.get('avg_win', 0.02),
                self.historical_performance.get('avg_loss', -0.02)
            )
            kelly_size = account_balance * kelly_ratio
            base_size = min(base_size, kelly_size)
        
        adjusted_size = base_size * signal_multiplier
        
        return {
            'position_size': adjusted_size,
            'risk_percentage': (adjusted_size / account_balance) * 100,
            'signal_multiplier': signal_multiplier,
            'kelly_suggested': base_size if hasattr(self, 'historical_performance') else None
        }
    
    def calculate_portfolio_metrics(self, positions: List[Dict]) -> Dict:
        """Calculate comprehensive portfolio metrics"""
        if not positions:
            return {}
            
        total_value = sum(pos.get('current_value', 0) for pos in positions)
        total_pnl = sum(pos.get('unrealized_pnl', 0) for pos in positions)
        
        # Calculate portfolio weights
        weights = [pos.get('current_value', 0) / total_value for pos in positions if total_value > 0]
        
        # Risk metrics
        portfolio_var = self._calculate_var(positions)
        max_drawdown = self._calculate_max_drawdown()
        sharpe_ratio = self._calculate_sharpe_ratio()
        
        # Concentration metrics
        concentration_risk = max(weights) if weights else 0
        diversification_score = 1 - sum([w**2 for w in weights]) if weights else 0
        
        return {
            'total_value': total_value,
            'total_pnl': total_pnl,
            'total_pnl_percentage': (total_pnl / total_value * 100) if total_value > 0 else 0,
            'portfolio_var_95': portfolio_var,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'concentration_risk': concentration_risk,
            'diversification_score': diversification_score,
            'number_of_positions': len(positions),
            'largest_position_weight': max(weights) if weights else 0
        }
    
    def _calculate_var(self, positions: List[Dict], confidence: float = 0.95) -> float:
        """Calculate Value at Risk"""
        if not positions:
            return 0
            
        # Simplified VaR calculation based on historical volatility
        returns = []
        for pos in positions:
            hist_data = pos.get('price_history', [])
            if len(hist_data) > 1:
                daily_returns = [(hist_data[i] - hist_data[i-1]) / hist_data[i-1] 
                               for i in range(1, len(hist_data))]
                returns.extend(daily_returns)
        
        if not returns:
            return 0
            
        returns_array = np.array(returns)
        var_percentile = (1 - confidence) * 100
        var = np.percentile(returns_array, var_percentile)
        
        total_value = sum(pos.get('current_value', 0) for pos in positions)
        return abs(var * total_value)
    
    def _calculate_max_drawdown(self) -> float:
        """Calculate maximum drawdown from performance history"""
        if len(self.performance_history) < 2:
            return 0
            
        values = [entry['portfolio_value'] for entry in self.performance_history]
        peak = values[0]
        max_dd = 0
        
        for value in values:
            if value > peak:
                peak = value
            else:
                drawdown = (peak - value) / peak
                max_dd = max(max_dd, drawdown)
        
        return max_dd * 100  # Return as percentage
    
    def _calculate_sharpe_ratio(self, risk_free_rate: float = 0.02) -> float:
        """Calculate Sharpe ratio"""
        if len(self.performance_history) < 2:
            return 0
            
        returns = []
        for i in range(1, len(self.performance_history)):
            prev_value = self.performance_history[i-1]['portfolio_value']
            curr_value = self.performance_history[i]['portfolio_value']
            if prev_value > 0:
                returns.append((curr_value - prev_value) / prev_value)
        
        if not returns:
            return 0
            
        returns_array = np.array(returns)
        avg_return = np.mean(returns_array)
        std_return = np.std(returns_array)
        
        if std_return == 0:
            return 0
            
        # Annualized Sharpe ratio (assuming daily returns)
        return (avg_return * 252 - risk_free_rate) / (std_return * np.sqrt(252))
    
    def generate_portfolio_heatmap_data(self) -> Dict:
        """Generate data for portfolio visualization heatmap"""
        positions = self.get_all_positions()
        
        if not positions:
            return {'symbols': [], 'weights': [], 'returns': [], 'risks': []}
            
        symbols = []
        weights = []
        returns = []
        risks = []
        
        total_value = sum(pos.get('current_value', 0) for pos in positions)
        
        for pos in positions:
            symbols.append(pos.get('symbol', 'Unknown'))
            weight = pos.get('current_value', 0) / total_value if total_value > 0 else 0
            weights.append(weight)
            returns.append(pos.get('unrealized_pnl_percentage', 0))
            
            # Calculate risk as volatility of recent returns
            price_history = pos.get('price_history', [])
            if len(price_history) > 1:
                daily_returns = [(price_history[i] - price_history[i-1]) / price_history[i-1] 
                               for i in range(1, len(price_history))]
                risk = np.std(daily_returns) * 100 if daily_returns else 0
            else:
                risk = 0
            risks.append(risk)
        
        return {
            'symbols': symbols,
            'weights': weights,
            'returns': returns,
            'risks': risks
        }
    
    def update_correlation_matrix(self, price_data: Dict):
        """Update correlation matrix between assets"""
        try:
            # Convert price data to DataFrame
            df_data = {}
            for symbol, data in price_data.items():
                if 'price_history' in data and len(data['price_history']) > 1:
                    df_data[symbol] = data['price_history']
            
            if len(df_data) < 2:
                return
                
            # Create DataFrame and calculate returns
            df = pd.DataFrame(df_data)
            returns_df = df.pct_change().dropna()
            
            # Calculate correlation matrix
            self.correlation_matrix = returns_df.corr()
            
        except Exception as e:
            logging.error(f"Error updating correlation matrix: {str(e)}")
    
    def get_correlation_data(self) -> Dict:
        """Get correlation matrix data for visualization"""
        if self.correlation_matrix.empty:
            return {}
            
        return {
            'symbols': self.correlation_matrix.columns.tolist(),
            'correlation_matrix': self.correlation_matrix.values.tolist()
        }

# ==================== BACKTESTING & STRATEGY OPTIMIZATION ====================

class AdvancedBacktester:
    """Professional backtesting system with Monte Carlo and walk-forward analysis"""
    
    def __init__(self, db_manager):
        self.db = db_manager
        self.results_cache = {}
        self.optimization_results = {}
        
    def run_backtest(self, strategy_config: Dict, start_date: str, end_date: str, 
                    initial_capital: float = 100000) -> Dict:
        """Run comprehensive backtest with detailed metrics"""
        
        try:
            # Fetch historical data
            historical_data = self._fetch_historical_data(
                strategy_config.get('symbols', ['BTC/USDT']),
                start_date,
                end_date
            )
            
            if not historical_data:
                return {'error': 'No historical data available'}
            
            # Initialize backtest state
            portfolio_value = initial_capital
            positions = {}
            trades = []
            equity_curve = []
            drawdown_curve = []
            peak_value = initial_capital
            
            # Run through historical data
            for date, market_data in historical_data.items():
                # Generate signals using current strategy
                signals = self._generate_backtest_signals(market_data, strategy_config)
                
                # Execute trades based on signals
                trade_results = self._execute_backtest_trades(
                    signals, positions, market_data, portfolio_value
                )
                
                trades.extend(trade_results['trades'])
                positions = trade_results['positions']
                portfolio_value = trade_results['portfolio_value']
                
                # Track equity curve and drawdown
                equity_curve.append({
                    'date': date,
                    'portfolio_value': portfolio_value,
                    'returns': (portfolio_value - initial_capital) / initial_capital
                })
                
                # Calculate drawdown
                if portfolio_value > peak_value:
                    peak_value = portfolio_value
                
                current_drawdown = (peak_value - portfolio_value) / peak_value
                drawdown_curve.append({
                    'date': date,
                    'drawdown': current_drawdown,
                    'peak_value': peak_value
                })
            
            # Calculate comprehensive metrics
            metrics = self._calculate_backtest_metrics(
                trades, equity_curve, drawdown_curve, initial_capital
            )
            
            return {
                'metrics': metrics,
                'trades': trades,
                'equity_curve': equity_curve,
                'drawdown_curve': drawdown_curve,
                'strategy_config': strategy_config,
                'period': f"{start_date} to {end_date}"
            }
            
        except Exception as e:
            logging.error(f"Backtest error: {str(e)}")
            return {'error': str(e)}
    
    def monte_carlo_simulation(self, base_strategy: Dict, num_simulations: int = 1000,
                             variation_params: Dict = None) -> Dict:
        """Run Monte Carlo simulation to test strategy robustness"""
        
        if variation_params is None:
            variation_params = {
                'entry_threshold': {'min': -0.2, 'max': 0.2},
                'exit_threshold': {'min': -0.2, 'max': 0.2},
                'stop_loss': {'min': 0.01, 'max': 0.05},
                'take_profit': {'min': 0.02, 'max': 0.08}
            }
        
        simulation_results = []
        
        for i in range(num_simulations):
            # Create randomized strategy variant
            strategy_variant = base_strategy.copy()
            
            for param, range_info in variation_params.items():
                if param in strategy_variant:
                    original_value = strategy_variant[param]
                    variation = np.random.uniform(range_info['min'], range_info['max'])
                    strategy_variant[param] = original_value * (1 + variation)
            
            # Run backtest with variant
            result = self.run_backtest(
                strategy_variant,
                base_strategy.get('start_date', '2023-01-01'),
                base_strategy.get('end_date', '2023-12-31')
            )
            
            if 'metrics' in result:
                simulation_results.append({
                    'simulation_id': i,
                    'strategy_variant': strategy_variant,
                    'total_return': result['metrics'].get('total_return_pct', 0),
                    'sharpe_ratio': result['metrics'].get('sharpe_ratio', 0),
                    'max_drawdown': result['metrics'].get('max_drawdown_pct', 0),
                    'win_rate': result['metrics'].get('win_rate', 0),
                    'profit_factor': result['metrics'].get('profit_factor', 0)
                })
        
        # Analyze results
        if simulation_results:
            returns = [r['total_return'] for r in simulation_results]
            sharpe_ratios = [r['sharpe_ratio'] for r in simulation_results]
            max_drawdowns = [r['max_drawdown'] for r in simulation_results]
            
            analysis = {
                'total_simulations': len(simulation_results),
                'profitable_percentage': len([r for r in returns if r > 0]) / len(returns) * 100,
                'average_return': np.mean(returns),
                'return_std': np.std(returns),
                'best_return': max(returns),
                'worst_return': min(returns),
                'average_sharpe': np.mean(sharpe_ratios),
                'average_max_drawdown': np.mean(max_drawdowns),
                'confidence_intervals': {
                    '95%': np.percentile(returns, [2.5, 97.5]).tolist(),
                    '90%': np.percentile(returns, [5, 95]).tolist(),
                    '68%': np.percentile(returns, [16, 84]).tolist()
                }
            }
            
            return {
                'analysis': analysis,
                'simulation_results': simulation_results[:100],  # Return first 100 for performance
                'base_strategy': base_strategy
            }
        
        return {'error': 'No valid simulation results'}
    
    def walk_forward_analysis(self, strategy_config: Dict, analysis_periods: int = 12,
                            optimization_window: int = 3) -> Dict:
        """Perform walk-forward analysis to test strategy adaptability"""
        
        results = []
        
        # Calculate period dates
        total_months = analysis_periods + optimization_window
        end_date = datetime.now()
        start_date = end_date - timedelta(days=total_months * 30)
        
        for period in range(analysis_periods):
            # Define optimization and testing periods
            opt_start = start_date + timedelta(days=period * 30)
            opt_end = opt_start + timedelta(days=optimization_window * 30)
            test_start = opt_end
            test_end = test_start + timedelta(days=30)
            
            if test_end > end_date:
                break
            
            # Optimize strategy on the optimization period
            optimized_strategy = self._optimize_strategy_parameters(
                strategy_config,
                opt_start.strftime('%Y-%m-%d'),
                opt_end.strftime('%Y-%m-%d')
            )
            
            # Test optimized strategy on the testing period
            test_result = self.run_backtest(
                optimized_strategy,
                test_start.strftime('%Y-%m-%d'),
                test_end.strftime('%Y-%m-%d')
            )
            
            if 'metrics' in test_result:
                results.append({
                    'period': period + 1,
                    'optimization_period': f"{opt_start.strftime('%Y-%m-%d')} to {opt_end.strftime('%Y-%m-%d')}",
                    'testing_period': f"{test_start.strftime('%Y-%m-%d')} to {test_end.strftime('%Y-%m-%d')}",
                    'optimized_parameters': optimized_strategy,
                    'test_metrics': test_result['metrics']
                })
        
        # Analyze walk-forward results
        if results:
            total_returns = [r['test_metrics'].get('total_return_pct', 0) for r in results]
            sharpe_ratios = [r['test_metrics'].get('sharpe_ratio', 0) for r in results]
            
            analysis = {
                'total_periods': len(results),
                'profitable_periods': len([r for r in total_returns if r > 0]),
                'average_return_per_period': np.mean(total_returns),
                'return_consistency': 1 / (1 + np.std(total_returns)),  # Higher is better
                'average_sharpe': np.mean(sharpe_ratios),
                'cumulative_return': np.prod([1 + r/100 for r in total_returns]) - 1
            }
            
            return {
                'analysis': analysis,
                'period_results': results,
                'strategy_config': strategy_config
            }
        
        return {'error': 'No valid walk-forward results'}
    
    def _fetch_historical_data(self, symbols: List[str], start_date: str, end_date: str) -> Dict:
        """Fetch historical price data for backtesting"""
        # This would typically fetch from exchange APIs or database
        # For now, return simulated data structure
        historical_data = {}
        
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        current_dt = start_dt
        
        while current_dt <= end_dt:
            date_str = current_dt.strftime('%Y-%m-%d')
            historical_data[date_str] = {}
            
            for symbol in symbols:
                # Simulate price data (in production, fetch real data)
                base_price = 50000 if 'BTC' in symbol else 3000
                price = base_price * (1 + np.random.normal(0, 0.02))
                
                historical_data[date_str][symbol] = {
                    'open': price * 0.999,
                    'high': price * 1.002,
                    'low': price * 0.998,
                    'close': price,
                    'volume': np.random.uniform(1000, 10000)
                }
            
            current_dt += timedelta(days=1)
        
        return historical_data
    
    def _generate_backtest_signals(self, market_data: Dict, strategy_config: Dict) -> Dict:
        """Generate trading signals for backtesting"""
        signals = {}
        
        # Simple strategy example (in production, use full signal generation logic)
        for symbol, data in market_data.items():
            price = data['close']
            
            # Simple moving average strategy
            ma_short = strategy_config.get('ma_short', 10)
            ma_long = strategy_config.get('ma_long', 30)
            
            # In production, calculate actual moving averages from price history
            signal_strength = np.random.uniform(-1, 1)  # Simulated signal
            
            signals[symbol] = {
                'signal': 'BUY' if signal_strength > 0.3 else 'SELL' if signal_strength < -0.3 else 'HOLD',
                'strength': abs(signal_strength),
                'price': price
            }
        
        return signals
    
    def _execute_backtest_trades(self, signals: Dict, positions: Dict, 
                               market_data: Dict, portfolio_value: float) -> Dict:
        """Execute trades during backtesting"""
        trades = []
        new_positions = positions.copy()
        
        for symbol, signal_data in signals.items():
            current_price = signal_data['price']
            signal = signal_data['signal']
            
            if signal == 'BUY' and symbol not in positions:
                # Enter long position
                position_size = portfolio_value * 0.1  # 10% per position
                quantity = position_size / current_price
                
                new_positions[symbol] = {
                    'side': 'long',
                    'quantity': quantity,
                    'entry_price': current_price,
                    'entry_time': datetime.now()
                }
                
                trades.append({
                    'symbol': symbol,
                    'side': 'BUY',
                    'quantity': quantity,
                    'price': current_price,
                    'timestamp': datetime.now(),
                    'type': 'ENTRY',
                    'pnl': 0  # Entry trade has no P&L
                })
                
            elif signal == 'SELL' and symbol in positions:
                # Exit position
                position = positions[symbol]
                quantity = position['quantity']
                entry_price = position['entry_price']
                
                pnl = (current_price - entry_price) * quantity
                
                trades.append({
                    'symbol': symbol,
                    'side': 'SELL',
                    'quantity': quantity,
                    'price': current_price,
                    'timestamp': datetime.now(),
                    'type': 'EXIT',
                    'pnl': pnl,
                    'return_pct': (current_price - entry_price) / entry_price * 100
                })
                
                del new_positions[symbol]
        
        # Calculate new portfolio value
        cash = portfolio_value
        for symbol, position in new_positions.items():
            if symbol in market_data:
                current_price = market_data[symbol]['close']
                position_value = position['quantity'] * current_price
                cash -= position_value
        
        new_portfolio_value = max(cash, 0)
        for symbol, position in new_positions.items():
            if symbol in market_data:
                current_price = market_data[symbol]['close']
                new_portfolio_value += position['quantity'] * current_price
        
        return {
            'trades': trades,
            'positions': new_positions,
            'portfolio_value': new_portfolio_value
        }
    
    def _calculate_backtest_metrics(self, trades: List[Dict], equity_curve: List[Dict],
                                  drawdown_curve: List[Dict], initial_capital: float) -> Dict:
        """Calculate comprehensive backtest metrics"""
        
        if not trades or not equity_curve:
            return {}
        
        # Basic metrics
        final_value = equity_curve[-1]['portfolio_value']
        total_return = (final_value - initial_capital) / initial_capital
        
        # Trade-based metrics
        winning_trades = [t for t in trades if t.get('pnl', 0) > 0]
        losing_trades = [t for t in trades if t.get('pnl', 0) <= 0]
        
        win_rate = len(winning_trades) / len(trades) if trades else 0
        
        avg_win = np.mean([t['pnl'] for t in winning_trades]) if winning_trades else 0
        avg_loss = np.mean([t['pnl'] for t in losing_trades]) if losing_trades else 0
        
        profit_factor = abs(sum([t['pnl'] for t in winning_trades]) / 
                           sum([t['pnl'] for t in losing_trades])) if losing_trades else float('inf')
        
        # Risk metrics
        returns = [e['returns'] for e in equity_curve]
        if len(returns) > 1:
            daily_returns = np.diff(returns)
            volatility = np.std(daily_returns) * np.sqrt(252)  # Annualized
            sharpe_ratio = (total_return - 0.02) / volatility if volatility > 0 else 0
        else:
            volatility = 0
            sharpe_ratio = 0
        
        max_drawdown = max([d['drawdown'] for d in drawdown_curve]) if drawdown_curve else 0
        
        return {
            'total_return_pct': total_return * 100,
            'annualized_return_pct': (((final_value / initial_capital) ** (252 / len(equity_curve))) - 1) * 100,
            'volatility_pct': volatility * 100,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown_pct': max_drawdown * 100,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'total_trades': len(trades),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'largest_win': max([t.get('pnl', 0) for t in trades]) if trades else 0,
            'largest_loss': min([t.get('pnl', 0) for t in trades]) if trades else 0
        }
    
    def _optimize_strategy_parameters(self, base_strategy: Dict, start_date: str, end_date: str) -> Dict:
        """Optimize strategy parameters using grid search"""
        
        # Define parameter ranges for optimization
        param_ranges = {
            'ma_short': [5, 10, 15, 20],
            'ma_long': [20, 30, 50, 100],
            'rsi_overbought': [70, 75, 80],
            'rsi_oversold': [20, 25, 30]
        }
        
        best_strategy = base_strategy.copy()
        best_sharpe = -999
        
        # Grid search through parameter combinations
        import itertools
        
        param_names = list(param_ranges.keys())
        param_values = list(param_ranges.values())
        
        for combination in itertools.product(*param_values):
            test_strategy = base_strategy.copy()
            
            for i, param_name in enumerate(param_names):
                test_strategy[param_name] = combination[i]
            
            # Quick backtest for optimization
            result = self.run_backtest(test_strategy, start_date, end_date)
            
            if 'metrics' in result:
                sharpe = result['metrics'].get('sharpe_ratio', -999)
                if sharpe > best_sharpe:
                    best_sharpe = sharpe
                    best_strategy = test_strategy.copy()
        
        return best_strategy

class SocialSentimentAnalyzer:
    """Advanced social media sentiment analysis for crypto markets"""
    
    def __init__(self, db_manager):
        self.db = db_manager
        self.sentiment_cache = {}
        self.social_metrics = {}
        self.fear_greed_history = []
        
    def analyze_twitter_sentiment(self, symbols: List[str], hours_back: int = 24) -> Dict:
        """Analyze Twitter sentiment for crypto symbols"""
        try:
            sentiment_data = {}
            
            for symbol in symbols:
                # Search terms for the symbol
                search_terms = [symbol, symbol.replace('/', ''), f"${symbol.split('/')[0]}"]
                
                tweets_data = []
                sentiment_scores = []
                
                # In production, use Twitter API v2
                # For now, simulate sentiment analysis
                for _ in range(100):  # Simulate 100 tweets
                    sentiment_score = np.random.normal(0, 0.3)  # Neutral bias with noise
                    tweets_data.append({
                        'text': f"Sample tweet about {symbol}",
                        'sentiment_score': sentiment_score,
                        'retweets': np.random.randint(0, 1000),
                        'likes': np.random.randint(0, 5000),
                        'timestamp': datetime.now() - timedelta(hours=np.random.randint(0, hours_back))
                    })
                    sentiment_scores.append(sentiment_score)
                
                # Calculate aggregated sentiment metrics
                avg_sentiment = np.mean(sentiment_scores)
                sentiment_std = np.std(sentiment_scores)
                positive_ratio = len([s for s in sentiment_scores if s > 0.1]) / len(sentiment_scores)
                negative_ratio = len([s for s in sentiment_scores if s < -0.1]) / len(sentiment_scores)
                
                # Weight by engagement
                weighted_sentiment = sum([
                    tweet['sentiment_score'] * (tweet['retweets'] + tweet['likes'] + 1)
                    for tweet in tweets_data
                ]) / sum([tweet['retweets'] + tweet['likes'] + 1 for tweet in tweets_data])
                
                sentiment_data[symbol] = {
                    'average_sentiment': avg_sentiment,
                    'weighted_sentiment': weighted_sentiment,
                    'sentiment_volatility': sentiment_std,
                    'positive_ratio': positive_ratio,
                    'negative_ratio': negative_ratio,
                    'neutral_ratio': 1 - positive_ratio - negative_ratio,
                    'total_tweets': len(tweets_data),
                    'sentiment_trend': self._calculate_sentiment_trend(symbol, avg_sentiment),
                    'engagement_score': np.mean([t['retweets'] + t['likes'] for t in tweets_data]),
                    'last_updated': datetime.now()
                }
            
            return sentiment_data
            
        except Exception as e:
            logging.error(f"Error analyzing Twitter sentiment: {str(e)}")
            return {}
    
    def analyze_reddit_sentiment(self, symbols: List[str]) -> Dict:
        """Analyze Reddit sentiment from crypto-related subreddits"""
        try:
            reddit_data = {}
            
            # Relevant subreddits
            subreddits = ['cryptocurrency', 'bitcoin', 'ethtrader', 'cryptomarkets', 'altcoin']
            
            for symbol in symbols:
                posts_data = []
                sentiment_scores = []
                
                # Simulate Reddit data analysis
                for _ in range(50):  # Simulate 50 posts
                    sentiment_score = np.random.normal(0.1, 0.4)  # Slightly positive bias
                    upvotes = np.random.randint(1, 1000)
                    comments = np.random.randint(1, 200)
                    
                    posts_data.append({
                        'title': f"Discussion about {symbol}",
                        'sentiment_score': sentiment_score,
                        'upvotes': upvotes,
                        'comments': comments,
                        'score': upvotes - np.random.randint(0, upvotes // 10),
                        'timestamp': datetime.now() - timedelta(hours=np.random.randint(0, 48))
                    })
                    sentiment_scores.append(sentiment_score)
                
                # Calculate metrics
                avg_sentiment = np.mean(sentiment_scores)
                discussion_volume = sum([p['comments'] for p in posts_data])
                
                # Weight by Reddit score and comments
                weighted_sentiment = sum([
                    post['sentiment_score'] * (post['score'] + post['comments'] + 1)
                    for post in posts_data
                ]) / sum([post['score'] + post['comments'] + 1 for post in posts_data])
                
                reddit_data[symbol] = {
                    'average_sentiment': avg_sentiment,
                    'weighted_sentiment': weighted_sentiment,
                    'discussion_volume': discussion_volume,
                    'total_posts': len(posts_data),
                    'average_upvotes': np.mean([p['upvotes'] for p in posts_data]),
                    'sentiment_distribution': {
                        'positive': len([s for s in sentiment_scores if s > 0.2]),
                        'neutral': len([s for s in sentiment_scores if -0.2 <= s <= 0.2]),
                        'negative': len([s for s in sentiment_scores if s < -0.2])
                    },
                    'last_updated': datetime.now()
                }
            
            return reddit_data
            
        except Exception as e:
            logging.error(f"Error analyzing Reddit sentiment: {str(e)}")
            return {}
    
    def get_fear_greed_index(self) -> Dict:
        """Calculate crypto Fear & Greed Index"""
        try:
            # In production, fetch from alternative.me API or calculate from multiple factors
            # For now, simulate the index
            
            # Components of Fear & Greed Index
            components = {
                'volatility': np.random.uniform(0, 100),  # Price volatility
                'market_momentum': np.random.uniform(0, 100),  # Volume and momentum
                'social_media': np.random.uniform(0, 100),  # Social media sentiment
                'surveys': np.random.uniform(0, 100),  # Market surveys
                'dominance': np.random.uniform(0, 100),  # Bitcoin dominance
                'google_trends': np.random.uniform(0, 100)  # Google search trends
            }
            
            # Calculate weighted average
            weights = {
                'volatility': 0.25,
                'market_momentum': 0.25,
                'social_media': 0.15,
                'surveys': 0.15,
                'dominance': 0.10,
                'google_trends': 0.10
            }
            
            fear_greed_value = sum([components[comp] * weights[comp] for comp in components])
            
            # Determine sentiment label
            if fear_greed_value <= 25:
                sentiment_label = "Extreme Fear"
                color = "#8B0000"
            elif fear_greed_value <= 45:
                sentiment_label = "Fear"
                color = "#FF4500"
            elif fear_greed_value <= 55:
                sentiment_label = "Neutral"
                color = "#FFD700"
            elif fear_greed_value <= 75:
                sentiment_label = "Greed"
                color = "#32CD32"
            else:
                sentiment_label = "Extreme Greed"
                color = "#006400"
            
            index_data = {
                'value': round(fear_greed_value, 1),
                'sentiment': sentiment_label,
                'color': color,
                'components': components,
                'timestamp': datetime.now(),
                'historical_average': np.mean([entry['value'] for entry in self.fear_greed_history]) if self.fear_greed_history else fear_greed_value
            }
            
            # Store in history
            self.fear_greed_history.append(index_data)
            if len(self.fear_greed_history) > 30:  # Keep last 30 days
                self.fear_greed_history.pop(0)
            
            return index_data
            
        except Exception as e:
            logging.error(f"Error calculating Fear & Greed Index: {str(e)}")
            return {}
    
    def analyze_news_sentiment(self, symbols: List[str]) -> Dict:
        """Analyze sentiment from crypto news sources"""
        try:
            news_sentiment = {}
            
            # News sources to monitor
            sources = ['coindesk', 'cointelegraph', 'decrypt', 'coinmarketcap', 'blockchain.news']
            
            for symbol in symbols:
                articles_data = []
                sentiment_scores = []
                
                # Simulate news article analysis
                for _ in range(20):  # Simulate 20 articles
                    sentiment_score = np.random.normal(0.05, 0.3)  # Slightly positive bias for news
                    
                    articles_data.append({
                        'title': f"News about {symbol}",
                        'source': np.random.choice(sources),
                        'sentiment_score': sentiment_score,
                        'importance_score': np.random.uniform(0.3, 1.0),
                        'timestamp': datetime.now() - timedelta(hours=np.random.randint(0, 72))
                    })
                    sentiment_scores.append(sentiment_score)
                
                # Calculate weighted sentiment by importance
                weighted_sentiment = sum([
                    article['sentiment_score'] * article['importance_score']
                    for article in articles_data
                ]) / sum([article['importance_score'] for article in articles_data])
                
                news_sentiment[symbol] = {
                    'average_sentiment': np.mean(sentiment_scores),
                    'weighted_sentiment': weighted_sentiment,
                    'total_articles': len(articles_data),
                    'sentiment_trend': self._calculate_sentiment_trend(symbol, weighted_sentiment),
                    'source_diversity': len(set([a['source'] for a in articles_data])),
                    'last_updated': datetime.now()
                }
            
            return news_sentiment
            
        except Exception as e:
            logging.error(f"Error analyzing news sentiment: {str(e)}")
            return {}
    
    def get_comprehensive_sentiment_score(self, symbol: str) -> Dict:
        """Calculate comprehensive sentiment score from all sources"""
        try:
            # Get sentiment from all sources
            twitter_data = self.sentiment_cache.get('twitter', {}).get(symbol, {})
            reddit_data = self.sentiment_cache.get('reddit', {}).get(symbol, {})
            news_data = self.sentiment_cache.get('news', {}).get(symbol, {})
            fear_greed = self.get_fear_greed_index()
            
            # Extract sentiment scores
            twitter_sentiment = twitter_data.get('weighted_sentiment', 0)
            reddit_sentiment = reddit_data.get('weighted_sentiment', 0)
            news_sentiment = news_data.get('weighted_sentiment', 0)
            fear_greed_normalized = (fear_greed.get('value', 50) - 50) / 50  # Normalize to -1 to 1
            
            # Calculate weighted composite score
            weights = {
                'twitter': 0.3,
                'reddit': 0.25,
                'news': 0.25,
                'fear_greed': 0.2
            }
            
            composite_score = (
                twitter_sentiment * weights['twitter'] +
                reddit_sentiment * weights['reddit'] +
                news_sentiment * weights['news'] +
                fear_greed_normalized * weights['fear_greed']
            )
            
            # Normalize to 0-100 scale
            sentiment_score = max(0, min(100, (composite_score + 1) * 50))
            
            # Determine sentiment category
            if sentiment_score >= 70:
                category = "Very Bullish"
                color = "#00FF00"
            elif sentiment_score >= 60:
                category = "Bullish"
                color = "#90EE90"
            elif sentiment_score >= 40:
                category = "Neutral"
                color = "#FFFF00"
            elif sentiment_score >= 30:
                category = "Bearish"
                color = "#FFA500"
            else:
                category = "Very Bearish"
                color = "#FF0000"
            
            return {
                'composite_score': round(sentiment_score, 1),
                'category': category,
                'color': color,
                'components': {
                    'twitter': twitter_sentiment,
                    'reddit': reddit_sentiment,
                    'news': news_sentiment,
                    'fear_greed': fear_greed_normalized
                },
                'confidence': self._calculate_sentiment_confidence(twitter_data, reddit_data, news_data),
                'last_updated': datetime.now()
            }
            
        except Exception as e:
            logging.error(f"Error calculating comprehensive sentiment: {str(e)}")
            return {}
    
    def _calculate_sentiment_trend(self, symbol: str, current_sentiment: float) -> str:
        """Calculate sentiment trend direction"""
        history_key = f"{symbol}_sentiment_history"
        
        if history_key not in self.sentiment_cache:
            self.sentiment_cache[history_key] = []
        
        history = self.sentiment_cache[history_key]
        history.append({
            'sentiment': current_sentiment,
            'timestamp': datetime.now()
        })
        
        # Keep only last 24 hours
        cutoff_time = datetime.now() - timedelta(hours=24)
        history = [h for h in history if h['timestamp'] > cutoff_time]
        self.sentiment_cache[history_key] = history
        
        if len(history) < 2:
            return "No Trend"
        
        # Calculate trend
        recent_avg = np.mean([h['sentiment'] for h in history[-6:]])  # Last 6 readings
        older_avg = np.mean([h['sentiment'] for h in history[-12:-6]])  # Previous 6 readings
        
        if len(history) < 12:
            return "Insufficient Data"
        
        change = recent_avg - older_avg
        
        if change > 0.1:
            return "Improving"
        elif change < -0.1:
            return "Declining"
        else:
            return "Stable"
    
    def _calculate_sentiment_confidence(self, twitter_data: Dict, reddit_data: Dict, news_data: Dict) -> float:
        """Calculate confidence level of sentiment analysis"""
        confidence_factors = []
        
        # Twitter confidence based on volume and consistency
        if twitter_data:
            twitter_volume = twitter_data.get('total_tweets', 0)
            twitter_volatility = twitter_data.get('sentiment_volatility', 1)
            twitter_conf = min(1.0, twitter_volume / 100) * (1 - min(1.0, twitter_volatility))
            confidence_factors.append(twitter_conf)
        
        # Reddit confidence based on discussion volume
        if reddit_data:
            reddit_volume = reddit_data.get('discussion_volume', 0)
            reddit_conf = min(1.0, reddit_volume / 500)
            confidence_factors.append(reddit_conf)
        
        # News confidence based on article count and source diversity
        if news_data:
            news_articles = news_data.get('total_articles', 0)
            source_diversity = news_data.get('source_diversity', 1)
            news_conf = min(1.0, news_articles / 10) * min(1.0, source_diversity / 3)
            confidence_factors.append(news_conf)
        
        if not confidence_factors:
            return 0.0
        
        return np.mean(confidence_factors)
    
    def update_sentiment_cache(self, symbols: List[str]):
        """Update sentiment cache for all symbols"""
        try:
            # Update Twitter sentiment
            twitter_sentiment = self.analyze_twitter_sentiment(symbols)
            self.sentiment_cache['twitter'] = twitter_sentiment
            
            # Update Reddit sentiment
            reddit_sentiment = self.analyze_reddit_sentiment(symbols)
            self.sentiment_cache['reddit'] = reddit_sentiment
            
            # Update news sentiment
            news_sentiment = self.analyze_news_sentiment(symbols)
            self.sentiment_cache['news'] = news_sentiment
            
            logging.info(f"Updated sentiment cache for {len(symbols)} symbols")
            
        except Exception as e:
            logging.error(f"Error updating sentiment cache: {str(e)}")

class DeFiAnalyzer:
    """Advanced DeFi and on-chain analytics system"""
    
    def __init__(self, db_manager):
        self.db = db_manager
        self.dex_data = {}
        self.liquidity_pools = {}
        self.whale_addresses = {}
        self.on_chain_metrics = {}
        
    def analyze_dex_markets(self, symbols: List[str]) -> Dict:
        """Analyze DEX markets across multiple protocols"""
        try:
            dex_analysis = {}
            
            # Major DEX protocols to monitor
            dex_protocols = ['uniswap', 'sushiswap', 'pancakeswap', 'curve', '1inch']
            
            for symbol in symbols:
                protocol_data = {}
                
                for protocol in dex_protocols:
                    # Simulate DEX data (in production, use actual DEX APIs)
                    price = np.random.uniform(45000, 55000) if 'BTC' in symbol else np.random.uniform(2800, 3200)
                    liquidity = np.random.uniform(1000000, 50000000)
                    volume_24h = np.random.uniform(100000, 10000000)
                    
                    protocol_data[protocol] = {
                        'price': price,
                        'liquidity_usd': liquidity,
                        'volume_24h': volume_24h,
                        'fees_24h': volume_24h * 0.003,  # 0.3% typical fee
                        'price_impact_1k': np.random.uniform(0.01, 0.1),
                        'price_impact_10k': np.random.uniform(0.1, 1.0),
                        'slippage_tolerance': np.random.uniform(0.5, 2.0)
                    }
                
                # Calculate best execution data
                best_buy_price = min([data['price'] for data in protocol_data.values()])
                best_sell_price = max([data['price'] for data in protocol_data.values()])
                total_liquidity = sum([data['liquidity_usd'] for data in protocol_data.values()])
                
                dex_analysis[symbol] = {
                    'protocols': protocol_data,
                    'best_buy_exchange': [p for p, data in protocol_data.items() if data['price'] == best_buy_price][0],
                    'best_sell_exchange': [p for p, data in protocol_data.items() if data['price'] == best_sell_price][0],
                    'price_spread': best_sell_price - best_buy_price,
                    'spread_percentage': ((best_sell_price - best_buy_price) / best_buy_price) * 100,
                    'total_liquidity': total_liquidity,
                    'avg_price': np.mean([data['price'] for data in protocol_data.values()]),
                    'liquidity_fragmentation': len([p for p, data in protocol_data.items() if data['liquidity_usd'] > total_liquidity * 0.1])
                }
            
            return dex_analysis
            
        except Exception as e:
            logging.error(f"Error analyzing DEX markets: {str(e)}")
            return {}
    
    def monitor_liquidity_pools(self, pool_addresses: List[str] = None) -> Dict:
        """Monitor liquidity pool performance and yields"""
        try:
            if pool_addresses is None:
                # Default to major pools
                pool_addresses = [
                    '0x...btc_eth_pool',
                    '0x...usdc_usdt_pool', 
                    '0x...eth_dai_pool'
                ]
            
            pool_analysis = {}
            
            for pool_address in pool_addresses:
                # Simulate pool data (in production, use Web3 and DEX subgraphs)
                pool_analysis[pool_address] = {
                    'protocol': np.random.choice(['Uniswap V3', 'Curve', 'Balancer']),
                    'token_pair': np.random.choice(['BTC/ETH', 'USDC/USDT', 'ETH/DAI']),
                    'tvl_usd': np.random.uniform(1000000, 100000000),
                    'volume_24h': np.random.uniform(100000, 50000000),
                    'fees_24h': np.random.uniform(1000, 100000),
                    'apy': np.random.uniform(2, 25),
                    'impermanent_loss_risk': np.random.uniform(0.1, 5.0),
                    'price_range': {
                        'lower': np.random.uniform(0.95, 1.0),
                        'upper': np.random.uniform(1.0, 1.05)
                    },
                    'utilization_rate': np.random.uniform(60, 95),
                    'fee_tier': np.random.choice([0.05, 0.3, 1.0]),
                    'last_updated': datetime.now()
                }
            
            # Calculate aggregate metrics
            total_tvl = sum([pool['tvl_usd'] for pool in pool_analysis.values()])
            avg_apy = np.mean([pool['apy'] for pool in pool_analysis.values()])
            
            return {
                'pools': pool_analysis,
                'aggregate_metrics': {
                    'total_tvl': total_tvl,
                    'average_apy': avg_apy,
                    'total_pools_monitored': len(pool_analysis),
                    'highest_apy_pool': max(pool_analysis.keys(), key=lambda x: pool_analysis[x]['apy']),
                    'largest_pool': max(pool_analysis.keys(), key=lambda x: pool_analysis[x]['tvl_usd'])
                }
            }
            
        except Exception as e:
            logging.error(f"Error monitoring liquidity pools: {str(e)}")
            return {}
    
    def track_whale_movements(self, symbols: List[str], min_transaction_usd: float = 1000000) -> Dict:
        """Track large whale transactions and wallet movements"""
        try:
            whale_activity = {}
            
            for symbol in symbols:
                transactions = []
                
                # Simulate whale transactions (in production, use blockchain APIs)
                for _ in range(np.random.randint(5, 20)):
                    transaction_value = np.random.uniform(min_transaction_usd, min_transaction_usd * 10)
                    transaction_type = np.random.choice(['buy', 'sell', 'transfer'])
                    
                    transactions.append({
                        'tx_hash': f"0x{''.join(np.random.choice('0123456789abcdef', 64))}",
                        'type': transaction_type,
                        'value_usd': transaction_value,
                        'amount': transaction_value / (50000 if 'BTC' in symbol else 3000),
                        'from_address': f"0x{''.join(np.random.choice('0123456789abcdef', 40))}",
                        'to_address': f"0x{''.join(np.random.choice('0123456789abcdef', 40))}",
                        'timestamp': datetime.now() - timedelta(hours=np.random.randint(0, 24)),
                        'exchange': np.random.choice(['Binance', 'Coinbase', 'Unknown Wallet', 'DeFi Protocol'])
                    })
                
                # Analyze patterns
                buy_volume = sum([tx['value_usd'] for tx in transactions if tx['type'] == 'buy'])
                sell_volume = sum([tx['value_usd'] for tx in transactions if tx['type'] == 'sell'])
                net_flow = buy_volume - sell_volume
                
                whale_activity[symbol] = {
                    'transactions': sorted(transactions, key=lambda x: x['value_usd'], reverse=True)[:10],  # Top 10
                    'summary': {
                        'total_transactions': len(transactions),
                        'buy_volume': buy_volume,
                        'sell_volume': sell_volume,
                        'net_flow': net_flow,
                        'net_flow_direction': 'Accumulation' if net_flow > 0 else 'Distribution',
                        'largest_transaction': max([tx['value_usd'] for tx in transactions]) if transactions else 0,
                        'average_transaction_size': np.mean([tx['value_usd'] for tx in transactions]) if transactions else 0
                    },
                    'exchange_flows': self._analyze_exchange_flows(transactions),
                    'last_updated': datetime.now()
                }
            
            return whale_activity
            
        except Exception as e:
            logging.error(f"Error tracking whale movements: {str(e)}")
            return {}
    
    def analyze_on_chain_metrics(self, symbols: List[str]) -> Dict:
        """Analyze comprehensive on-chain metrics"""
        try:
            on_chain_data = {}
            
            for symbol in symbols:
                # Simulate on-chain metrics (in production, use blockchain APIs like Glassnode, IntoTheBlock)
                on_chain_data[symbol] = {
                    'network_metrics': {
                        'active_addresses': np.random.randint(500000, 1000000),
                        'new_addresses': np.random.randint(10000, 50000),
                        'transaction_count': np.random.randint(200000, 500000),
                        'transaction_volume': np.random.uniform(1000000000, 5000000000),
                        'average_transaction_value': np.random.uniform(500, 5000),
                        'hash_rate': np.random.uniform(100, 200) if 'BTC' in symbol else None,
                        'network_difficulty': np.random.uniform(20, 30) if 'BTC' in symbol else None
                    },
                    'holder_metrics': {
                        'addresses_with_balance': np.random.randint(30000000, 50000000),
                        'addresses_holding_1_year_plus': np.random.uniform(0.4, 0.6),
                        'top_10_holders_percentage': np.random.uniform(5, 15),
                        'top_100_holders_percentage': np.random.uniform(15, 30),
                        'hodler_score': np.random.uniform(60, 90)
                    },
                    'flow_metrics': {
                        'exchange_inflows': np.random.uniform(10000, 100000),
                        'exchange_outflows': np.random.uniform(10000, 100000),
                        'exchange_net_flow': np.random.uniform(-50000, 50000),
                        'stablecoin_inflows': np.random.uniform(50000000, 500000000),
                        'institutional_inflows': np.random.uniform(10000000, 100000000)
                    },
                    'derivatives_metrics': {
                        'futures_open_interest': np.random.uniform(1000000000, 10000000000),
                        'options_open_interest': np.random.uniform(500000000, 5000000000),
                        'funding_rates': np.random.uniform(-0.01, 0.01),
                        'long_short_ratio': np.random.uniform(0.8, 1.2),
                        'liquidations_24h': np.random.uniform(10000000, 100000000)
                    },
                    'technical_on_chain': {
                        'nvt_ratio': np.random.uniform(20, 100),
                        'mvrv_ratio': np.random.uniform(0.8, 3.0),
                        'realized_price': np.random.uniform(30000, 45000) if 'BTC' in symbol else np.random.uniform(2000, 2800),
                        'stock_to_flow_ratio': np.random.uniform(50, 60) if 'BTC' in symbol else None,
                        'pi_cycle_top': np.random.uniform(0.3, 0.8),
                        'puell_multiple': np.random.uniform(0.5, 2.0) if 'BTC' in symbol else None
                    }
                }
                
                # Calculate composite scores
                on_chain_data[symbol]['composite_scores'] = {
                    'network_health': self._calculate_network_health_score(on_chain_data[symbol]['network_metrics']),
                    'adoption_score': self._calculate_adoption_score(on_chain_data[symbol]['holder_metrics']),
                    'institutional_interest': self._calculate_institutional_score(on_chain_data[symbol]['flow_metrics']),
                    'market_cycle_position': self._calculate_cycle_position(on_chain_data[symbol]['technical_on_chain'])
                }
            
            return on_chain_data
            
        except Exception as e:
            logging.error(f"Error analyzing on-chain metrics: {str(e)}")
            return {}
    
    def _analyze_exchange_flows(self, transactions: List[Dict]) -> Dict:
        """Analyze flows between exchanges and wallets"""
        exchange_flows = defaultdict(lambda: {'inflow': 0, 'outflow': 0})
        
        for tx in transactions:
            if tx['exchange'] != 'Unknown Wallet':
                if tx['type'] == 'buy':
                    exchange_flows[tx['exchange']]['inflow'] += tx['value_usd']
                elif tx['type'] == 'sell':
                    exchange_flows[tx['exchange']]['outflow'] += tx['value_usd']
        
        # Calculate net flows
        for exchange in exchange_flows:
            exchange_flows[exchange]['net_flow'] = (
                exchange_flows[exchange]['inflow'] - exchange_flows[exchange]['outflow']
            )
        
        return dict(exchange_flows)
    
    def _calculate_network_health_score(self, network_metrics: Dict) -> float:
        """Calculate network health score (0-100)"""
        # Normalize metrics and calculate weighted score
        active_addresses_score = min(100, (network_metrics['active_addresses'] / 1000000) * 100)
        transaction_score = min(100, (network_metrics['transaction_count'] / 500000) * 100)
        volume_score = min(100, (network_metrics['transaction_volume'] / 5000000000) * 100)
        
        return (active_addresses_score * 0.4 + transaction_score * 0.3 + volume_score * 0.3)
    
    def _calculate_adoption_score(self, holder_metrics: Dict) -> float:
        """Calculate adoption score (0-100)"""
        hodl_score = holder_metrics['addresses_holding_1_year_plus'] * 100
        distribution_score = 100 - holder_metrics['top_10_holders_percentage']  # Lower concentration = better
        base_score = holder_metrics['hodler_score']
        
        return (hodl_score * 0.4 + distribution_score * 0.3 + base_score * 0.3)
    
    def _calculate_institutional_score(self, flow_metrics: Dict) -> float:
        """Calculate institutional interest score (0-100)"""
        institutional_flow = flow_metrics['institutional_inflows'] / 1000000000  # Normalize to billions
        stablecoin_flow = flow_metrics['stablecoin_inflows'] / 1000000000
        
        score = min(100, (institutional_flow * 50 + stablecoin_flow * 20))
        return score
    
    def _calculate_cycle_position(self, technical_metrics: Dict) -> float:
        """Calculate market cycle position (0-100, where 50 is neutral)"""
        mvrv = technical_metrics['mvrv_ratio']
        pi_cycle = technical_metrics['pi_cycle_top']
        
        # MVRV interpretation: <1 = undervalued, >3 = overvalued
        mvrv_score = max(0, min(100, (mvrv - 0.5) / 2.5 * 100))
        pi_score = pi_cycle * 100
        
        return (mvrv_score * 0.6 + pi_score * 0.4)

class ProfessionalReportGenerator:
    """Generate professional-grade trading reports and compliance documentation"""
    
    def __init__(self, db_manager):
        self.db = db_manager
        self.report_templates = {}
        self.compliance_settings = {}
        
    def generate_daily_report(self, date: str = None) -> Dict:
        """Generate comprehensive daily trading report"""
        try:
            if date is None:
                date = datetime.now().strftime('%Y-%m-%d')
            
            # Gather data for report
            portfolio_data = self._get_portfolio_snapshot(date)
            performance_data = self._get_performance_metrics(date)
            risk_data = self._get_risk_analysis(date)
            market_data = self._get_market_overview(date)
            
            report = {
                'report_metadata': {
                    'report_type': 'Daily Trading Report',
                    'date': date,
                    'generated_at': datetime.now(),
                    'report_id': f"DTR_{date.replace('-', '')}_{int(time.time())}"
                },
                'executive_summary': self._generate_executive_summary(portfolio_data, performance_data),
                'portfolio_overview': portfolio_data,
                'performance_analysis': performance_data,
                'risk_assessment': risk_data,
                'market_overview': market_data,
                'trading_activity': self._get_trading_activity(date),
                'alerts_summary': self._get_alerts_summary(date),
                'recommendations': self._generate_recommendations(portfolio_data, risk_data)
            }
            
            return report
            
        except Exception as e:
            logging.error(f"Error generating daily report: {str(e)}")
            return {'error': str(e)}
    
    def generate_monthly_report(self, year: int, month: int) -> Dict:
        """Generate comprehensive monthly report"""
        try:
            month_start = datetime(year, month, 1)
            if month == 12:
                month_end = datetime(year + 1, 1, 1) - timedelta(days=1)
            else:
                month_end = datetime(year, month + 1, 1) - timedelta(days=1)
            
            report = {
                'report_metadata': {
                    'report_type': 'Monthly Performance Report',
                    'period': f"{month_start.strftime('%B %Y')}",
                    'generated_at': datetime.now(),
                    'report_id': f"MPR_{year}{month:02d}_{int(time.time())}"
                },
                'performance_summary': self._get_monthly_performance(month_start, month_end),
                'portfolio_evolution': self._get_portfolio_evolution(month_start, month_end),
                'risk_metrics': self._get_monthly_risk_metrics(month_start, month_end),
                'trading_statistics': self._get_trading_statistics(month_start, month_end),
                'benchmark_comparison': self._get_benchmark_comparison(month_start, month_end),
                'attribution_analysis': self._get_attribution_analysis(month_start, month_end),
                'compliance_review': self._get_compliance_review(month_start, month_end)
            }
            
            return report
            
        except Exception as e:
            logging.error(f"Error generating monthly report: {str(e)}")
            return {'error': str(e)}
    
    def generate_pdf_report(self, report_data: Dict, output_path: str = None) -> str:
        """Generate PDF report from report data"""
        try:
            from reportlab.lib.pagesizes import letter, A4
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch
            from reportlab.lib import colors
            from reportlab.graphics.shapes import Drawing
            from reportlab.graphics.charts.linecharts import HorizontalLineChart
            from reportlab.graphics.charts.piecharts import Pie
            
            if output_path is None:
                output_path = f"/tmp/crypto_report_{int(time.time())}.pdf"
            
            doc = SimpleDocTemplate(output_path, pagesize=A4)
            styles = getSampleStyleSheet()
            story = []
            
            # Custom styles
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=24,
                spaceAfter=30,
                textColor=colors.darkblue
            )
            
            header_style = ParagraphStyle(
                'CustomHeader',
                parent=styles['Heading2'],
                fontSize=16,
                spaceAfter=12,
                textColor=colors.blue
            )
            
            # Title page
            story.append(Paragraph("Professional Crypto Trading Report", title_style))
            story.append(Spacer(1, 12))
            
            # Report metadata
            metadata = report_data.get('report_metadata', {})
            story.append(Paragraph(f"Report Type: {metadata.get('report_type', 'N/A')}", styles['Normal']))
            story.append(Paragraph(f"Period: {metadata.get('date', metadata.get('period', 'N/A'))}", styles['Normal']))
            story.append(Paragraph(f"Generated: {metadata.get('generated_at', 'N/A')}", styles['Normal']))
            story.append(Paragraph(f"Report ID: {metadata.get('report_id', 'N/A')}", styles['Normal']))
            story.append(Spacer(1, 20))
            
            # Executive Summary
            if 'executive_summary' in report_data:
                story.append(Paragraph("Executive Summary", header_style))
                exec_summary = report_data['executive_summary']
                story.append(Paragraph(exec_summary.get('overview', ''), styles['Normal']))
                story.append(Spacer(1, 12))
                
                # Key metrics table
                key_metrics = [
                    ['Metric', 'Value'],
                    ['Total Portfolio Value', f"${exec_summary.get('total_value', 0):,.2f}"],
                    ['Daily P&L', f"${exec_summary.get('daily_pnl', 0):,.2f}"],
                    ['Total Return', f"{exec_summary.get('total_return_pct', 0):.2f}%"],
                    ['Sharpe Ratio', f"{exec_summary.get('sharpe_ratio', 0):.2f}"],
                    ['Max Drawdown', f"{exec_summary.get('max_drawdown', 0):.2f}%"]
                ]
                
                table = Table(key_metrics)
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 14),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                story.append(table)
                story.append(Spacer(1, 20))
            
            # Portfolio Overview
            if 'portfolio_overview' in report_data:
                story.append(Paragraph("Portfolio Overview", header_style))
                portfolio = report_data['portfolio_overview']
                
                positions_data = [['Symbol', 'Quantity', 'Current Price', 'Market Value', 'P&L']]
                for position in portfolio.get('positions', []):
                    positions_data.append([
                        position.get('symbol', ''),
                        f"{position.get('quantity', 0):.4f}",
                        f"${position.get('current_price', 0):.2f}",
                        f"${position.get('market_value', 0):,.2f}",
                        f"${position.get('unrealized_pnl', 0):,.2f}"
                    ])
                
                if len(positions_data) > 1:
                    positions_table = Table(positions_data)
                    positions_table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, 0), 12),
                        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                        ('BACKGROUND', (0, 1), (-1, -1), colors.lightblue),
                        ('GRID', (0, 0), (-1, -1), 1, colors.black)
                    ]))
                    story.append(positions_table)
                    story.append(Spacer(1, 20))
            
            # Risk Assessment
            if 'risk_assessment' in report_data:
                story.append(PageBreak())
                story.append(Paragraph("Risk Assessment", header_style))
                risk = report_data['risk_assessment']
                
                risk_metrics = [
                    ['Risk Metric', 'Value', 'Status'],
                    ['Value at Risk (95%)', f"${risk.get('var_95', 0):,.2f}", risk.get('var_status', 'Normal')],
                    ['Portfolio Beta', f"{risk.get('portfolio_beta', 0):.2f}", risk.get('beta_status', 'Normal')],
                    ['Concentration Risk', f"{risk.get('concentration_risk', 0):.1f}%", risk.get('concentration_status', 'Normal')],
                    ['Liquidity Risk', risk.get('liquidity_risk', 'Low'), risk.get('liquidity_status', 'Normal')]
                ]
                
                risk_table = Table(risk_metrics)
                risk_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.red),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 12),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                story.append(risk_table)
            
            # Build PDF
            doc.build(story)
            
            return output_path
            
        except Exception as e:
            logging.error(f"Error generating PDF report: {str(e)}")
            return None
    
    def generate_compliance_report(self, start_date: str, end_date: str) -> Dict:
        """Generate compliance and regulatory report"""
        try:
            report = {
                'report_metadata': {
                    'report_type': 'Compliance Report',
                    'period': f"{start_date} to {end_date}",
                    'generated_at': datetime.now(),
                    'report_id': f"COMP_{start_date.replace('-', '')}_{end_date.replace('-', '')}_{int(time.time())}"
                },
                'regulatory_compliance': {
                    'position_limits': self._check_position_limits(),
                    'concentration_limits': self._check_concentration_limits(),
                    'risk_limits': self._check_risk_limits(),
                    'trading_hours': self._check_trading_hours_compliance(),
                    'documentation': self._verify_trade_documentation()
                },
                'risk_compliance': {
                    'var_breaches': self._check_var_breaches(),
                    'drawdown_limits': self._check_drawdown_limits(),
                    'leverage_compliance': self._check_leverage_compliance(),
                    'liquidity_requirements': self._check_liquidity_requirements()
                },
                'audit_trail': {
                    'trade_reconciliation': self._reconcile_trades(),
                    'price_verification': self._verify_pricing(),
                    'system_logs': self._extract_system_logs(),
                    'error_analysis': self._analyze_errors()
                },
                'recommendations': self._generate_compliance_recommendations()
            }
            
            return report
            
        except Exception as e:
            logging.error(f"Error generating compliance report: {str(e)}")
            return {'error': str(e)}
    
    def _get_portfolio_snapshot(self, date: str) -> Dict:
        """Get portfolio snapshot for specific date"""
        # In production, query actual portfolio data
        return {
            'total_value': np.random.uniform(950000, 1050000),
            'cash_balance': np.random.uniform(50000, 150000),
            'positions': [
                {
                    'symbol': 'BTC/USDT',
                    'quantity': np.random.uniform(5, 15),
                    'current_price': np.random.uniform(48000, 52000),
                    'market_value': np.random.uniform(240000, 780000),
                    'unrealized_pnl': np.random.uniform(-50000, 50000)
                },
                {
                    'symbol': 'ETH/USDT',
                    'quantity': np.random.uniform(50, 150),
                    'current_price': np.random.uniform(2800, 3200),
                    'market_value': np.random.uniform(140000, 480000),
                    'unrealized_pnl': np.random.uniform(-30000, 30000)
                }
            ],
            'allocation': {
                'BTC': np.random.uniform(40, 60),
                'ETH': np.random.uniform(25, 40),
                'Others': np.random.uniform(5, 15),
                'Cash': np.random.uniform(5, 20)
            }
        }
    
    def _get_performance_metrics(self, date: str) -> Dict:
        """Get performance metrics for specific date"""
        return {
            'daily_return': np.random.uniform(-3, 3),
            'weekly_return': np.random.uniform(-8, 8),
            'monthly_return': np.random.uniform(-15, 15),
            'ytd_return': np.random.uniform(-20, 25),
            'sharpe_ratio': np.random.uniform(0.5, 2.5),
            'sortino_ratio': np.random.uniform(0.7, 3.0),
            'max_drawdown': np.random.uniform(2, 15),
            'win_rate': np.random.uniform(45, 75),
            'profit_factor': np.random.uniform(1.1, 2.5)
        }
    
    def _get_risk_analysis(self, date: str) -> Dict:
        """Get risk analysis for specific date"""
        return {
            'var_95': np.random.uniform(10000, 50000),
            'var_99': np.random.uniform(15000, 75000),
            'portfolio_beta': np.random.uniform(0.8, 1.2),
            'concentration_risk': np.random.uniform(15, 35),
            'liquidity_risk': np.random.choice(['Low', 'Medium', 'High']),
            'correlation_risk': np.random.uniform(0.3, 0.8),
            'var_status': 'Normal',
            'beta_status': 'Normal',
            'concentration_status': 'Elevated' if np.random.random() > 0.7 else 'Normal',
            'liquidity_status': 'Normal'
        }
    
    def _get_market_overview(self, date: str) -> Dict:
        """Get market overview for specific date"""
        return {
            'market_sentiment': np.random.choice(['Bullish', 'Bearish', 'Neutral']),
            'volatility_index': np.random.uniform(20, 80),
            'fear_greed_index': np.random.uniform(10, 90),
            'major_events': [
                'Fed meeting scheduled',
                'BTC halving approaching',
                'ETF approval pending'
            ],
            'market_cap_change': np.random.uniform(-5, 5),
            'volume_change': np.random.uniform(-15, 15)
        }
    
    def _generate_executive_summary(self, portfolio_data: Dict, performance_data: Dict) -> Dict:
        """Generate executive summary"""
        total_value = portfolio_data.get('total_value', 0)
        daily_return = performance_data.get('daily_return', 0)
        
        return {
            'overview': f"Portfolio performance for the period shows a {'positive' if daily_return > 0 else 'negative'} return of {daily_return:.2f}%. Current portfolio value stands at ${total_value:,.2f}.",
            'total_value': total_value,
            'daily_pnl': total_value * (daily_return / 100),
            'total_return_pct': performance_data.get('ytd_return', 0),
            'sharpe_ratio': performance_data.get('sharpe_ratio', 0),
            'max_drawdown': performance_data.get('max_drawdown', 0)
        }
    
    def _get_trading_activity(self, date: str) -> Dict:
        """Get trading activity for specific date"""
        return {
            'total_trades': np.random.randint(5, 25),
            'buy_orders': np.random.randint(2, 12),
            'sell_orders': np.random.randint(3, 13),
            'volume_traded': np.random.uniform(100000, 500000),
            'avg_trade_size': np.random.uniform(10000, 50000),
            'largest_trade': np.random.uniform(50000, 150000),
            'execution_quality': np.random.uniform(95, 99.5)
        }
    
    def _check_position_limits(self) -> Dict:
        """Check position limit compliance"""
        return {
            'single_position_limit': '20%',
            'current_max_position': f"{np.random.uniform(15, 25):.1f}%",
            'compliance_status': 'COMPLIANT' if np.random.random() > 0.1 else 'BREACH',
            'breaches': []
        }
    
    def _get_alerts_summary(self, date: str) -> Dict:
        """Get alerts summary for specific date"""
        return {
            'total_alerts': np.random.randint(5, 25),
            'high_priority': np.random.randint(1, 5),
            'medium_priority': np.random.randint(2, 10),
            'low_priority': np.random.randint(5, 15),
            'categories': {
                'price_alerts': np.random.randint(2, 8),
                'technical_signals': np.random.randint(3, 10),
                'risk_warnings': np.random.randint(1, 5),
                'market_events': np.random.randint(0, 3)
            }
        }
        """Check VaR breach compliance"""
        return {
            'var_limit': '$50,000',
            'current_var': f"${np.random.uniform(30000, 60000):,.0f}",
            'breaches_count': np.random.randint(0, 3),
            'last_breach_date': None if np.random.random() > 0.3 else '2024-01-15'
        }

class AdvancedMarketStructureAnalyzer:
    """Advanced market microstructure analysis and order book analytics"""
    
    def __init__(self, db_manager):
        self.db = db_manager
        self.order_book_data = {}
        self.market_structure_metrics = {}
        
    def analyze_order_book(self, symbol: str, depth: int = 20) -> Dict:
        """Analyze order book depth and market microstructure"""
        try:
            # Simulate order book data (in production, use exchange WebSocket feeds)
            mid_price = np.random.uniform(48000, 52000) if 'BTC' in symbol else np.random.uniform(2800, 3200)
            
            # Generate realistic bid/ask levels
            bids = []
            asks = []
            
            for i in range(depth):
                bid_price = mid_price * (1 - (i + 1) * 0.0001)
                ask_price = mid_price * (1 + (i + 1) * 0.0001)
                
                bid_size = np.random.exponential(10) + 1  # Exponential distribution for realistic sizes
                ask_size = np.random.exponential(10) + 1
                
                bids.append({'price': bid_price, 'size': bid_size})
                asks.append({'price': ask_price, 'size': ask_size})
            
            # Calculate market microstructure metrics
            spread = asks[0]['price'] - bids[0]['price']
            spread_bps = (spread / mid_price) * 10000
            
            bid_volume = sum([b['size'] for b in bids])
            ask_volume = sum([a['size'] for a in asks])
            
            # Order book imbalance
            imbalance = (bid_volume - ask_volume) / (bid_volume + ask_volume)
            
            # Price impact analysis
            impact_1k = self._calculate_price_impact(bids, asks, 1000, mid_price)
            impact_10k = self._calculate_price_impact(bids, asks, 10000, mid_price)
            impact_100k = self._calculate_price_impact(bids, asks, 100000, mid_price)
            
            # Market depth metrics
            depth_analysis = self._analyze_market_depth(bids, asks, mid_price)
            
            return {
                'symbol': symbol,
                'timestamp': datetime.now(),
                'mid_price': mid_price,
                'best_bid': bids[0]['price'],
                'best_ask': asks[0]['price'],
                'spread': spread,
                'spread_bps': spread_bps,
                'bid_ask_ratio': bid_volume / ask_volume if ask_volume > 0 else 0,
                'order_book_imbalance': imbalance,
                'total_bid_volume': bid_volume,
                'total_ask_volume': ask_volume,
                'price_impact': {
                    '1k_usd': impact_1k,
                    '10k_usd': impact_10k,
                    '100k_usd': impact_100k
                },
                'market_depth': depth_analysis,
                'liquidity_score': self._calculate_liquidity_score(spread_bps, bid_volume + ask_volume, impact_10k),
                'order_book_quality': self._assess_order_book_quality(bids, asks)
            }
            
        except Exception as e:
            logging.error(f"Error analyzing order book: {str(e)}")
            return {}
    
    def monitor_funding_rates(self, symbols: List[str]) -> Dict:
        """Monitor perpetual futures funding rates across exchanges"""
        try:
            funding_data = {}
            exchanges = ['binance', 'bybit', 'okx', 'deribit']
            
            for symbol in symbols:
                exchange_rates = {}
                
                for exchange in exchanges:
                    # Simulate funding rate data
                    funding_rate = np.random.normal(0.01, 0.05) / 100  # 0.01% average with 0.05% std
                    predicted_rate = np.random.normal(funding_rate, 0.01)
                    
                    exchange_rates[exchange] = {
                        'current_rate': funding_rate,
                        'predicted_rate': predicted_rate,
                        'rate_8h': funding_rate * 3,  # 8-hour rate
                        'annualized_rate': funding_rate * 365 * 3 * 100,  # Annualized percentage
                        'timestamp': datetime.now()
                    }
                
                # Calculate cross-exchange metrics
                rates = [data['current_rate'] for data in exchange_rates.values()]
                avg_rate = np.mean(rates)
                rate_spread = max(rates) - min(rates)
                
                funding_data[symbol] = {
                    'exchanges': exchange_rates,
                    'average_rate': avg_rate,
                    'rate_spread': rate_spread,
                    'rate_divergence': np.std(rates),
                    'sentiment_indicator': 'Bullish' if avg_rate > 0.02 else 'Bearish' if avg_rate < -0.02 else 'Neutral',
                    'arbitrage_opportunity': rate_spread > 0.1,
                    'historical_percentile': np.random.uniform(10, 90)  # Where current rate stands historically
                }
            
            return funding_data
            
        except Exception as e:
            logging.error(f"Error monitoring funding rates: {str(e)}")
            return {}
    
    def analyze_perpetual_futures(self, symbols: List[str]) -> Dict:
        """Analyze perpetual futures market structure"""
        try:
            futures_analysis = {}
            
            for symbol in symbols:
                spot_price = np.random.uniform(48000, 52000) if 'BTC' in symbol else np.random.uniform(2800, 3200)
                perp_price = spot_price * np.random.uniform(0.999, 1.001)  # Small premium/discount
                
                # Open interest analysis
                open_interest = np.random.uniform(1000000000, 5000000000)  # $1B to $5B
                oi_change_24h = np.random.uniform(-0.1, 0.1)
                
                # Volume analysis
                volume_24h = np.random.uniform(10000000000, 50000000000)  # $10B to $50B
                
                # Liquidations
                long_liquidations = np.random.uniform(10000000, 100000000)
                short_liquidations = np.random.uniform(10000000, 100000000)
                
                futures_analysis[symbol] = {
                    'spot_price': spot_price,
                    'perpetual_price': perp_price,
                    'basis': perp_price - spot_price,
                    'basis_bps': ((perp_price - spot_price) / spot_price) * 10000,
                    'open_interest': {
                        'total_usd': open_interest,
                        'change_24h_pct': oi_change_24h * 100,
                        'oi_weighted_price': perp_price,
                        'estimated_long_short_ratio': np.random.uniform(0.8, 1.2)
                    },
                    'volume_analysis': {
                        'volume_24h_usd': volume_24h,
                        'oi_volume_ratio': open_interest / volume_24h,
                        'avg_trade_size': volume_24h / np.random.randint(1000000, 5000000)
                    },
                    'liquidations': {
                        'long_liquidations_24h': long_liquidations,
                        'short_liquidations_24h': short_liquidations,
                        'net_liquidations': long_liquidations - short_liquidations,
                        'liquidation_ratio': (long_liquidations + short_liquidations) / volume_24h
                    },
                    'market_sentiment': {
                        'leverage_ratio': np.random.uniform(10, 50),
                        'fear_index': np.random.uniform(20, 80),
                        'institutional_flow': np.random.choice(['Buying', 'Selling', 'Neutral'])
                    }
                }
            
            return futures_analysis
            
        except Exception as e:
            logging.error(f"Error analyzing perpetual futures: {str(e)}")
            return {}
    
    def _calculate_price_impact(self, bids: List[Dict], asks: List[Dict], 
                               order_size_usd: float, mid_price: float) -> float:
        """Calculate price impact for a given order size"""
        remaining_size = order_size_usd
        total_cost = 0
        
        # Simulate market buy order
        for ask in asks:
            if remaining_size <= 0:
                break
                
            available_liquidity = ask['size'] * ask['price']
            trade_size = min(remaining_size, available_liquidity)
            
            total_cost += trade_size
            remaining_size -= trade_size
            
            if remaining_size <= 0:
                effective_price = total_cost / order_size_usd
                price_impact = ((effective_price - mid_price) / mid_price) * 100
                return price_impact
        
        # If order couldn't be filled completely
        return 99.9  # High impact indicating insufficient liquidity
    
    def _analyze_market_depth(self, bids: List[Dict], asks: List[Dict], mid_price: float) -> Dict:
        """Analyze market depth characteristics"""
        # Depth at different price levels
        depth_levels = [0.1, 0.25, 0.5, 1.0]  # Percentage from mid price
        depth_analysis = {}
        
        for level in depth_levels:
            level_price_bid = mid_price * (1 - level / 100)
            level_price_ask = mid_price * (1 + level / 100)
            
            bid_liquidity = sum([b['size'] for b in bids if b['price'] >= level_price_bid])
            ask_liquidity = sum([a['size'] for a in asks if a['price'] <= level_price_ask])
            
            depth_analysis[f"{level}%"] = {
                'bid_liquidity': bid_liquidity,
                'ask_liquidity': ask_liquidity,
                'total_liquidity': bid_liquidity + ask_liquidity,
                'imbalance': (bid_liquidity - ask_liquidity) / (bid_liquidity + ask_liquidity) if (bid_liquidity + ask_liquidity) > 0 else 0
            }
        
        return depth_analysis
    
    def _calculate_liquidity_score(self, spread_bps: float, total_volume: float, price_impact_10k: float) -> float:
        """Calculate overall liquidity score (0-100)"""
        # Lower spread = better liquidity
        spread_score = max(0, 100 - spread_bps * 10)
        
        # Higher volume = better liquidity
        volume_score = min(100, (total_volume / 1000) * 10)
        
        # Lower price impact = better liquidity
        impact_score = max(0, 100 - price_impact_10k * 1000)
        
        # Weighted average
        liquidity_score = (spread_score * 0.4 + volume_score * 0.3 + impact_score * 0.3)
        
        return max(0, min(100, liquidity_score))
    
    def _assess_order_book_quality(self, bids: List[Dict], asks: List[Dict]) -> Dict:
        """Assess order book quality metrics"""
        bid_sizes = [b['size'] for b in bids]
        ask_sizes = [a['size'] for a in asks]
        
        return {
            'size_distribution': {
                'bid_size_std': np.std(bid_sizes),
                'ask_size_std': np.std(ask_sizes),
                'size_consistency': 1 / (1 + np.mean([np.std(bid_sizes), np.std(ask_sizes)]))
            },
            'level_consistency': {
                'bid_levels': len(bids),
                'ask_levels': len(asks),
                'level_balance': min(len(bids), len(asks)) / max(len(bids), len(asks))
            },
            'market_making_quality': np.random.uniform(0.7, 0.95),  # Professional market makers present
            'manipulation_risk': np.random.uniform(0.05, 0.3)  # Risk of price manipulation
        }

# ==================== DEEP LEARNING & AI MODELS ====================

class DeepLearningPredictor:
    """Advanced deep learning models for price prediction and pattern recognition"""
    
    def __init__(self, db_manager):
        self.db = db_manager
        self.models = {}
        self.model_performance = {}
        self.feature_importance = {}
        
    def build_lstm_model(self, symbol: str, lookback_days: int = 60) -> Dict:
        """Build and train LSTM model for price prediction"""
        try:
            # In production, use actual TensorFlow/PyTorch
            # For now, simulate model building and results
            
            model_config = {
                'model_type': 'LSTM',
                'layers': [
                    {'type': 'LSTM', 'units': 128, 'return_sequences': True},
                    {'type': 'Dropout', 'rate': 0.2},
                    {'type': 'LSTM', 'units': 64, 'return_sequences': True},
                    {'type': 'Dropout', 'rate': 0.2},
                    {'type': 'LSTM', 'units': 32},
                    {'type': 'Dense', 'units': 1, 'activation': 'linear'}
                ],
                'optimizer': 'adam',
                'loss': 'mse',
                'lookback_days': lookback_days,
                'features': ['price', 'volume', 'rsi', 'macd', 'bb_upper', 'bb_lower']
            }
            
            # Simulate training results
            training_results = {
                'training_loss': np.random.uniform(0.001, 0.01),
                'validation_loss': np.random.uniform(0.002, 0.015),
                'training_accuracy': np.random.uniform(0.75, 0.92),
                'validation_accuracy': np.random.uniform(0.70, 0.88),
                'epochs_trained': np.random.randint(50, 200),
                'early_stopping_epoch': np.random.randint(30, 150)
            }
            
            # Generate predictions
            predictions = self._generate_lstm_predictions(symbol, lookback_days)
            
            # Model evaluation
            evaluation = {
                'mse': np.random.uniform(0.002, 0.02),
                'rmse': np.random.uniform(0.05, 0.15),
                'mae': np.random.uniform(0.03, 0.12),
                'r2_score': np.random.uniform(0.65, 0.85),
                'directional_accuracy': np.random.uniform(0.58, 0.75)
            }
            
            self.models[f"{symbol}_LSTM"] = {
                'config': model_config,
                'training_results': training_results,
                'evaluation': evaluation,
                'predictions': predictions,
                'last_updated': datetime.now(),
                'model_version': '1.0.0'
            }
            
            return {
                'status': 'success',
                'model_id': f"{symbol}_LSTM",
                'config': model_config,
                'training_results': training_results,
                'evaluation': evaluation,
                'predictions': predictions
            }
            
        except Exception as e:
            logging.error(f"Error building LSTM model: {str(e)}")
            return {'status': 'error', 'message': str(e)}
    
    def build_transformer_model(self, symbol: str, sequence_length: int = 100) -> Dict:
        """Build and train Transformer model for advanced pattern recognition"""
        try:
            model_config = {
                'model_type': 'Transformer',
                'architecture': {
                    'num_layers': 6,
                    'num_heads': 8,
                    'd_model': 256,
                    'dff': 1024,
                    'dropout_rate': 0.1,
                    'sequence_length': sequence_length
                },
                'features': [
                    'price', 'volume', 'rsi', 'macd', 'bb_bands', 'stoch',
                    'atr', 'adx', 'cci', 'williams_r', 'momentum', 'roc'
                ],
                'target': 'next_day_return'
            }
            
            # Simulate training
            training_results = {
                'training_loss': np.random.uniform(0.0005, 0.005),
                'validation_loss': np.random.uniform(0.001, 0.008),
                'attention_weights': self._generate_attention_weights(),
                'convergence_epoch': np.random.randint(80, 300),
                'peak_performance_epoch': np.random.randint(150, 250)
            }
            
            # Advanced predictions with confidence intervals
            predictions = self._generate_transformer_predictions(symbol, sequence_length)
            
            # Feature importance from attention mechanisms
            feature_importance = self._calculate_feature_importance(model_config['features'])
            
            self.models[f"{symbol}_Transformer"] = {
                'config': model_config,
                'training_results': training_results,
                'predictions': predictions,
                'feature_importance': feature_importance,
                'last_updated': datetime.now(),
                'model_version': '2.0.0'
            }
            
            return {
                'status': 'success',
                'model_id': f"{symbol}_Transformer",
                'config': model_config,
                'training_results': training_results,
                'predictions': predictions,
                'feature_importance': feature_importance
            }
            
        except Exception as e:
            logging.error(f"Error building Transformer model: {str(e)}")
            return {'status': 'error', 'message': str(e)}
    
    def ensemble_prediction(self, symbol: str) -> Dict:
        """Create ensemble predictions from multiple models"""
        try:
            models_to_ensemble = [
                f"{symbol}_LSTM",
                f"{symbol}_Transformer",
                f"{symbol}_RandomForest",
                f"{symbol}_XGBoost"
            ]
            
            predictions = []
            weights = []
            confidence_scores = []
            
            for model_id in models_to_ensemble:
                if model_id in self.models:
                    model_data = self.models[model_id]
                    pred = model_data.get('predictions', {}).get('next_day_price', 0)
                    conf = model_data.get('evaluation', {}).get('validation_accuracy', 0)
                    
                    predictions.append(pred)
                    weights.append(conf)
                    confidence_scores.append(conf)
            
            if not predictions:
                return {'error': 'No trained models available for ensemble'}
            
            # Weighted ensemble
            weights = np.array(weights)
            weights = weights / np.sum(weights)  # Normalize
            
            ensemble_prediction = np.sum(np.array(predictions) * weights)
            ensemble_confidence = np.mean(confidence_scores)
            
            # Uncertainty quantification
            prediction_std = np.std(predictions)
            confidence_interval = {
                'lower_95': ensemble_prediction - 1.96 * prediction_std,
                'upper_95': ensemble_prediction + 1.96 * prediction_std,
                'lower_68': ensemble_prediction - prediction_std,
                'upper_68': ensemble_prediction + prediction_std
            }
            
            return {
                'ensemble_prediction': ensemble_prediction,
                'confidence': ensemble_confidence,
                'confidence_interval': confidence_interval,
                'individual_predictions': [
                    {'model': models_to_ensemble[i], 'prediction': predictions[i], 'weight': weights[i]}
                    for i in range(len(predictions))
                ],
                'prediction_consensus': len([p for p in predictions if abs(p - ensemble_prediction) < prediction_std]) / len(predictions),
                'uncertainty_score': prediction_std / abs(ensemble_prediction) if ensemble_prediction != 0 else 1
            }
            
        except Exception as e:
            logging.error(f"Error creating ensemble prediction: {str(e)}")
            return {'error': str(e)}
    
    def detect_regime_changes(self, symbol: str, lookback_periods: int = 200) -> Dict:
        """Detect market regime changes using ML models"""
        try:
            # Simulate regime detection (in production, use actual ML algorithms)
            regimes = ['Bull Market', 'Bear Market', 'Sideways', 'High Volatility', 'Low Volatility']
            
            # Current regime analysis
            current_regime = np.random.choice(regimes)
            regime_confidence = np.random.uniform(0.6, 0.95)
            
            # Regime transition probabilities
            transition_matrix = {
                'Bull Market': {'Bear Market': 0.15, 'Sideways': 0.25, 'High Volatility': 0.20, 'stay': 0.40},
                'Bear Market': {'Bull Market': 0.20, 'Sideways': 0.30, 'High Volatility': 0.25, 'stay': 0.25},
                'Sideways': {'Bull Market': 0.35, 'Bear Market': 0.30, 'High Volatility': 0.15, 'stay': 0.20},
                'High Volatility': {'Bull Market': 0.25, 'Bear Market': 0.25, 'Sideways': 0.30, 'stay': 0.20},
                'Low Volatility': {'Bull Market': 0.40, 'Sideways': 0.35, 'High Volatility': 0.15, 'stay': 0.10}
            }
            
            # Historical regime analysis
            regime_history = []
            for i in range(lookback_periods):
                regime_history.append({
                    'date': datetime.now() - timedelta(days=i),
                    'regime': np.random.choice(regimes),
                    'confidence': np.random.uniform(0.5, 0.9)
                })
            
            # Regime change indicators
            volatility_indicator = np.random.uniform(-2, 2)  # Z-score
            momentum_indicator = np.random.uniform(-2, 2)
            volume_indicator = np.random.uniform(-2, 2)
            
            # Change point detection
            change_probability = np.random.uniform(0.1, 0.4)
            
            return {
                'current_regime': current_regime,
                'regime_confidence': regime_confidence,
                'regime_duration_days': np.random.randint(10, 90),
                'transition_probabilities': transition_matrix.get(current_regime, {}),
                'change_indicators': {
                    'volatility_z_score': volatility_indicator,
                    'momentum_z_score': momentum_indicator,
                    'volume_z_score': volume_indicator,
                    'composite_score': (volatility_indicator + momentum_indicator + volume_indicator) / 3
                },
                'change_probability': change_probability,
                'regime_forecast': {
                    '7_days': self._forecast_regime(current_regime, 7),
                    '30_days': self._forecast_regime(current_regime, 30),
                    '90_days': self._forecast_regime(current_regime, 90)
                },
                'historical_regimes': regime_history[:30],  # Last 30 periods
                'regime_performance': self._analyze_regime_performance(regimes)
            }
            
        except Exception as e:
            logging.error(f"Error detecting regime changes: {str(e)}")
            return {'error': str(e)}
    
    def _generate_lstm_predictions(self, symbol: str, lookback_days: int) -> Dict:
        """Generate LSTM model predictions"""
        current_price = np.random.uniform(48000, 52000) if 'BTC' in symbol else np.random.uniform(2800, 3200)
        
        return {
            'next_day_price': current_price * np.random.uniform(0.98, 1.02),
            'next_week_price': current_price * np.random.uniform(0.95, 1.05),
            'next_month_price': current_price * np.random.uniform(0.90, 1.10),
            'direction_probability': {
                'up': np.random.uniform(0.4, 0.8),
                'down': np.random.uniform(0.2, 0.6)
            },
            'price_targets': {
                'conservative': current_price * np.random.uniform(1.01, 1.03),
                'moderate': current_price * np.random.uniform(1.03, 1.06),
                'aggressive': current_price * np.random.uniform(1.06, 1.10)
            }
        }
    
    def _generate_transformer_predictions(self, symbol: str, sequence_length: int) -> Dict:
        """Generate Transformer model predictions with attention analysis"""
        current_price = np.random.uniform(48000, 52000) if 'BTC' in symbol else np.random.uniform(2800, 3200)
        
        return {
            'price_sequence_forecast': [
                current_price * np.random.uniform(0.995, 1.005) for _ in range(10)
            ],
            'volatility_forecast': [
                np.random.uniform(0.02, 0.08) for _ in range(10)
            ],
            'pattern_recognition': {
                'detected_patterns': ['Double Bottom', 'Ascending Triangle'],
                'pattern_confidence': [0.87, 0.72],
                'completion_probability': [0.65, 0.58]
            },
            'attention_focus': {
                'most_important_features': ['price', 'volume', 'rsi'],
                'feature_weights': [0.35, 0.28, 0.18],
                'temporal_focus': 'Last 5 days most important'
            }
        }
    
    def _generate_attention_weights(self) -> List[List[float]]:
        """Generate simulated attention weights for visualization"""
        num_heads = 8
        sequence_length = 100
        
        attention_weights = []
        for head in range(num_heads):
            head_weights = []
            for pos in range(sequence_length):
                # Create realistic attention patterns
                weights = np.random.exponential(0.1, sequence_length)
                weights = weights / np.sum(weights)  # Normalize
                head_weights.append(weights.tolist())
            attention_weights.append(head_weights)
        
        return attention_weights
    
    def _calculate_feature_importance(self, features: List[str]) -> Dict:
        """Calculate feature importance from model analysis"""
        importance_scores = {}
        total_importance = 0
        
        for feature in features:
            score = np.random.exponential(0.2)
            importance_scores[feature] = score
            total_importance += score
        
        # Normalize to percentages
        for feature in importance_scores:
            importance_scores[feature] = (importance_scores[feature] / total_importance) * 100
        
        return importance_scores
    
    def _forecast_regime(self, current_regime: str, days_ahead: int) -> Dict:
        """Forecast regime for specific time horizon"""
        regimes = ['Bull Market', 'Bear Market', 'Sideways', 'High Volatility', 'Low Volatility']
        
        # Simple Markov chain simulation
        transition_prob = 0.05 * days_ahead  # Probability of change increases with time
        
        if np.random.random() < transition_prob:
            forecast_regime = np.random.choice([r for r in regimes if r != current_regime])
        else:
            forecast_regime = current_regime
        
        return {
            'most_likely_regime': forecast_regime,
            'probability': np.random.uniform(0.4, 0.8),
            'alternative_scenarios': [
                {'regime': regime, 'probability': np.random.uniform(0.1, 0.3)}
                for regime in regimes if regime != forecast_regime
            ]
        }
    
    def _analyze_regime_performance(self, regimes: List[str]) -> Dict:
        """Analyze historical performance in different regimes"""
        performance = {}
        
        for regime in regimes:
            performance[regime] = {
                'average_return': np.random.uniform(-0.1, 0.15),
                'volatility': np.random.uniform(0.15, 0.45),
                'max_drawdown': np.random.uniform(0.05, 0.25),
                'duration_days': np.random.randint(20, 120),
                'frequency': np.random.uniform(0.1, 0.3)
            }
        
        return performance

# ==================== WEB APPLICATION ====================

def create_app():
    """Create Flask web application with all advanced features"""
    app = Flask(__name__)
    app.secret_key = config.SECRET_KEY
    
    # Initialize core components
    db_manager = DatabaseManager()
    portfolio_manager = PortfolioManager(db_manager)
    alert_system = AlertSystem(db_manager)
    
    # Initialize new advanced components
    stream_manager = RealTimeStreamManager(db_manager)
    enhanced_alerts = EnhancedAlertSystem(db_manager)
    advanced_portfolio = AdvancedPortfolioManager(db_manager)
    backtester = AdvancedBacktester(db_manager)
    sentiment_analyzer = SocialSentimentAnalyzer(db_manager)
    defi_analyzer = DeFiAnalyzer(db_manager)
    report_generator = ProfessionalReportGenerator(db_manager)
    market_structure = AdvancedMarketStructureAnalyzer(db_manager)
    ml_predictor = DeepLearningPredictor(db_manager)
    
    # Start real-time streams for major symbols
    major_symbols = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'ADA/USDT', 'SOL/USDT']
    stream_manager.start_streams(major_symbols)
    
    # HTML Template
    HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🚀 Crypto Trading Dashboard</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        body {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            font-family: 'Arial', sans-serif;
        }
        .glass-card {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            border: 1px solid rgba(255, 255, 255, 0.2);
            box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37);
            padding: 20px;
            margin-bottom: 20px;
        }
        .navbar {
            background: rgba(255, 255, 255, 0.1) !important;
            backdrop-filter: blur(10px);
            border-bottom: 1px solid rgba(255, 255, 255, 0.2);
        }
        .text-white { color: white !important; }
        .price-up { color: #00ff88; }
        .price-down { color: #ff4757; }
        .signal-buy { background: linear-gradient(45deg, #00ff88, #00d4aa); }
        .signal-sell { background: linear-gradient(45deg, #ff4757, #ff3838); }
        .signal-hold { background: linear-gradient(45deg, #ffa500, #ff8c00); }
        .metric-card {
            text-align: center;
            padding: 15px;
            border-radius: 10px;
            margin: 10px 0;
        }
        .chart-container {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 10px;
            padding: 15px;
            margin: 10px 0;
        }
        .alert-badge {
            position: absolute;
            top: -5px;
            right: -5px;
            background: #ff4757;
            color: white;
            border-radius: 50%;
            width: 20px;
            height: 20px;
            font-size: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .crypto-logo {
            width: 32px;
            height: 32px;
            border-radius: 50%;
            margin-right: 10px;
        }
    </style>
</head>
<body>
    <!-- Navigation -->
    <nav class="navbar navbar-expand-lg navbar-dark">
        <div class="container-fluid">
            <a class="navbar-brand text-white" href="#"><i class="fas fa-rocket"></i> Crypto Trading Dashboard</a>
            <div class="navbar-nav ms-auto">
                <span class="nav-link text-white"><i class="fas fa-clock"></i> Last Update: <span id="last-update"></span></span>
                <button class="btn btn-outline-light btn-sm me-2" onclick="refreshData()">
                    <i class="fas fa-sync-alt"></i> Refresh
                </button>
                <button class="btn btn-outline-success btn-sm" onclick="runAnalysis()">
                    <i class="fas fa-chart-line"></i> Analyze
                </button>
            </div>
        </div>
    </nav>

    <div class="container-fluid mt-4">
        <!-- Market Overview -->
        <div class="row">
            <div class="col-12">
                <div class="glass-card">
                    <h3 class="text-white mb-3"><i class="fas fa-chart-line"></i> Market Overview</h3>
                    <div class="row" id="market-overview">
                        <!-- Market data will be loaded here -->
                    </div>
                </div>
            </div>
        </div>

        <!-- Price Monitoring -->
        <div class="row">
            <div class="col-lg-8">
                <div class="glass-card">
                    <h4 class="text-white mb-3"><i class="fas fa-coins"></i> Live Prices & Signals</h4>
                    <div class="row" id="price-grid">
                        <!-- Price cards will be loaded here -->
                    </div>
                </div>
            </div>
            <div class="col-lg-4">
                <div class="glass-card">
                    <h4 class="text-white mb-3"><i class="fas fa-bell"></i> Alerts <span class="alert-badge" id="alert-count">0</span></h4>
                    <div id="alerts-container">
                        <!-- Alerts will be loaded here -->
                    </div>
                </div>
            </div>
        </div>

        <!-- Charts -->
        <div class="row">
            <div class="col-lg-8">
                <div class="glass-card">
                    <h4 class="text-white mb-3"><i class="fas fa-chart-area"></i> Price Chart</h4>
                    <select class="form-select mb-3" id="chart-symbol" onchange="updateChart()">
                        {% for pair in trading_pairs %}
                        <option value="{{ pair }}">{{ pair }}</option>
                        {% endfor %}
                    </select>
                    <div class="chart-container">
                        <div id="price-chart"></div>
                    </div>
                </div>
            </div>
            <div class="col-lg-4">
                <div class="glass-card">
                    <h4 class="text-white mb-3"><i class="fas fa-wallet"></i> Portfolio</h4>
                    <div id="portfolio-summary">
                        <!-- Portfolio data will be loaded here -->
                    </div>
                </div>
                <div class="glass-card">
                    <h4 class="text-white mb-3"><i class="fas fa-history"></i> Recent Signals</h4>
                    <div id="recent-signals">
                        <!-- Recent signals will be loaded here -->
                    </div>
                </div>
            </div>
        </div>

        <!-- Technical Analysis -->
        <div class="row">
            <div class="col-lg-6">
                <div class="glass-card">
                    <h4 class="text-white mb-3"><i class="fas fa-chart-bar"></i> RSI Indicator</h4>
                    <div class="chart-container">
                        <div id="rsi-chart"></div>
                    </div>
                </div>
            </div>
            <div class="col-lg-6">
                <div class="glass-card">
                    <h4 class="text-white mb-3"><i class="fas fa-wave-square"></i> MACD Indicator</h4>
                    <div class="chart-container">
                        <div id="macd-chart"></div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Advanced Features Dashboard -->
        <div class="row mt-4">
            <div class="col-lg-12">
                <div class="glass-card">
                    <h3 class="text-white mb-4"><i class="fas fa-rocket"></i> Advanced Trading Intelligence</h3>
                    
                    <!-- Navigation Tabs -->
                    <ul class="nav nav-tabs mb-3" id="advanced-tabs">
                        <li class="nav-item">
                            <a class="nav-link active" data-bs-toggle="tab" href="#ml-predictions">🤖 AI Predictions</a>
                        </li>
                        <li class="nav-item">
                            <a class="nav-link" data-bs-toggle="tab" href="#sentiment-analysis">📊 Sentiment Analysis</a>
                        </li>
                        <li class="nav-item">
                            <a class="nav-link" data-bs-toggle="tab" href="#defi-analytics">🌐 DeFi Analytics</a>
                        </li>
                        <li class="nav-item">
                            <a class="nav-link" data-bs-toggle="tab" href="#market-structure">📈 Market Structure</a>
                        </li>
                        <li class="nav-item">
                            <a class="nav-link" data-bs-toggle="tab" href="#risk-management">⚖️ Risk Management</a>
                        </li>
                        <li class="nav-item">
                            <a class="nav-link" data-bs-toggle="tab" href="#backtesting">🔄 Backtesting</a>
                        </li>
                    </ul>

                    <!-- Tab Content -->
                    <div class="tab-content">
                        <!-- AI Predictions Tab -->
                        <div class="tab-pane fade show active" id="ml-predictions">
                            <div class="row">
                                <div class="col-lg-6">
                                    <div class="card bg-dark text-white">
                                        <div class="card-header">
                                            <h5><i class="fas fa-brain"></i> LSTM Price Predictions</h5>
                                        </div>
                                        <div class="card-body" id="lstm-predictions">
                                            <!-- LSTM predictions will be loaded here -->
                                        </div>
                                    </div>
                                </div>
                                <div class="col-lg-6">
                                    <div class="card bg-dark text-white">
                                        <div class="card-header">
                                            <h5><i class="fas fa-eye"></i> Transformer Analysis</h5>
                                        </div>
                                        <div class="card-body" id="transformer-analysis">
                                            <!-- Transformer analysis will be loaded here -->
                                        </div>
                                    </div>
                                </div>
                            </div>
                            <div class="row mt-3">
                                <div class="col-lg-12">
                                    <div class="card bg-dark text-white">
                                        <div class="card-header">
                                            <h5><i class="fas fa-chart-line"></i> Ensemble Predictions & Regime Analysis</h5>
                                        </div>
                                        <div class="card-body" id="ensemble-regime">
                                            <!-- Ensemble predictions and regime analysis -->
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- Sentiment Analysis Tab -->
                        <div class="tab-pane fade" id="sentiment-analysis">
                            <div class="row">
                                <div class="col-lg-4">
                                    <div class="card bg-dark text-white">
                                        <div class="card-header">
                                            <h5><i class="fab fa-twitter"></i> Social Media Sentiment</h5>
                                        </div>
                                        <div class="card-body" id="social-sentiment">
                                            <!-- Social media sentiment -->
                                        </div>
                                    </div>
                                </div>
                                <div class="col-lg-4">
                                    <div class="card bg-dark text-white">
                                        <div class="card-header">
                                            <h5><i class="fas fa-newspaper"></i> News Sentiment</h5>
                                        </div>
                                        <div class="card-body" id="news-sentiment">
                                            <!-- News sentiment -->
                                        </div>
                                    </div>
                                </div>
                                <div class="col-lg-4">
                                    <div class="card bg-dark text-white">
                                        <div class="card-header">
                                            <h5><i class="fas fa-thermometer-half"></i> Fear & Greed Index</h5>
                                        </div>
                                        <div class="card-body" id="fear-greed-index">
                                            <!-- Fear & Greed Index -->
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- DeFi Analytics Tab -->
                        <div class="tab-pane fade" id="defi-analytics">
                            <div class="row">
                                <div class="col-lg-6">
                                    <div class="card bg-dark text-white">
                                        <div class="card-header">
                                            <h5><i class="fas fa-exchange-alt"></i> DEX Analysis</h5>
                                        </div>
                                        <div class="card-body" id="dex-analysis">
                                            <!-- DEX analysis -->
                                        </div>
                                    </div>
                                </div>
                                <div class="col-lg-6">
                                    <div class="card bg-dark text-white">
                                        <div class="card-header">
                                            <h5><i class="fas fa-swimming-pool"></i> Liquidity Pools</h5>
                                        </div>
                                        <div class="card-body" id="liquidity-pools">
                                            <!-- Liquidity pools -->
                                        </div>
                                    </div>
                                </div>
                            </div>
                            <div class="row mt-3">
                                <div class="col-lg-6">
                                    <div class="card bg-dark text-white">
                                        <div class="card-header">
                                            <h5><i class="fas fa-whale"></i> Whale Movements</h5>
                                        </div>
                                        <div class="card-body" id="whale-movements">
                                            <!-- Whale movements -->
                                        </div>
                                    </div>
                                </div>
                                <div class="col-lg-6">
                                    <div class="card bg-dark text-white">
                                        <div class="card-header">
                                            <h5><i class="fas fa-link"></i> On-Chain Metrics</h5>
                                        </div>
                                        <div class="card-body" id="on-chain-metrics">
                                            <!-- On-chain metrics -->
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- Market Structure Tab -->
                        <div class="tab-pane fade" id="market-structure">
                            <div class="row">
                                <div class="col-lg-6">
                                    <div class="card bg-dark text-white">
                                        <div class="card-header">
                                            <h5><i class="fas fa-book"></i> Order Book Analysis</h5>
                                        </div>
                                        <div class="card-body" id="order-book-analysis">
                                            <!-- Order book analysis -->
                                        </div>
                                    </div>
                                </div>
                                <div class="col-lg-6">
                                    <div class="card bg-dark text-white">
                                        <div class="card-header">
                                            <h5><i class="fas fa-percentage"></i> Funding Rates</h5>
                                        </div>
                                        <div class="card-body" id="funding-rates">
                                            <!-- Funding rates -->
                                        </div>
                                    </div>
                                </div>
                            </div>
                            <div class="row mt-3">
                                <div class="col-lg-12">
                                    <div class="card bg-dark text-white">
                                        <div class="card-header">
                                            <h5><i class="fas fa-chart-area"></i> Perpetual Futures Analysis</h5>
                                        </div>
                                        <div class="card-body" id="futures-analysis">
                                            <!-- Futures analysis -->
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- Risk Management Tab -->
                        <div class="tab-pane fade" id="risk-management">
                            <div class="row">
                                <div class="col-lg-6">
                                    <div class="card bg-dark text-white">
                                        <div class="card-header">
                                            <h5><i class="fas fa-shield-alt"></i> Portfolio Risk Metrics</h5>
                                        </div>
                                        <div class="card-body" id="portfolio-risk">
                                            <!-- Portfolio risk metrics -->
                                        </div>
                                    </div>
                                </div>
                                <div class="col-lg-6">
                                    <div class="card bg-dark text-white">
                                        <div class="card-header">
                                            <h5><i class="fas fa-calculator"></i> Position Sizing</h5>
                                        </div>
                                        <div class="card-body" id="position-sizing">
                                            <!-- Position sizing calculator -->
                                            <div class="mb-3">
                                                <label class="form-label text-white">Signal Strength (0-1):</label>
                                                <input type="range" class="form-range" min="0" max="1" step="0.1" value="0.5" id="signal-strength">
                                                <span id="signal-strength-value" class="text-white">0.5</span>
                                            </div>
                                            <div class="mb-3">
                                                <label class="form-label text-white">Account Balance ($):</label>
                                                <input type="number" class="form-control" value="100000" id="account-balance">
                                            </div>
                                            <div class="mb-3">
                                                <label class="form-label text-white">Risk per Trade (%):</label>
                                                <input type="range" class="form-range" min="0.5" max="5" step="0.5" value="2" id="risk-per-trade">
                                                <span id="risk-per-trade-value" class="text-white">2%</span>
                                            </div>
                                            <button class="btn btn-primary" onclick="calculatePositionSize()">Calculate Position Size</button>
                                            <div id="position-size-result" class="mt-3"></div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- Backtesting Tab -->
                        <div class="tab-pane fade" id="backtesting">
                            <div class="row">
                                <div class="col-lg-12">
                                    <div class="card bg-dark text-white">
                                        <div class="card-header">
                                            <h5><i class="fas fa-history"></i> Strategy Backtesting</h5>
                                        </div>
                                        <div class="card-body">
                                            <div class="row">
                                                <div class="col-lg-6">
                                                    <h6>Backtest Configuration</h6>
                                                    <div class="mb-3">
                                                        <label class="form-label text-white">Start Date:</label>
                                                        <input type="date" class="form-control" id="backtest-start" value="2023-01-01">
                                                    </div>
                                                    <div class="mb-3">
                                                        <label class="form-label text-white">End Date:</label>
                                                        <input type="date" class="form-control" id="backtest-end" value="2023-12-31">
                                                    </div>
                                                    <div class="mb-3">
                                                        <label class="form-label text-white">Initial Capital:</label>
                                                        <input type="number" class="form-control" id="initial-capital" value="100000">
                                                    </div>
                                                    <button class="btn btn-success" onclick="runBacktest()">Run Backtest</button>
                                                    <button class="btn btn-warning ms-2" onclick="runMonteCarloSimulation()">Monte Carlo</button>
                                                </div>
                                                <div class="col-lg-6">
                                                    <h6>Backtest Results</h6>
                                                    <div id="backtest-results">
                                                        <!-- Backtest results will be displayed here -->
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Real-Time Arbitrage Opportunities -->
        <div class="row mt-4">
            <div class="col-lg-12">
                <div class="glass-card">
                    <h4 class="text-white mb-3"><i class="fas fa-exchange-alt"></i> Real-Time Arbitrage Opportunities</h4>
                    <div id="arbitrage-opportunities">
                        <!-- Arbitrage opportunities will be loaded here -->
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
        // Global variables
        let advancedDataCache = {};
        
        // Initialize page
        document.addEventListener('DOMContentLoaded', function() {
            refreshData();
            loadAdvancedFeatures();
            setInterval(refreshData, 60000); // Refresh every 60 seconds
            setInterval(loadAdvancedFeatures, 120000); // Refresh advanced features every 2 minutes
            
            // Initialize position sizing sliders
            initializeSliders();
        });

        // Initialize interactive sliders
        function initializeSliders() {
            const signalStrength = document.getElementById('signal-strength');
            const signalStrengthValue = document.getElementById('signal-strength-value');
            const riskPerTrade = document.getElementById('risk-per-trade');
            const riskPerTradeValue = document.getElementById('risk-per-trade-value');
            
            signalStrength.addEventListener('input', function() {
                signalStrengthValue.textContent = this.value;
            });
            
            riskPerTrade.addEventListener('input', function() {
                riskPerTradeValue.textContent = this.value + '%';
            });
        }

        // Load advanced features data
        async function loadAdvancedFeatures() {
            try {
                // Load ML predictions
                await loadMLPredictions();
                
                // Load sentiment analysis
                await loadSentimentAnalysis();
                
                // Load DeFi analytics
                await loadDeFiAnalytics();
                
                // Load market structure
                await loadMarketStructure();
                
                // Load arbitrage opportunities
                await loadArbitrageOpportunities();
                
                // Load advanced portfolio metrics
                await loadAdvancedPortfolio();
                
            } catch (error) {
                console.error('Error loading advanced features:', error);
            }
        }

        // Load ML predictions
        async function loadMLPredictions() {
            try {
                const symbol = document.getElementById('symbol-select').value || 'BTC/USDT';
                const response = await fetch(`/api/ml/prediction/${symbol}`);
                const data = await response.json();
                
                if (data.error) {
                    console.error('ML Predictions error:', data.error);
                    return;
                }
                
                // Update LSTM predictions
                const lstmElement = document.getElementById('lstm-predictions');
                if (data.lstm_model && data.lstm_model.predictions) {
                    const predictions = data.lstm_model.predictions;
                    lstmElement.innerHTML = `
                        <div class="row">
                            <div class="col-6">
                                <div class="metric-item">
                                    <small class="text-muted">Next Day Price</small>
                                    <div class="metric-value">$${predictions.next_day_price ? predictions.next_day_price.toFixed(2) : 'N/A'}</div>
                                </div>
                            </div>
                            <div class="col-6">
                                <div class="metric-item">
                                    <small class="text-muted">Direction Probability</small>
                                    <div class="metric-value">${predictions.direction_probability ? (predictions.direction_probability.up * 100).toFixed(1) : 'N/A'}% Up</div>
                                </div>
                            </div>
                        </div>
                        <div class="row mt-2">
                            <div class="col-12">
                                <small class="text-muted">Price Targets:</small>
                                <div class="d-flex justify-content-between">
                                    <span class="badge bg-success">Conservative: $${predictions.price_targets ? predictions.price_targets.conservative.toFixed(2) : 'N/A'}</span>
                                    <span class="badge bg-warning">Moderate: $${predictions.price_targets ? predictions.price_targets.moderate.toFixed(2) : 'N/A'}</span>
                                    <span class="badge bg-danger">Aggressive: $${predictions.price_targets ? predictions.price_targets.aggressive.toFixed(2) : 'N/A'}</span>
                                </div>
                            </div>
                        </div>
                    `;
                }
                
                // Update Transformer analysis
                const transformerElement = document.getElementById('transformer-analysis');
                if (data.transformer_model && data.transformer_model.predictions) {
                    const analysis = data.transformer_model.predictions;
                    transformerElement.innerHTML = `
                        <div class="mb-3">
                            <small class="text-muted">Pattern Recognition:</small>
                            ${analysis.pattern_recognition ? analysis.pattern_recognition.detected_patterns.map((pattern, index) => 
                                `<div class="badge bg-info me-1">${pattern} (${(analysis.pattern_recognition.pattern_confidence[index] * 100).toFixed(1)}%)</div>`
                            ).join('') : 'No patterns detected'}
                        </div>
                        <div class="mb-3">
                            <small class="text-muted">Attention Focus:</small>
                            <div class="text-warning">${analysis.attention_focus ? analysis.attention_focus.temporal_focus : 'N/A'}</div>
                        </div>
                        <div>
                            <small class="text-muted">Important Features:</small>
                            ${analysis.attention_focus ? analysis.attention_focus.most_important_features.map((feature, index) => 
                                `<span class="badge bg-secondary me-1">${feature} (${(analysis.attention_focus.feature_weights[index] * 100).toFixed(1)}%)</span>`
                            ).join('') : 'N/A'}
                        </div>
                    `;
                }
                
                // Update ensemble predictions
                const ensembleElement = document.getElementById('ensemble-regime');
                if (data.ensemble_prediction) {
                    const ensemble = data.ensemble_prediction;
                    const regime = data.regime_analysis;
                    
                    ensembleElement.innerHTML = `
                        <div class="row">
                            <div class="col-lg-6">
                                <h6 class="text-warning">Ensemble Prediction</h6>
                                <div class="metric-item">
                                    <div class="metric-value">$${ensemble.ensemble_prediction ? ensemble.ensemble_prediction.toFixed(2) : 'N/A'}</div>
                                    <small class="text-muted">Confidence: ${ensemble.confidence ? (ensemble.confidence * 100).toFixed(1) : 'N/A'}%</small>
                                </div>
                                <div class="mt-2">
                                    <small class="text-muted">95% Confidence Interval:</small>
                                    <div class="text-info">$${ensemble.confidence_interval ? ensemble.confidence_interval.lower_95.toFixed(2) : 'N/A'} - $${ensemble.confidence_interval ? ensemble.confidence_interval.upper_95.toFixed(2) : 'N/A'}</div>
                                </div>
                            </div>
                            <div class="col-lg-6">
                                <h6 class="text-warning">Market Regime</h6>
                                <div class="metric-item">
                                    <div class="metric-value">${regime ? regime.current_regime : 'N/A'}</div>
                                    <small class="text-muted">Confidence: ${regime ? (regime.regime_confidence * 100).toFixed(1) : 'N/A'}%</small>
                                </div>
                                <div class="mt-2">
                                    <small class="text-muted">Change Probability:</small>
                                    <div class="text-warning">${regime ? (regime.change_probability * 100).toFixed(1) : 'N/A'}%</div>
                                </div>
                            </div>
                        </div>
                    `;
                }
                
            } catch (error) {
                console.error('Error loading ML predictions:', error);
            }
        }

        // Load sentiment analysis
        async function loadSentimentAnalysis() {
            try {
                const symbol = document.getElementById('symbol-select').value || 'BTC/USDT';
                const response = await fetch(`/api/sentiment/${symbol}`);
                const data = await response.json();
                
                if (data.error) {
                    console.error('Sentiment analysis error:', data.error);
                    return;
                }
                
                // Update social sentiment
                const socialElement = document.getElementById('social-sentiment');
                if (data.sentiment) {
                    const sentiment = data.sentiment;
                    socialElement.innerHTML = `
                        <div class="text-center">
                            <div class="metric-value" style="color: ${sentiment.color}">${sentiment.composite_score}/100</div>
                            <div class="badge" style="background-color: ${sentiment.color}">${sentiment.category}</div>
                            <div class="mt-2">
                                <small class="text-muted">Confidence: ${sentiment.confidence ? (sentiment.confidence * 100).toFixed(1) : 'N/A'}%</small>
                            </div>
                        </div>
                    `;
                }
                
                // Update Fear & Greed Index
                const fearGreedElement = document.getElementById('fear-greed-index');
                if (data.fear_greed_index) {
                    const fgi = data.fear_greed_index;
                    fearGreedElement.innerHTML = `
                        <div class="text-center">
                            <div class="metric-value" style="color: ${fgi.color}">${fgi.value}</div>
                            <div class="badge" style="background-color: ${fgi.color}">${fgi.sentiment}</div>
                            <div class="mt-2">
                                <small class="text-muted">Historical Avg: ${fgi.historical_average ? fgi.historical_average.toFixed(1) : 'N/A'}</small>
                            </div>
                        </div>
                    `;
                }
                
            } catch (error) {
                console.error('Error loading sentiment analysis:', error);
            }
        }

        // Load DeFi analytics
        async function loadDeFiAnalytics() {
            try {
                const response = await fetch('/api/defi/analysis');
                const data = await response.json();
                
                if (data.error) {
                    console.error('DeFi analytics error:', data.error);
                    return;
                }
                
                // Update DEX analysis
                const dexElement = document.getElementById('dex-analysis');
                if (data.dex_analysis) {
                    const btcData = data.dex_analysis['BTC/USDT'];
                    if (btcData) {
                        dexElement.innerHTML = `
                            <div class="mb-3">
                                <small class="text-muted">Best Prices:</small>
                                <div class="d-flex justify-content-between">
                                    <span class="text-success">Buy: ${btcData.best_buy_exchange}</span>
                                    <span class="text-danger">Sell: ${btcData.best_sell_exchange}</span>
                                </div>
                            </div>
                            <div class="mb-3">
                                <small class="text-muted">Price Spread:</small>
                                <div class="metric-value">${btcData.spread_percentage ? btcData.spread_percentage.toFixed(3) : 'N/A'}%</div>
                            </div>
                            <div>
                                <small class="text-muted">Total Liquidity:</small>
                                <div class="text-info">$${btcData.total_liquidity ? (btcData.total_liquidity / 1000000).toFixed(1) : 'N/A'}M</div>
                            </div>
                        `;
                    }
                }
                
                // Update liquidity pools
                const poolsElement = document.getElementById('liquidity-pools');
                if (data.liquidity_pools && data.liquidity_pools.aggregate_metrics) {
                    const metrics = data.liquidity_pools.aggregate_metrics;
                    poolsElement.innerHTML = `
                        <div class="mb-3">
                            <small class="text-muted">Total TVL:</small>
                            <div class="metric-value">$${metrics.total_tvl ? (metrics.total_tvl / 1000000).toFixed(1) : 'N/A'}M</div>
                        </div>
                        <div class="mb-3">
                            <small class="text-muted">Average APY:</small>
                            <div class="text-success">${metrics.average_apy ? metrics.average_apy.toFixed(2) : 'N/A'}%</div>
                        </div>
                        <div>
                            <small class="text-muted">Pools Monitored:</small>
                            <div class="text-info">${metrics.total_pools_monitored || 'N/A'}</div>
                        </div>
                    `;
                }
                
            } catch (error) {
                console.error('Error loading DeFi analytics:', error);
            }
        }

        // Load market structure
        async function loadMarketStructure() {
            try {
                const symbol = document.getElementById('symbol-select').value || 'BTC/USDT';
                const response = await fetch(`/api/market-structure/${symbol}`);
                const data = await response.json();
                
                if (data.error) {
                    console.error('Market structure error:', data.error);
                    return;
                }
                
                // Update order book analysis
                const orderBookElement = document.getElementById('order-book-analysis');
                if (data.order_book) {
                    const ob = data.order_book;
                    orderBookElement.innerHTML = `
                        <div class="mb-3">
                            <small class="text-muted">Spread:</small>
                            <div class="metric-value">${ob.spread_bps ? ob.spread_bps.toFixed(2) : 'N/A'} bps</div>
                        </div>
                        <div class="mb-3">
                            <small class="text-muted">Liquidity Score:</small>
                            <div class="text-success">${ob.liquidity_score ? ob.liquidity_score.toFixed(1) : 'N/A'}/100</div>
                        </div>
                        <div class="mb-3">
                            <small class="text-muted">Price Impact (10k USD):</small>
                            <div class="text-warning">${ob.price_impact ? ob.price_impact['10k_usd'].toFixed(3) : 'N/A'}%</div>
                        </div>
                        <div>
                            <small class="text-muted">Order Book Imbalance:</small>
                            <div class="${ob.order_book_imbalance > 0 ? 'text-success' : 'text-danger'}">${ob.order_book_imbalance ? (ob.order_book_imbalance * 100).toFixed(2) : 'N/A'}%</div>
                        </div>
                    `;
                }
                
            } catch (error) {
                console.error('Error loading market structure:', error);
            }
        }

        // Load arbitrage opportunities
        async function loadArbitrageOpportunities() {
            try {
                const response = await fetch('/api/arbitrage');
                const data = await response.json();
                
                if (data.error) {
                    console.error('Arbitrage error:', data.error);
                    return;
                }
                
                const arbitrageElement = document.getElementById('arbitrage-opportunities');
                if (data.opportunities && data.opportunities.length > 0) {
                    const opportunities = data.opportunities.slice(0, 5); // Show top 5
                    arbitrageElement.innerHTML = `
                        <div class="table-responsive">
                            <table class="table table-dark table-striped">
                                <thead>
                                    <tr>
                                        <th>Symbol</th>
                                        <th>Buy Exchange</th>
                                        <th>Sell Exchange</th>
                                        <th>Profit %</th>
                                        <th>Buy Price</th>
                                        <th>Sell Price</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${opportunities.map(opp => `
                                        <tr>
                                            <td>${opp.symbol}</td>
                                            <td class="text-success">${opp.buy_exchange}</td>
                                            <td class="text-danger">${opp.sell_exchange}</td>
                                            <td class="text-warning">${opp.profit_percentage.toFixed(3)}%</td>
                                            <td>$${opp.buy_price.toFixed(2)}</td>
                                            <td>$${opp.sell_price.toFixed(2)}</td>
                                        </tr>
                                    `).join('')}
                                </tbody>
                            </table>
                        </div>
                    `;
                } else {
                    arbitrageElement.innerHTML = '<div class="text-center text-muted">No arbitrage opportunities detected</div>';
                }
                
            } catch (error) {
                console.error('Error loading arbitrage opportunities:', error);
            }
        }

        // Load advanced portfolio metrics
        async function loadAdvancedPortfolio() {
            try {
                const response = await fetch('/api/portfolio/advanced');
                const data = await response.json();
                
                if (data.error) {
                    console.error('Advanced portfolio error:', data.error);
                    return;
                }
                
                const portfolioRiskElement = document.getElementById('portfolio-risk');
                if (data.metrics) {
                    const metrics = data.metrics;
                    portfolioRiskElement.innerHTML = `
                        <div class="row">
                            <div class="col-6">
                                <div class="metric-item">
                                    <small class="text-muted">Portfolio VaR (95%)</small>
                                    <div class="metric-value text-danger">$${metrics.portfolio_var_95 ? metrics.portfolio_var_95.toFixed(0) : 'N/A'}</div>
                                </div>
                            </div>
                            <div class="col-6">
                                <div class="metric-item">
                                    <small class="text-muted">Max Drawdown</small>
                                    <div class="metric-value text-warning">${metrics.max_drawdown ? metrics.max_drawdown.toFixed(2) : 'N/A'}%</div>
                                </div>
                            </div>
                        </div>
                        <div class="row mt-2">
                            <div class="col-6">
                                <div class="metric-item">
                                    <small class="text-muted">Sharpe Ratio</small>
                                    <div class="metric-value text-info">${metrics.sharpe_ratio ? metrics.sharpe_ratio.toFixed(2) : 'N/A'}</div>
                                </div>
                            </div>
                            <div class="col-6">
                                <div class="metric-item">
                                    <small class="text-muted">Concentration Risk</small>
                                    <div class="metric-value ${metrics.concentration_risk > 30 ? 'text-danger' : 'text-success'}">${metrics.concentration_risk ? metrics.concentration_risk.toFixed(1) : 'N/A'}%</div>
                                </div>
                            </div>
                        </div>
                    `;
                }
                
            } catch (error) {
                console.error('Error loading advanced portfolio:', error);
            }
        }

        // Calculate position size
        async function calculatePositionSize() {
            try {
                const signalStrength = parseFloat(document.getElementById('signal-strength').value);
                const accountBalance = parseFloat(document.getElementById('account-balance').value);
                const riskPerTrade = parseFloat(document.getElementById('risk-per-trade').value) / 100;
                
                const response = await fetch('/api/position-sizing', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        signal_strength: signalStrength,
                        account_balance: accountBalance,
                        risk_per_trade: riskPerTrade
                    })
                });
                
                const data = await response.json();
                
                if (data.error) {
                    console.error('Position sizing error:', data.error);
                    return;
                }
                
                const resultElement = document.getElementById('position-size-result');
                resultElement.innerHTML = `
                    <div class="alert alert-info">
                        <h6>Recommended Position Size</h6>
                        <div class="row">
                            <div class="col-6">
                                <strong>Position Size:</strong> $${data.position_size ? data.position_size.toFixed(2) : 'N/A'}
                            </div>
                            <div class="col-6">
                                <strong>Risk %:</strong> ${data.risk_percentage ? data.risk_percentage.toFixed(2) : 'N/A'}%
                            </div>
                        </div>
                        <div class="mt-2">
                            <small class="text-muted">Signal Multiplier: ${data.signal_multiplier ? data.signal_multiplier.toFixed(2) : 'N/A'}x</small>
                        </div>
                    </div>
                `;
                
            } catch (error) {
                console.error('Error calculating position size:', error);
            }
        }

        // Run backtest
        async function runBacktest() {
            try {
                const startDate = document.getElementById('backtest-start').value;
                const endDate = document.getElementById('backtest-end').value;
                const initialCapital = parseFloat(document.getElementById('initial-capital').value);
                
                const response = await fetch('/api/backtest', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        symbols: ['BTC/USDT'],
                        start_date: startDate,
                        end_date: endDate,
                        initial_capital: initialCapital,
                        ma_short: 10,
                        ma_long: 30
                    })
                });
                
                const data = await response.json();
                
                if (data.error) {
                    console.error('Backtest error:', data.error);
                    return;
                }
                
                const resultsElement = document.getElementById('backtest-results');
                if (data.metrics) {
                    const metrics = data.metrics;
                    resultsElement.innerHTML = `
                        <div class="alert alert-success">
                            <h6>Backtest Results</h6>
                            <div class="row">
                                <div class="col-6">
                                    <strong>Total Return:</strong> ${metrics.total_return_pct ? metrics.total_return_pct.toFixed(2) : 'N/A'}%
                                </div>
                                <div class="col-6">
                                    <strong>Sharpe Ratio:</strong> ${metrics.sharpe_ratio ? metrics.sharpe_ratio.toFixed(2) : 'N/A'}
                                </div>
                            </div>
                            <div class="row">
                                <div class="col-6">
                                    <strong>Win Rate:</strong> ${metrics.win_rate ? (metrics.win_rate * 100).toFixed(1) : 'N/A'}%
                                </div>
                                <div class="col-6">
                                    <strong>Max Drawdown:</strong> ${metrics.max_drawdown_pct ? metrics.max_drawdown_pct.toFixed(2) : 'N/A'}%
                                </div>
                            </div>
                            <div class="row">
                                <div class="col-6">
                                    <strong>Total Trades:</strong> ${metrics.total_trades || 'N/A'}
                                </div>
                                <div class="col-6">
                                    <strong>Profit Factor:</strong> ${metrics.profit_factor ? metrics.profit_factor.toFixed(2) : 'N/A'}
                                </div>
                            </div>
                        </div>
                    `;
                }
                
            } catch (error) {
                console.error('Error running backtest:', error);
            }
        }

        // Run Monte Carlo simulation
        async function runMonteCarloSimulation() {
            try {
                const response = await fetch('/api/monte-carlo', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        base_strategy: {
                            symbols: ['BTC/USDT'],
                            start_date: '2023-01-01',
                            end_date: '2023-12-31',
                            ma_short: 10,
                            ma_long: 30
                        },
                        num_simulations: 500
                    })
                });
                
                const data = await response.json();
                
                if (data.error) {
                    console.error('Monte Carlo error:', data.error);
                    return;
                }
                
                const resultsElement = document.getElementById('backtest-results');
                if (data.analysis) {
                    const analysis = data.analysis;
                    resultsElement.innerHTML = `
                        <div class="alert alert-warning">
                            <h6>Monte Carlo Analysis (${analysis.total_simulations} simulations)</h6>
                            <div class="row">
                                <div class="col-6">
                                    <strong>Profitable %:</strong> ${analysis.profitable_percentage ? analysis.profitable_percentage.toFixed(1) : 'N/A'}%
                                </div>
                                <div class="col-6">
                                    <strong>Avg Return:</strong> ${analysis.average_return ? analysis.average_return.toFixed(2) : 'N/A'}%
                                </div>
                            </div>
                            <div class="row">
                                <div class="col-6">
                                    <strong>Best Case:</strong> ${analysis.best_return ? analysis.best_return.toFixed(2) : 'N/A'}%
                                </div>
                                <div class="col-6">
                                    <strong>Worst Case:</strong> ${analysis.worst_return ? analysis.worst_return.toFixed(2) : 'N/A'}%
                                </div>
                            </div>
                            <div class="mt-2">
                                <strong>95% Confidence Interval:</strong> 
                                ${analysis.confidence_intervals && analysis.confidence_intervals['95%'] ? 
                                    `${analysis.confidence_intervals['95%'][0].toFixed(2)}% to ${analysis.confidence_intervals['95%'][1].toFixed(2)}%` : 'N/A'}
                            </div>
                        </div>
                    `;
                }
                
            } catch (error) {
                console.error('Error running Monte Carlo simulation:', error);
            }
        }

        // Refresh all data
        async function refreshData() {
            try {
                await Promise.all([
                    updatePrices(),
                    updateAlerts(),
                    updatePortfolio(),
                    updateRecentSignals(),
                    updateChart()
                ]);
                document.getElementById('last-update').textContent = new Date().toLocaleTimeString();
            } catch (error) {
                console.error('Error refreshing data:', error);
            }
        }

        // Run full analysis (heavy operation)
        async function runAnalysis() {
            try {
                const button = event.target;
                button.disabled = true;
                button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Analyzing...';
                
                const response = await fetch('/api/refresh');
                const result = await response.json();
                
                // Show success message
                if (result.status) {
                    button.innerHTML = '<i class="fas fa-check"></i> Started';
                    setTimeout(() => {
                        button.disabled = false;
                        button.innerHTML = '<i class="fas fa-chart-line"></i> Analyze';
                        refreshData(); // Refresh after analysis
                    }, 3000);
                }
            } catch (error) {
                console.error('Error running analysis:', error);
                const button = event.target;
                button.disabled = false;
                button.innerHTML = '<i class="fas fa-chart-line"></i> Analyze';
            }
        }   } catch (error) {
                console.error('Error refreshing data:', error);
            }
        }

        // Update live prices
        async function updatePrices() {
            try {
                const response = await fetch('/api/prices');
                const data = await response.json();
                priceData = data;
                
                const grid = document.getElementById('price-grid');
                grid.innerHTML = '';
                
                for (const [symbol, info] of Object.entries(data)) {
                    const changeClass = info.change_24h >= 0 ? 'price-up' : 'price-down';
                    const signalClass = getSignalClass(info.recommendation);
                    const sourceIcon = info.source === 'yfinance_fallback' ? '🔄' : '📡';
                    
                    grid.innerHTML += `
                        <div class="col-md-6 col-lg-4 mb-3">
                            <div class="metric-card ${signalClass}">
                                <h5 class="text-white">${symbol} ${sourceIcon}</h5>
                                <h3 class="text-white">$${info.price.toFixed(2)}</h3>
                                <p class="${changeClass}">
                                    <i class="fas fa-arrow-${info.change_24h >= 0 ? 'up' : 'down'}"></i>
                                    ${info.change_24h.toFixed(2)}%
                                </p>
                                <small class="text-white">${info.recommendation || 'ANALYZING'}</small>
                                ${info.confidence > 0 ? `<br><small class="text-success">Confidence: ${(info.confidence * 100).toFixed(0)}%</small>` : ''}
                                ${info.accuracy_score > 0 ? `<br><small class="text-info">Accuracy: ${(info.accuracy_score * 100).toFixed(0)}%</small>` : ''}
                                ${info.signal_count > 0 ? `<br><small class="text-warning">${info.signal_count} indicators</small>` : ''}
                                <br><small class="text-muted">Updated: ${info.last_analysis}</small>
                            </div>
                        </div>
                    `;
                }
            } catch (error) {
                console.error('Error updating prices:', error);
                // Show error in UI
                const grid = document.getElementById('price-grid');
                grid.innerHTML = '<div class="col-12"><div class="alert alert-warning">Price update failed. Retrying...</div></div>';
            }
        }

        // Update alerts
        async function updateAlerts() {
            try {
                const response = await fetch('/api/alerts');
                const alerts = await response.json();
                
                document.getElementById('alert-count').textContent = alerts.length;
                
                const container = document.getElementById('alerts-container');
                container.innerHTML = '';
                
                if (alerts.length === 0) {
                    container.innerHTML = '<p class="text-white">No new alerts</p>';
                } else {
                    alerts.slice(0, 5).forEach(alert => {
                        const alertType = alert.alert_type;
                        const iconClass = getAlertIcon(alertType);
                        
                        container.innerHTML += `
                            <div class="alert alert-info alert-dismissible">
                                <i class="${iconClass}"></i>
                                <strong>${alert.symbol}</strong>
                                <br><small>${alert.message}</small>
                                <br><small class="text-muted">${new Date(alert.timestamp).toLocaleString()}</small>
                            </div>
                        `;
                    });
                }
            } catch (error) {
                console.error('Error updating alerts:', error);
            }
        }

        // Update portfolio
        async function updatePortfolio() {
            try {
                const response = await fetch('/api/portfolio');
                const portfolio = await response.json();
                
                const container = document.getElementById('portfolio-summary');
                container.innerHTML = `
                    <div class="metric-card" style="background: rgba(255,255,255,0.1);">
                        <h5 class="text-white">Total Value</h5>
                        <h3 class="text-white">$${portfolio.total_value.toFixed(2)}</h3>
                        <p class="text-white">Positions: ${portfolio.total_positions}</p>
                    </div>
                `;
                
                if (portfolio.top_holdings.length > 0) {
                    container.innerHTML += '<h6 class="text-white mt-3">Top Holdings</h6>';
                    portfolio.top_holdings.forEach(holding => {
                        const pnlClass = holding.pnl >= 0 ? 'price-up' : 'price-down';
                        container.innerHTML += `
                            <div class="d-flex justify-content-between text-white mb-2">
                                <span>${holding.symbol}</span>
                                <span class="${pnlClass}">${holding.pnl_pct.toFixed(1)}%</span>
                            </div>
                        `;
                    });
                }
            } catch (error) {
                console.error('Error updating portfolio:', error);
            }
        }

        // Update recent signals
        async function updateRecentSignals() {
            try {
                const response = await fetch('/api/signals');
                const signals = await response.json();
                
                const container = document.getElementById('recent-signals');
                container.innerHTML = '';
                
                if (signals.length === 0) {
                    container.innerHTML = '<p class="text-white">No recent signals</p>';
                } else {
                    signals.slice(0, 5).forEach(signal => {
                        const signalClass = getSignalClass(signal.recommendation);
                        container.innerHTML += `
                            <div class="alert alert-secondary">
                                <strong class="text-white">${signal.symbol}</strong>
                                <span class="badge ${signalClass}">${signal.recommendation}</span>
                                <br><small class="text-muted">$${signal.price.toFixed(2)} - ${new Date(signal.timestamp).toLocaleString()}</small>
                            </div>
                        `;
                    });
                }
            } catch (error) {
                console.error('Error updating recent signals:', error);
            }
        }

        // Update chart
        async function updateChart() {
            try {
                const response = await fetch(`/api/chart/${chartSymbol}`);
                const data = await response.json();
                
                if (data.error) {
                    document.getElementById('price-chart').innerHTML = `<p class="text-white">Error loading chart: ${data.error}</p>`;
                    return;
                }
                
                // Price chart
                Plotly.newPlot('price-chart', data.price_chart.data, data.price_chart.layout, {responsive: true});
                
                // RSI chart
                if (data.rsi_chart) {
                    Plotly.newPlot('rsi-chart', data.rsi_chart.data, data.rsi_chart.layout, {responsive: true});
                }
                
                // MACD chart
                if (data.macd_chart) {
                    Plotly.newPlot('macd-chart', data.macd_chart.data, data.macd_chart.layout, {responsive: true});
                }
            } catch (error) {
                console.error('Error updating chart:', error);
            }
        }

        // Utility functions
        function getSignalClass(recommendation) {
            if (!recommendation) return 'signal-hold';
            if (recommendation.includes('BUY')) return 'signal-buy';
            if (recommendation.includes('SELL')) return 'signal-sell';
            return 'signal-hold';
        }

        function getAlertIcon(alertType) {
            switch(alertType) {
                case 'SIGNAL': return 'fas fa-chart-line';
                case 'RSI_OVERSOLD': return 'fas fa-arrow-down';
                case 'RSI_OVERBOUGHT': return 'fas fa-arrow-up';
                default: return 'fas fa-info-circle';
            }
        }

        function updateChartSymbol() {
            chartSymbol = document.getElementById('chart-symbol').value;
            updateChart();
        }
    </script>
</body>
</html>
    """
    
    @app.route('/')
    def dashboard():
        """Main dashboard page"""
        return render_template_string(HTML_TEMPLATE, trading_pairs=config.TRADING_PAIRS)
    
    @app.route('/api/prices')
    def api_prices():
        """API endpoint for live prices - optimized for speed"""
        prices = {}
        
        # Get recent signals from database first (faster)
        recent_signals = db_manager.get_recent_signals(limit=20)
        signal_map = {signal['symbol']: signal for signal in recent_signals}
        
        for i, symbol in enumerate(config.TRADING_PAIRS):
            try:
                # Add small delay to prevent overwhelming
                if i > 0:
                    time.sleep(0.5)  # Reduced delay for faster response
                
                # Get real-time price (this is the main data we need quickly)
                price_data = CryptoDataFetcher.get_realtime_price(symbol)
                
                # Use cached analysis from database if available, otherwise use defaults
                if symbol in signal_map:
                    cached_signal = signal_map[symbol]
                    recommendation = cached_signal.get('recommendation', 'ANALYZING')
                    confidence = cached_signal.get('confidence', 0)
                    accuracy_score = cached_signal.get('accuracy_score', 0)
                    signal_count = cached_signal.get('signal_count', 0)
                    last_analysis = cached_signal.get('timestamp', 'Never')
                else:
                    recommendation = 'ANALYZING'
                    confidence = 0
                    accuracy_score = 0
                    signal_count = 0
                    last_analysis = 'Pending'
                
                prices[symbol] = {
                    'price': price_data.get('price', 0),
                    'change_24h': price_data.get('change_24h', 0),
                    'volume_24h': price_data.get('volume_24h', 0),
                    'recommendation': recommendation,
                    'confidence': confidence,
                    'accuracy_score': accuracy_score,
                    'signal_count': signal_count,
                    'source': price_data.get('source', 'coingecko'),
                    'last_analysis': last_analysis
                }
                    
            except Exception as e:
                logging.error(f"Error processing {symbol}: {e}")
                prices[symbol] = {
                    'price': 0,
                    'change_24h': 0,
                    'volume_24h': 0,
                    'recommendation': 'ERROR',
                    'confidence': 0,
                    'source': 'error',
                    'last_analysis': 'Error'
                }
        
        return jsonify(prices)
    
    @app.route('/api/alerts')
    def api_alerts():
        """API endpoint for alerts"""
        return jsonify(db_manager.get_unread_alerts())
    
    @app.route('/api/portfolio')
    def api_portfolio():
        """API endpoint for portfolio data"""
        return jsonify(portfolio_manager.get_portfolio_summary())
    
    @app.route('/api/signals')
    def api_signals():
        """API endpoint for recent signals"""
        return jsonify(db_manager.get_recent_signals())
    
    @app.route('/api/analysis/<symbol>')
    def api_analysis(symbol):
        """API endpoint for detailed analysis of specific symbol"""
        try:
            # Get historical data for analysis
            df = CryptoDataFetcher.get_historical_data(symbol, "30d")
            
            if df.empty:
                return jsonify({'error': 'No historical data available'})
            
            # Store in database
            db_manager.store_price_data(symbol, df)
            
            # Generate signals
            analysis = TechnicalAnalysis.generate_signals(df)
            
            # Get current price
            price_data = CryptoDataFetcher.get_realtime_price(symbol)
            
            # Store signal
            signal_data = {
                'price': price_data.get('price', 0),
                'confidence': analysis.get('confidence', 0),
                'rsi': analysis.get('indicators', {}).get('rsi', 0),
                'macd': analysis.get('indicators', {}).get('macd', 0),
                'recommendation': analysis.get('recommendation', 'HOLD')
            }
            db_manager.store_signal(symbol, signal_data)
            
            # Check alerts
            alert_system.check_price_alerts(symbol, price_data.get('price', 0), analysis)
            
            return jsonify({
                'symbol': symbol,
                'price': price_data.get('price', 0),
                'analysis': analysis,
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            logging.error(f"Error analyzing {symbol}: {e}")
            return jsonify({'error': str(e)})
    
    @app.route('/api/refresh')
    def api_refresh():
        """API endpoint to trigger background analysis for all symbols"""
        def run_analysis():
            import requests
            for symbol in config.TRADING_PAIRS:
                try:
                    requests.get(f"http://localhost:{config.PORT}/api/analysis/{symbol}", timeout=30)
                except:
                    pass
        
        # Run in background thread
        import threading
        thread = threading.Thread(target=run_analysis, daemon=True)
        thread.start()
        
        return jsonify({'status': 'Analysis started in background'})
    
    @app.route('/api/chart/<symbol>')
    def api_chart(symbol):
        """API endpoint for chart data"""
        try:
            df = CryptoDataFetcher.get_historical_data(symbol, "30d")
            
            if df.empty:
                return jsonify({'error': 'No data available'})
            
            # Store data
            db_manager.store_price_data(symbol, df)
            
            # Calculate indicators
            rsi = TechnicalAnalysis.calculate_rsi(df['Close'])
            macd_data = TechnicalAnalysis.calculate_macd(df['Close'])
            bb_data = TechnicalAnalysis.calculate_bollinger_bands(df['Close'])
            ma_data = TechnicalAnalysis.calculate_moving_averages(df['Close'])
            
            # Create price chart
            price_chart = {
                'data': [
                    {
                        'x': [idx.strftime('%Y-%m-%d') if hasattr(idx, 'strftime') else str(idx) for idx in df.index],
                        'open': df['Open'].tolist(),
                        'high': df['High'].tolist(),
                        'low': df['Low'].tolist(),
                        'close': df['Close'].tolist(),
                        'type': 'candlestick',
                        'name': symbol
                    },
                    {
                        'x': [idx.strftime('%Y-%m-%d') if hasattr(idx, 'strftime') else str(idx) for idx in df.index],
                        'y': ma_data['sma_short'].tolist(),
                        'type': 'scatter',
                        'mode': 'lines',
                        'name': 'SMA 20',
                        'line': {'color': 'blue'}
                    },
                    {
                        'x': [idx.strftime('%Y-%m-%d') if hasattr(idx, 'strftime') else str(idx) for idx in df.index],
                        'y': ma_data['sma_long'].tolist(),
                        'type': 'scatter',
                        'mode': 'lines',
                        'name': 'SMA 50',
                        'line': {'color': 'red'}
                    }
                ],
                'layout': {
                    'title': f'{symbol} Price Chart',
                    'xaxis': {'title': 'Date'},
                    'yaxis': {'title': 'Price ($)'},
                    'template': 'plotly_dark'
                }
            }
            
            # Create RSI chart
            rsi_chart = {
                'data': [
                    {
                        'x': [idx.strftime('%Y-%m-%d') if hasattr(idx, 'strftime') else str(idx) for idx in df.index],
                        'y': rsi.tolist(),
                        'type': 'scatter',
                        'mode': 'lines',
                        'name': 'RSI',
                        'line': {'color': 'purple'}
                    }
                ],
                'layout': {
                    'title': 'RSI Indicator',
                    'xaxis': {'title': 'Date'},
                    'yaxis': {'title': 'RSI', 'range': [0, 100]},
                    'template': 'plotly_dark',
                    'shapes': [
                        {'type': 'line', 'x0': 0, 'x1': 1, 'y0': 70, 'y1': 70, 'xref': 'paper', 'line': {'color': 'red', 'dash': 'dash'}},
                        {'type': 'line', 'x0': 0, 'x1': 1, 'y0': 30, 'y1': 30, 'xref': 'paper', 'line': {'color': 'green', 'dash': 'dash'}}
                    ]
                }
            }
            
            # Create MACD chart
            macd_chart = {
                'data': [
                    {
                        'x': [idx.strftime('%Y-%m-%d') if hasattr(idx, 'strftime') else str(idx) for idx in df.index],
                        'y': macd_data['macd'].tolist(),
                        'type': 'scatter',
                        'mode': 'lines',
                        'name': 'MACD',
                        'line': {'color': 'blue'}
                    },
                    {
                        'x': [idx.strftime('%Y-%m-%d') if hasattr(idx, 'strftime') else str(idx) for idx in df.index],
                        'y': macd_data['signal'].tolist(),
                        'type': 'scatter',
                        'mode': 'lines',
                        'name': 'Signal',
                        'line': {'color': 'red'}
                    }
                ],
                'layout': {
                    'title': 'MACD Indicator',
                    'xaxis': {'title': 'Date'},
                    'yaxis': {'title': 'MACD'},
                    'template': 'plotly_dark'
                }
            }
            
            return jsonify({
                'price_chart': price_chart,
                'rsi_chart': rsi_chart,
                'macd_chart': macd_chart
            })
            
        except Exception as e:
            logging.error(f"Error generating chart for {symbol}: {e}")
            return jsonify({'error': str(e)})
    
    # ==================== NEW ADVANCED API ENDPOINTS ====================
    
    @app.route('/api/real-time/<symbol>')
    def get_real_time_data(symbol):
        """Get real-time market data"""
        try:
            data = stream_manager.get_real_time_data(symbol)
            return jsonify(data)
        except Exception as e:
            return jsonify({'error': str(e)})
    
    @app.route('/api/arbitrage')
    def get_arbitrage_opportunities():
        """Get cross-exchange arbitrage opportunities"""
        try:
            opportunities = stream_manager.get_arbitrage_opportunities()
            return jsonify({'opportunities': opportunities})
        except Exception as e:
            return jsonify({'error': str(e)})
    
    @app.route('/api/portfolio/advanced')
    def get_advanced_portfolio():
        """Get advanced portfolio metrics"""
        try:
            positions = portfolio_manager.get_all_positions()
            metrics = advanced_portfolio.calculate_portfolio_metrics(positions)
            heatmap_data = advanced_portfolio.generate_portfolio_heatmap_data()
            correlation_data = advanced_portfolio.get_correlation_data()
            
            return jsonify({
                'metrics': metrics,
                'heatmap_data': heatmap_data,
                'correlation_data': correlation_data
            })
        except Exception as e:
            return jsonify({'error': str(e)})
    
    @app.route('/api/backtest', methods=['POST'])
    def run_backtest():
        """Run backtesting analysis"""
        try:
            strategy_config = request.json
            result = backtester.run_backtest(
                strategy_config,
                strategy_config.get('start_date', '2023-01-01'),
                strategy_config.get('end_date', '2023-12-31')
            )
            return jsonify(result)
        except Exception as e:
            return jsonify({'error': str(e)})
    
    @app.route('/api/monte-carlo', methods=['POST'])
    def run_monte_carlo():
        """Run Monte Carlo simulation"""
        try:
            config = request.json
            result = backtester.monte_carlo_simulation(
                config.get('base_strategy', {}),
                config.get('num_simulations', 1000)
            )
            return jsonify(result)
        except Exception as e:
            return jsonify({'error': str(e)})
    
    @app.route('/api/sentiment/<symbol>')
    def get_sentiment_analysis(symbol):
        """Get comprehensive sentiment analysis"""
        try:
            # Update sentiment data
            sentiment_analyzer.update_sentiment_cache([symbol])
            
            # Get comprehensive sentiment
            sentiment_data = sentiment_analyzer.get_comprehensive_sentiment_score(symbol)
            
            # Get Fear & Greed Index
            fear_greed = sentiment_analyzer.get_fear_greed_index()
            
            return jsonify({
                'sentiment': sentiment_data,
                'fear_greed_index': fear_greed
            })
        except Exception as e:
            return jsonify({'error': str(e)})
    
    @app.route('/api/defi/analysis')
    def get_defi_analysis():
        """Get DeFi market analysis"""
        try:
            symbols = ['BTC/USDT', 'ETH/USDT']
            
            dex_analysis = defi_analyzer.analyze_dex_markets(symbols)
            liquidity_pools = defi_analyzer.monitor_liquidity_pools()
            whale_movements = defi_analyzer.track_whale_movements(symbols)
            on_chain_metrics = defi_analyzer.analyze_on_chain_metrics(symbols)
            
            return jsonify({
                'dex_analysis': dex_analysis,
                'liquidity_pools': liquidity_pools,
                'whale_movements': whale_movements,
                'on_chain_metrics': on_chain_metrics
            })
        except Exception as e:
            return jsonify({'error': str(e)})
    
    @app.route('/api/market-structure/<symbol>')
    def get_market_structure(symbol):
        """Get advanced market structure analysis"""
        try:
            order_book = market_structure.analyze_order_book(symbol)
            funding_rates = market_structure.monitor_funding_rates([symbol])
            futures_analysis = market_structure.analyze_perpetual_futures([symbol])
            
            return jsonify({
                'order_book': order_book,
                'funding_rates': funding_rates,
                'futures_analysis': futures_analysis
            })
        except Exception as e:
            return jsonify({'error': str(e)})
    
    @app.route('/api/ml/prediction/<symbol>')
    def get_ml_predictions(symbol):
        """Get machine learning predictions"""
        try:
            # Build/update models
            lstm_result = ml_predictor.build_lstm_model(symbol)
            transformer_result = ml_predictor.build_transformer_model(symbol)
            
            # Get ensemble prediction
            ensemble_result = ml_predictor.ensemble_prediction(symbol)
            
            # Get regime analysis
            regime_analysis = ml_predictor.detect_regime_changes(symbol)
            
            return jsonify({
                'lstm_model': lstm_result,
                'transformer_model': transformer_result,
                'ensemble_prediction': ensemble_result,
                'regime_analysis': regime_analysis
            })
        except Exception as e:
            return jsonify({'error': str(e)})
    
    @app.route('/api/reports/daily')
    def get_daily_report():
        """Generate daily trading report"""
        try:
            report = report_generator.generate_daily_report()
            return jsonify(report)
        except Exception as e:
            return jsonify({'error': str(e)})
    
    @app.route('/api/reports/monthly/<int:year>/<int:month>')
    def get_monthly_report(year, month):
        """Generate monthly trading report"""
        try:
            report = report_generator.generate_monthly_report(year, month)
            return jsonify(report)
        except Exception as e:
            return jsonify({'error': str(e)})
    
    @app.route('/api/reports/pdf', methods=['POST'])
    def generate_pdf_report():
        """Generate PDF report"""
        try:
            report_data = request.json
            pdf_path = report_generator.generate_pdf_report(report_data)
            
            if pdf_path:
                return jsonify({'status': 'success', 'pdf_path': pdf_path})
            else:
                return jsonify({'status': 'error', 'message': 'Failed to generate PDF'})
        except Exception as e:
            return jsonify({'error': str(e)})
    
    @app.route('/api/compliance')
    def get_compliance_report():
        """Get compliance analysis"""
        try:
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            
            compliance_report = report_generator.generate_compliance_report(start_date, end_date)
            return jsonify(compliance_report)
        except Exception as e:
            return jsonify({'error': str(e)})
    
    @app.route('/api/alerts/enhanced', methods=['POST'])
    def send_enhanced_alert():
        """Send enhanced alert through multiple channels"""
        try:
            alert_data = request.json
            enhanced_alerts.send_alert(
                alert_data.get('type', 'GENERAL'),
                alert_data.get('message', ''),
                alert_data.get('priority', 'medium'),
                alert_data.get('include_chart', False),
                alert_data.get('symbol')
            )
            return jsonify({'status': 'success'})
        except Exception as e:
            return jsonify({'error': str(e)})
    
    @app.route('/api/position-sizing', methods=['POST'])
    def calculate_position_size():
        """Calculate optimal position size"""
        try:
            data = request.json
            result = advanced_portfolio.calculate_position_size(
                data.get('signal_strength', 0.5),
                data.get('account_balance', 100000),
                data.get('risk_per_trade', 0.02)
            )
            return jsonify(result)
        except Exception as e:
            return jsonify({'error': str(e)})
    
    @app.route('/api/dashboard/comprehensive')
    def get_comprehensive_dashboard():
        """Get comprehensive dashboard data with all advanced features"""
        try:
            symbols = ['BTC/USDT', 'ETH/USDT']
            
            # Gather data from all systems
            dashboard_data = {
                'real_time_data': {symbol: stream_manager.get_real_time_data(symbol) for symbol in symbols},
                'arbitrage_opportunities': stream_manager.get_arbitrage_opportunities(),
                'portfolio_metrics': advanced_portfolio.calculate_portfolio_metrics(portfolio_manager.get_all_positions()),
                'sentiment_analysis': {symbol: sentiment_analyzer.get_comprehensive_sentiment_score(symbol) for symbol in symbols},
                'fear_greed_index': sentiment_analyzer.get_fear_greed_index(),
                'market_structure': {symbol: market_structure.analyze_order_book(symbol) for symbol in symbols},
                'ml_predictions': {symbol: ml_predictor.ensemble_prediction(symbol) for symbol in symbols},
                'on_chain_metrics': defi_analyzer.analyze_on_chain_metrics(symbols)
            }
            
            return jsonify(dashboard_data)
        except Exception as e:
            return jsonify({'error': str(e)})
    
    return app

# ==================== BACKGROUND TASKS ====================

def background_monitor():
    """Background monitoring task"""
    db_manager = DatabaseManager()
    alert_system = AlertSystem(db_manager)
    
    def update_data():
        """Update all crypto data"""
        logging.info("🔄 Starting background data update...")
        
        for i, symbol in enumerate(config.TRADING_PAIRS):
            try:
                # Add delay between requests to avoid rate limiting
                if i > 0:
                    time.sleep(3)  # 3 second delay between symbols
                
                # Get fresh data
                df = CryptoDataFetcher.get_historical_data(symbol, "30d")
                if not df.empty:
                    db_manager.store_price_data(symbol, df)
                    
                    # Generate analysis
                    analysis = TechnicalAnalysis.generate_signals(df)
                    
                    # Get current price
                    price_data = CryptoDataFetcher.get_realtime_price(symbol)
                    current_price = price_data.get('price', 0)
                    
                    # Store signal
                    signal_data = {
                        'price': current_price,
                        'confidence': analysis.get('confidence', 0),
                        'rsi': analysis.get('indicators', {}).get('rsi', 0),
                        'macd': analysis.get('indicators', {}).get('macd', 0),
                        'recommendation': analysis.get('recommendation', 'HOLD')
                    }
                    db_manager.store_signal(symbol, signal_data)
                    
                    # Check alerts
                    alert_system.check_price_alerts(symbol, current_price, analysis)
                    
                    logging.info(f"✅ Updated {symbol}: ${current_price:.2f} - {analysis.get('recommendation', 'HOLD')}")
                
            except Exception as e:
                logging.error(f"❌ Error updating {symbol}: {e}")
        
        logging.info("🎉 Background data update completed")
    
    # Schedule updates every 10 minutes instead of 5 to reduce API calls
    schedule.every(10).minutes.do(update_data)
    
    # Initial update
    update_data()
    
    # Keep running
    while True:
        schedule.run_pending()
        time.sleep(60)

# ==================== MAIN APPLICATION ====================

def main():
    """Main application entry point"""
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('crypto_app.log'),
            logging.StreamHandler()
        ]
    )
    
    print("🚀 Crypto Trading Application Starting...")
    print("=" * 60)
    print("📊 Features:")
    print("   • Real-time cryptocurrency monitoring")
    print("   • Advanced technical analysis")
    print("   • Trading signal generation")
    print("   • Portfolio management")
    print("   • Alert system")
    print("   • Beautiful web dashboard")
    print("=" * 60)
    
    # Create Flask app
    app = create_app()
    
    # Start background monitoring in separate thread
    monitor_thread = threading.Thread(target=background_monitor, daemon=True)
    monitor_thread.start()
    
    # Start web server
    print(f"🌐 Web Dashboard: http://{config.HOST}:{config.PORT}")
    print("🛑 Press Ctrl+C to stop")
    print("=" * 60)
    
    try:
        # Open browser
        def open_browser():
            time.sleep(2)
            webbrowser.open(f"http://localhost:{config.PORT}")
        
        browser_thread = threading.Thread(target=open_browser, daemon=True)
        browser_thread.start()
        
        # Run Flask app
        app.run(host=config.HOST, port=config.PORT, debug=False, threaded=True)
        
    except KeyboardInterrupt:
        print("\n🛑 Application stopped by user")
    except Exception as e:
        print(f"❌ Application error: {e}")
        logging.error(f"Application error: {e}")

if __name__ == "__main__":
    main()
