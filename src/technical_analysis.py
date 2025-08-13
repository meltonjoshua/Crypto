import pandas as pd
import numpy as np
from typing import Dict, Tuple, Optional
import logging

class TechnicalAnalysis:
    """
    Technical analysis indicators and calculations
    """
    
    def __init__(self, config: Dict):
        self.config = config
        self.logger = logging.getLogger(__name__)
    
    def calculate_rsi(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate RSI (Relative Strength Index)"""
        try:
            if df.empty or len(df) < period + 1:
                self.logger.warning(f"Insufficient data for RSI calculation: {len(df)} periods (need {period + 1})")
                return pd.Series(dtype=float)
                
            if 'close' not in df.columns:
                self.logger.error("Missing 'close' column for RSI calculation")
                return pd.Series(dtype=float)
            
            # Validate data
            close_prices = df['close'].dropna()
            if len(close_prices) < period + 1:
                self.logger.warning(f"Insufficient valid close prices for RSI: {len(close_prices)}")
                return pd.Series(dtype=float)
            
            delta = close_prices.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            
            # Avoid division by zero
            rs = gain / loss.replace(0, np.inf)
            rsi = 100 - (100 / (1 + rs))
            
            # Handle infinite and NaN values
            rsi = rsi.replace([np.inf, -np.inf], np.nan)
            
            return rsi
            
        except Exception as e:
            self.logger.error(f"Error calculating RSI: {e}")
            return pd.Series(dtype=float)
    
    def calculate_macd(self, df: pd.DataFrame, fast: int = None, 
                      slow: int = None, signal: int = None) -> Dict[str, pd.Series]:
        """Calculate MACD indicator"""
        if fast is None:
            fast = self.config['technical_indicators']['macd']['fast_period']
        if slow is None:
            slow = self.config['technical_indicators']['macd']['slow_period']
        if signal is None:
            signal = self.config['technical_indicators']['macd']['signal_period']
        
        ema_fast = df['close'].ewm(span=fast).mean()
        ema_slow = df['close'].ewm(span=slow).mean()
        
        macd_line = ema_fast - ema_slow
        macd_signal = macd_line.ewm(span=signal).mean()
        macd_histogram = macd_line - macd_signal
        
        return {
            'macd': macd_line,
            'macd_signal': macd_signal,
            'macd_histogram': macd_histogram
        }
    
    def calculate_moving_averages(self, df: pd.DataFrame, 
                                short_period: int = None, 
                                long_period: int = None) -> Dict[str, pd.Series]:
        """Calculate simple moving averages"""
        if short_period is None:
            short_period = self.config['technical_indicators']['moving_averages']['short_period']
        if long_period is None:
            long_period = self.config['technical_indicators']['moving_averages']['long_period']
        
        return {
            'sma_short': df['close'].rolling(window=short_period).mean(),
            'sma_long': df['close'].rolling(window=long_period).mean(),
            'ema_short': df['close'].ewm(span=short_period).mean(),
            'ema_long': df['close'].ewm(span=long_period).mean()
        }
    
    def calculate_bollinger_bands(self, df: pd.DataFrame, 
                                period: int = None, 
                                std_dev: float = None) -> Dict[str, pd.Series]:
        """Calculate Bollinger Bands"""
        if period is None:
            period = self.config['technical_indicators']['bollinger_bands']['period']
        if std_dev is None:
            std_dev = self.config['technical_indicators']['bollinger_bands']['std_dev']
        
        sma = df['close'].rolling(window=period).mean()
        std = df['close'].rolling(window=period).std()
        
        bb_upper = sma + (std * std_dev)
        bb_lower = sma - (std * std_dev)
        bb_width = (bb_upper - bb_lower) / sma
        bb_percent = (df['close'] - bb_lower) / (bb_upper - bb_lower)
        
        return {
            'bb_upper': bb_upper,
            'bb_middle': sma,
            'bb_lower': bb_lower,
            'bb_width': bb_width,
            'bb_percent': bb_percent
        }
    
    def calculate_stochastic(self, df: pd.DataFrame, k_period: int = 14, 
                           d_period: int = 3) -> Dict[str, pd.Series]:
        """Calculate Stochastic Oscillator"""
        lowest_low = df['low'].rolling(window=k_period).min()
        highest_high = df['high'].rolling(window=k_period).max()
        
        k_percent = 100 * ((df['close'] - lowest_low) / (highest_high - lowest_low))
        d_percent = k_percent.rolling(window=d_period).mean()
        
        return {
            'stoch_k': k_percent,
            'stoch_d': d_percent
        }
    
    def calculate_williams_r(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate Williams %R"""
        highest_high = df['high'].rolling(window=period).max()
        lowest_low = df['low'].rolling(window=period).min()
        
        williams_r = -100 * ((highest_high - df['close']) / (highest_high - lowest_low))
        return williams_r
    
    def calculate_volume_indicators(self, df: pd.DataFrame) -> Dict[str, pd.Series]:
        """Calculate volume-based indicators"""
        volume_sma = df['volume'].rolling(window=20).mean()
        volume_ratio = df['volume'] / volume_sma
        
        # On-Balance Volume
        obv = (df['volume'] * np.where(df['close'] > df['close'].shift(1), 1, 
                                      np.where(df['close'] < df['close'].shift(1), -1, 0))).cumsum()
        
        # Volume Weighted Average Price (simplified)
        vwap = (df['close'] * df['volume']).rolling(window=20).sum() / df['volume'].rolling(window=20).sum()
        
        return {
            'volume_sma': volume_sma,
            'volume_ratio': volume_ratio,
            'obv': obv,
            'vwap': vwap
        }
    
    def calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate Average True Range"""
        high_low = df['high'] - df['low']
        high_close_prev = np.abs(df['high'] - df['close'].shift())
        low_close_prev = np.abs(df['low'] - df['close'].shift())
        
        true_range = np.maximum(high_low, np.maximum(high_close_prev, low_close_prev))
        atr = pd.Series(true_range).rolling(window=period).mean()
        atr.index = df.index
        
        return atr
    
    def calculate_support_resistance(self, df: pd.DataFrame, 
                                   window: int = 20) -> Dict[str, float]:
        """Calculate support and resistance levels"""
        recent_data = df.tail(window)
        
        # Simple support/resistance based on recent highs and lows
        resistance = recent_data['high'].max()
        support = recent_data['low'].min()
        
        # Pivot points
        high = recent_data['high'].iloc[-1]
        low = recent_data['low'].iloc[-1]
        close = recent_data['close'].iloc[-1]
        
        pivot = (high + low + close) / 3
        r1 = 2 * pivot - low
        r2 = pivot + (high - low)
        s1 = 2 * pivot - high
        s2 = pivot - (high - low)
        
        return {
            'resistance': resistance,
            'support': support,
            'pivot': pivot,
            'r1': r1,
            'r2': r2,
            's1': s1,
            's2': s2
        }
    
    def calculate_all_indicators(self, df: pd.DataFrame) -> Dict:
        """Calculate all technical indicators"""
        if df.empty or len(df) < 50:
            self.logger.warning("Insufficient data for technical analysis")
            return {}
        
        try:
            indicators = {}
            
            # Momentum indicators
            indicators['rsi'] = self.calculate_rsi(df)
            macd_data = self.calculate_macd(df)
            indicators.update(macd_data)
            
            # Trend indicators
            ma_data = self.calculate_moving_averages(df)
            indicators.update(ma_data)
            
            # Volatility indicators
            bb_data = self.calculate_bollinger_bands(df)
            indicators.update(bb_data)
            indicators['atr'] = self.calculate_atr(df)
            
            # Additional oscillators
            stoch_data = self.calculate_stochastic(df)
            indicators.update(stoch_data)
            indicators['williams_r'] = self.calculate_williams_r(df)
            
            # Volume indicators
            volume_data = self.calculate_volume_indicators(df)
            indicators.update(volume_data)
            
            # Support/Resistance
            sr_data = self.calculate_support_resistance(df)
            indicators['support_resistance'] = sr_data
            
            return indicators
            
        except Exception as e:
            self.logger.error(f"Error calculating technical indicators: {e}")
            return {}
    
    def get_trend_direction(self, df: pd.DataFrame) -> str:
        """Determine overall trend direction"""
        try:
            ma_data = self.calculate_moving_averages(df)
            
            if ma_data['sma_short'].iloc[-1] > ma_data['sma_long'].iloc[-1]:
                if ma_data['sma_short'].iloc[-1] > ma_data['sma_short'].iloc[-5]:
                    return "STRONG_UPTREND"
                else:
                    return "UPTREND"
            elif ma_data['sma_short'].iloc[-1] < ma_data['sma_long'].iloc[-1]:
                if ma_data['sma_short'].iloc[-1] < ma_data['sma_short'].iloc[-5]:
                    return "STRONG_DOWNTREND"
                else:
                    return "DOWNTREND"
            else:
                return "SIDEWAYS"
                
        except Exception as e:
            self.logger.error(f"Error determining trend direction: {e}")
            return "UNKNOWN"
    
    def calculate_volatility(self, df: pd.DataFrame, period: int = 20) -> float:
        """Calculate price volatility"""
        try:
            returns = df['close'].pct_change().dropna()
            volatility = returns.rolling(window=period).std().iloc[-1] * np.sqrt(252)
            return volatility
        except Exception as e:
            self.logger.error(f"Error calculating volatility: {e}")
            return 0.0
