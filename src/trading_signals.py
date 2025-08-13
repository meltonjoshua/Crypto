import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
import logging
from datetime import datetime

class TradingSignals:
    """
    Generate buy/sell signals based on technical indicators
    """
    
    def __init__(self, config: Dict):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Signal thresholds
        self.rsi_overbought = config['technical_indicators']['rsi']['overbought']
        self.rsi_oversold = config['technical_indicators']['rsi']['oversold']
    
    def generate_rsi_signals(self, rsi: pd.Series) -> Dict[str, bool]:
        """Generate signals based on RSI"""
        current_rsi = rsi.iloc[-1] if not rsi.empty else 50
        
        return {
            'rsi_buy': current_rsi < self.rsi_oversold,
            'rsi_sell': current_rsi > self.rsi_overbought,
            'rsi_value': current_rsi
        }
    
    def generate_macd_signals(self, macd_data: Dict[str, pd.Series]) -> Dict[str, bool]:
        """Generate signals based on MACD"""
        try:
            macd = macd_data['macd']
            signal = macd_data['macd_signal']
            histogram = macd_data['macd_histogram']
            
            if len(macd) < 2:
                return {'macd_buy': False, 'macd_sell': False}
            
            # MACD crossover signals
            macd_buy = (macd.iloc[-1] > signal.iloc[-1] and 
                       macd.iloc[-2] <= signal.iloc[-2])
            macd_sell = (macd.iloc[-1] < signal.iloc[-1] and 
                        macd.iloc[-2] >= signal.iloc[-2])
            
            # Histogram divergence
            histogram_bullish = (histogram.iloc[-1] > histogram.iloc[-2] and 
                               histogram.iloc[-1] > 0)
            histogram_bearish = (histogram.iloc[-1] < histogram.iloc[-2] and 
                                histogram.iloc[-1] < 0)
            
            return {
                'macd_buy': macd_buy or histogram_bullish,
                'macd_sell': macd_sell or histogram_bearish,
                'macd_value': macd.iloc[-1],
                'macd_signal_value': signal.iloc[-1]
            }
            
        except Exception as e:
            self.logger.error(f"Error generating MACD signals: {e}")
            return {'macd_buy': False, 'macd_sell': False}
    
    def generate_ma_signals(self, ma_data: Dict[str, pd.Series]) -> Dict[str, bool]:
        """Generate signals based on Moving Averages"""
        try:
            sma_short = ma_data['sma_short']
            sma_long = ma_data['sma_long']
            ema_short = ma_data['ema_short']
            ema_long = ma_data['ema_long']
            
            if len(sma_short) < 2 or len(sma_long) < 2:
                return {'ma_buy': False, 'ma_sell': False}
            
            # SMA crossover
            sma_buy = (sma_short.iloc[-1] > sma_long.iloc[-1] and 
                      sma_short.iloc[-2] <= sma_long.iloc[-2])
            sma_sell = (sma_short.iloc[-1] < sma_long.iloc[-1] and 
                       sma_short.iloc[-2] >= sma_long.iloc[-2])
            
            # EMA crossover
            ema_buy = (ema_short.iloc[-1] > ema_long.iloc[-1] and 
                      ema_short.iloc[-2] <= ema_long.iloc[-2])
            ema_sell = (ema_short.iloc[-1] < ema_long.iloc[-1] and 
                       ema_short.iloc[-2] >= ema_long.iloc[-2])
            
            return {
                'ma_buy': sma_buy or ema_buy,
                'ma_sell': sma_sell or ema_sell,
                'sma_short': sma_short.iloc[-1],
                'sma_long': sma_long.iloc[-1]
            }
            
        except Exception as e:
            self.logger.error(f"Error generating MA signals: {e}")
            return {'ma_buy': False, 'ma_sell': False}
    
    def generate_bb_signals(self, bb_data: Dict[str, pd.Series], 
                           current_price: float) -> Dict[str, bool]:
        """Generate signals based on Bollinger Bands"""
        try:
            bb_upper = bb_data['bb_upper'].iloc[-1]
            bb_lower = bb_data['bb_lower'].iloc[-1]
            bb_percent = bb_data['bb_percent'].iloc[-1]
            
            # Price touching bands
            bb_buy = current_price <= bb_lower * 1.001  # Small tolerance
            bb_sell = current_price >= bb_upper * 0.999  # Small tolerance
            
            # %B indicator signals
            bb_oversold = bb_percent < 0.2
            bb_overbought = bb_percent > 0.8
            
            return {
                'bb_buy': bb_buy or bb_oversold,
                'bb_sell': bb_sell or bb_overbought,
                'bb_percent': bb_percent
            }
            
        except Exception as e:
            self.logger.error(f"Error generating Bollinger Band signals: {e}")
            return {'bb_buy': False, 'bb_sell': False}
    
    def generate_stoch_signals(self, stoch_data: Dict[str, pd.Series]) -> Dict[str, bool]:
        """Generate signals based on Stochastic Oscillator"""
        try:
            stoch_k = stoch_data['stoch_k']
            stoch_d = stoch_data['stoch_d']
            
            if len(stoch_k) < 2:
                return {'stoch_buy': False, 'stoch_sell': False}
            
            current_k = stoch_k.iloc[-1]
            current_d = stoch_d.iloc[-1]
            
            # Oversold/Overbought conditions
            stoch_oversold = current_k < 20 and current_d < 20
            stoch_overbought = current_k > 80 and current_d > 80
            
            # Crossover signals
            stoch_buy_cross = (current_k > current_d and 
                              stoch_k.iloc[-2] <= stoch_d.iloc[-2])
            stoch_sell_cross = (current_k < current_d and 
                               stoch_k.iloc[-2] >= stoch_d.iloc[-2])
            
            return {
                'stoch_buy': stoch_oversold or (stoch_buy_cross and current_k < 50),
                'stoch_sell': stoch_overbought or (stoch_sell_cross and current_k > 50),
                'stoch_k': current_k,
                'stoch_d': current_d
            }
            
        except Exception as e:
            self.logger.error(f"Error generating Stochastic signals: {e}")
            return {'stoch_buy': False, 'stoch_sell': False}
    
    def generate_volume_signals(self, volume_data: Dict[str, pd.Series]) -> Dict[str, bool]:
        """Generate signals based on volume indicators"""
        try:
            volume_ratio = volume_data['volume_ratio'].iloc[-1]
            obv = volume_data['obv']
            
            # High volume confirmation
            high_volume = volume_ratio > 1.5
            
            # OBV trend
            obv_bullish = len(obv) >= 5 and obv.iloc[-1] > obv.iloc[-5]
            obv_bearish = len(obv) >= 5 and obv.iloc[-1] < obv.iloc[-5]
            
            return {
                'volume_confirmation': high_volume,
                'volume_bullish': obv_bullish,
                'volume_bearish': obv_bearish,
                'volume_ratio': volume_ratio
            }
            
        except Exception as e:
            self.logger.error(f"Error generating volume signals: {e}")
            return {'volume_confirmation': False, 'volume_bullish': False, 'volume_bearish': False}
    
    def calculate_signal_strength(self, signals: Dict) -> Tuple[float, float]:
        """Calculate overall buy/sell signal strength"""
        buy_signals = []
        sell_signals = []
        
        # Collect all buy/sell signals
        for key, value in signals.items():
            if key.endswith('_buy') and value:
                buy_signals.append(1)
            elif key.endswith('_sell') and value:
                sell_signals.append(1)
        
        # Weight the signals based on reliability
        weights = {
            'rsi': 0.2,
            'macd': 0.25,
            'ma': 0.25,
            'bb': 0.15,
            'stoch': 0.15
        }
        
        buy_strength = 0
        sell_strength = 0
        
        for indicator in weights:
            if f"{indicator}_buy" in signals and signals[f"{indicator}_buy"]:
                buy_strength += weights[indicator]
            if f"{indicator}_sell" in signals and signals[f"{indicator}_sell"]:
                sell_strength += weights[indicator]
        
        # Volume confirmation boost
        if signals.get('volume_confirmation', False):
            if signals.get('volume_bullish', False):
                buy_strength *= 1.2
            if signals.get('volume_bearish', False):
                sell_strength *= 1.2
        
        return min(buy_strength, 1.0), min(sell_strength, 1.0)
    
    def generate_comprehensive_signal(self, indicators: Dict, 
                                    current_price: float) -> Dict:
        """Generate comprehensive trading signal"""
        try:
            all_signals = {}
            
            # Generate individual indicator signals
            if 'rsi' in indicators:
                rsi_signals = self.generate_rsi_signals(indicators['rsi'])
                all_signals.update(rsi_signals)
            
            if 'macd' in indicators:
                macd_signals = self.generate_macd_signals({
                    'macd': indicators['macd'],
                    'macd_signal': indicators['macd_signal'],
                    'macd_histogram': indicators['macd_histogram']
                })
                all_signals.update(macd_signals)
            
            if 'sma_short' in indicators:
                ma_signals = self.generate_ma_signals({
                    'sma_short': indicators['sma_short'],
                    'sma_long': indicators['sma_long'],
                    'ema_short': indicators['ema_short'],
                    'ema_long': indicators['ema_long']
                })
                all_signals.update(ma_signals)
            
            if 'bb_upper' in indicators:
                bb_signals = self.generate_bb_signals({
                    'bb_upper': indicators['bb_upper'],
                    'bb_lower': indicators['bb_lower'],
                    'bb_percent': indicators['bb_percent']
                }, current_price)
                all_signals.update(bb_signals)
            
            if 'stoch_k' in indicators:
                stoch_signals = self.generate_stoch_signals({
                    'stoch_k': indicators['stoch_k'],
                    'stoch_d': indicators['stoch_d']
                })
                all_signals.update(stoch_signals)
            
            if 'volume_ratio' in indicators:
                volume_signals = self.generate_volume_signals({
                    'volume_ratio': indicators['volume_ratio'],
                    'obv': indicators['obv']
                })
                all_signals.update(volume_signals)
            
            # Calculate overall signal strength
            buy_strength, sell_strength = self.calculate_signal_strength(all_signals)
            
            # Determine final recommendation
            recommendation = "HOLD"
            if buy_strength > 0.6:
                recommendation = "STRONG_BUY"
            elif buy_strength > 0.4:
                recommendation = "BUY"
            elif sell_strength > 0.6:
                recommendation = "STRONG_SELL"
            elif sell_strength > 0.4:
                recommendation = "SELL"
            
            return {
                'timestamp': datetime.now(),
                'price': current_price,
                'recommendation': recommendation,
                'buy_strength': buy_strength,
                'sell_strength': sell_strength,
                'signals': all_signals,
                'support_resistance': indicators.get('support_resistance', {})
            }
            
        except Exception as e:
            self.logger.error(f"Error generating comprehensive signal: {e}")
            return {
                'timestamp': datetime.now(),
                'price': current_price,
                'recommendation': "HOLD",
                'buy_strength': 0.0,
                'sell_strength': 0.0,
                'signals': {},
                'support_resistance': {}
            }
