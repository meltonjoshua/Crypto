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

# Install required packages if not available
required_packages = [
    'flask', 'requests', 'pandas', 'numpy', 'plotly', 
    'schedule', 'websocket-client', 'yfinance'
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

# ==================== WEB APPLICATION ====================

def create_app():
    """Create Flask web application"""
    app = Flask(__name__)
    app.secret_key = config.SECRET_KEY
    
    # Initialize components
    db_manager = DatabaseManager()
    portfolio_manager = PortfolioManager(db_manager)
    alert_system = AlertSystem(db_manager)
    
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
    </div>

    <script>
        // Global variables
        // Initialize page
        document.addEventListener('DOMContentLoaded', function() {
            refreshData();
            setInterval(refreshData, 60000); // Refresh every 60 seconds (increased for stability)
        });

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
