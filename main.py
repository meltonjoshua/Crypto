#!/usr/bin/env python3
"""
Crypto Trading Bot - Main Application
"""

import os
import sys
import json
import time
import logging
import threading
import schedule
from datetime import datetime, timedelta
from typing import Dict, List

# Add src directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from coinbase_client import CoinbaseClient
from technical_analysis import TechnicalAnalysis
from trading_signals import TradingSignals
from risk_management import RiskManagement
from alerts import AlertSystem
from database import DatabaseManager

class CryptoTradingBot:
    """
    Main trading bot application
    """
    
    def __init__(self, config_path: str = "config/config.json"):
        # Setup logging
        self._setup_logging()
        self.logger = logging.getLogger(__name__)
        
        # Load configuration
        self.config = load_config(config_path)
        
        # Initialize components
        self.coinbase_client = CoinbaseClient(self.config['coinbase'])
        self.technical_analysis = TechnicalAnalysis(self.config)
        self.trading_signals = TradingSignals(self.config)
        self.risk_management = RiskManagement(self.config)
        self.alert_system = AlertSystem(self.config)
        self.database = DatabaseManager()
        
        # Runtime variables
        self.running = False
        self.last_signals = {}
        
        self.logger.info("Crypto Trading Bot initialized successfully")
    
    def _setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('trading_bot.log'),
                logging.StreamHandler(sys.stdout)
            ]
        )

    def run_analysis(self):
        """Run one-time analysis on all symbols"""
        print("🚀 Crypto Trading Bot - Analysis Report")
        print("=" * 60)
        
        for symbol in self.config['trading_pairs']:
            print(f"\n📊 Analyzing {symbol}...")
            try:
                analysis = self.analyze_symbol(symbol)
                if 'error' in analysis:
                    print(f"❌ Error: {analysis['error']}")
                    continue
                    
                # Display analysis results
                print(f"💰 Price: ${analysis['current_price']:.2f}")
                print(f"📈 Recommendation: {analysis['recommendation']}")
                print(f"🎯 Confidence: {analysis['confidence']:.1%}")
                
                if analysis.get('indicators'):
                    print("📊 Technical Indicators:")
                    indicators = analysis['indicators']
                    if 'rsi' in indicators and indicators['rsi'] is not None:
                        try:
                            rsi_val = float(indicators['rsi'].iloc[-1]) if hasattr(indicators['rsi'], 'iloc') else float(indicators['rsi'])
                            print(f"   RSI: {rsi_val:.1f}")
                        except (TypeError, ValueError, IndexError):
                            print("   RSI: N/A")
                    if 'macd' in indicators:
                        macd = indicators['macd']
                        try:
                            macd_val = float(macd.get('macd', 0)) if isinstance(macd, dict) else 0
                            print(f"   MACD: {macd_val:.3f}")
                        except (TypeError, ValueError):
                            print("   MACD: N/A")
                        
                print(f"✅ Analysis complete for {symbol}")
                
            except Exception as e:
                print(f"❌ Error analyzing {symbol}: {e}")
                self.logger.error(f"Analysis error for {symbol}: {e}")
        
        print("\\n" + "=" * 60)
        print("🎉 Analysis complete for all symbols!")
        
    def analyze_symbol(self, symbol: str) -> Dict:
        """Analyze a single symbol and return current status"""
        try:
            # Get fresh data from API first
            df = self.coinbase_client.get_historical_data(symbol, days=7, granularity=3600)
            
            if df.empty or len(df) < 50:
                # Try with more days if needed
                df = self.coinbase_client.get_historical_data(symbol, days=14, granularity=3600)
            
            if df.empty or len(df) < 50:
                return {'error': f'Insufficient data available for {symbol} (got {len(df)} points, need 50+)'}
            
            # Store in database for future use
            self.database.store_price_data(symbol, df)
            
            # Calculate indicators
            indicators = self.technical_analysis.calculate_all_indicators(df)
            
            # Get current price
            ticker = self.coinbase_client.get_product_ticker(symbol)
            if not ticker:
                return {'error': f'Unable to get current price for {symbol}'}
                
            current_price = float(ticker['price'])
            
            # Generate comprehensive signal
            signal = self.trading_signals.generate_comprehensive_signal(indicators, current_price)
            
            return {
                'symbol': symbol,
                'current_price': current_price,
                'recommendation': signal.get('recommendation', 'HOLD'),
                'confidence': signal.get('confidence', 0.0),
                'indicators': indicators,
                'signal_details': signal,
                'data_points': len(df)
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing {symbol}: {e}")
            return {'error': str(e)}

def load_config(config_path: str = 'config/config.json') -> Dict:
    """Load configuration from JSON file"""
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
            
        # Validate required sections
        required_sections = ['trading_pairs', 'analysis', 'risk_management']
        for section in required_sections:
            if section not in config:
                raise ValueError(f"Missing required configuration section: {section}")
                
        # Validate trading pairs
        if not config['trading_pairs'] or not isinstance(config['trading_pairs'], list):
            raise ValueError("trading_pairs must be a non-empty list")
            
        logging.info(f"Configuration loaded successfully from {config_path}")
        return config
        
    except FileNotFoundError:
        logging.error(f"Configuration file not found: {config_path}")
        raise
    except json.JSONDecodeError as e:
        logging.error(f"Invalid JSON in configuration file: {e}")
        raise
    except ValueError as e:
        logging.error(f"Configuration validation error: {e}")
        raise
    except Exception as e:
        logging.error(f"Unexpected error loading configuration: {e}")
        raise

    def update_market_data(self):
        """Update market data for all trading pairs"""
        try:
            for symbol in self.config['trading_pairs']:
                self.logger.info(f"Updating market data for {symbol}")
                
                # Get historical data
                days = max(7, self.config['data_collection']['history_days'])  # Ensure minimum 7 days
                df = self.coinbase_client.get_historical_data(symbol, days=days, granularity=3600)
                
                if df.empty:
                    self.logger.warning(f"No data received for {symbol}")
                    continue
                
                # Store in database
                self.database.store_price_data(symbol, df)
                
                # Calculate technical indicators
                indicators = self.technical_analysis.calculate_all_indicators(df)
                
                if not indicators:
                    self.logger.warning(f"No indicators calculated for {symbol}")
                    continue
                
                # Get current price
                ticker = self.coinbase_client.get_product_ticker(symbol)
                if not ticker:
                    self.logger.warning(f"No ticker data for {symbol}")
                    continue
                
                current_price = float(ticker['price'])
                
                # Generate trading signals
                signal = self.trading_signals.generate_comprehensive_signal(
                    indicators, current_price
                )
                
                # Store signal in database
                self.database.store_trading_signal(symbol, signal)
                
                # Check if signal has changed significantly
                if self._should_send_alert(symbol, signal):
                    self.alert_system.send_trading_signal_alert(symbol, signal)
                    self.last_signals[symbol] = signal
                
                # Check risk management for open positions
                self._check_open_positions(symbol, current_price)
                
                self.logger.info(f"Updated {symbol}: ${current_price:.2f} - {signal['recommendation']}")
                
        except Exception as e:
            self.logger.error(f"Error updating market data: {e}")
    
    def _should_send_alert(self, symbol: str, signal: Dict) -> bool:
        """Check if alert should be sent for this signal"""
        if symbol not in self.last_signals:
            return signal['recommendation'] in ['BUY', 'STRONG_BUY', 'SELL', 'STRONG_SELL']
        
        last_signal = self.last_signals[symbol]
        
        # Send alert if recommendation changed
        if signal['recommendation'] != last_signal['recommendation']:
            return True
        
        # Send alert if signal strength increased significantly
        buy_strength_change = signal['buy_strength'] - last_signal['buy_strength']
        sell_strength_change = signal['sell_strength'] - last_signal['sell_strength']
        
        return abs(buy_strength_change) > 0.2 or abs(sell_strength_change) > 0.2
    
    def _check_open_positions(self, symbol: str, current_price: float):
        """Check open positions for risk management"""
        try:
            open_positions = self.database.get_open_positions(symbol)
            
            for position in open_positions:
                exit_decision = self.risk_management.should_exit_position(
                    position['entry_price'],
                    current_price,
                    position['direction']
                )
                
                if exit_decision['should_exit']:
                    # Calculate P&L
                    if position['direction'] == 'BUY':
                        pnl_amount = (current_price - position['entry_price']) * position['position_size']
                        pnl_percentage = (current_price - position['entry_price']) / position['entry_price'] * 100
                    else:  # SELL
                        pnl_amount = (position['entry_price'] - current_price) * position['position_size']
                        pnl_percentage = (position['entry_price'] - current_price) / position['entry_price'] * 100
                    
                    # Update position in database
                    exit_data = {
                        'exit_timestamp': datetime.now(),
                        'exit_price': current_price,
                        'pnl_amount': pnl_amount,
                        'pnl_percentage': pnl_percentage
                    }
                    
                    self.database.update_position(position['id'], exit_data)
                    
                    # Send position exit alert
                    alert_details = {
                        'price': current_price,
                        'pnl_amount': pnl_amount,
                        'pnl_percentage': pnl_percentage,
                        'reason': exit_decision['reason']
                    }
                    
                    self.alert_system.send_position_alert(symbol, 'EXIT', alert_details)
                    
                    self.logger.info(f"Position closed for {symbol}: {exit_decision['reason']}")
                
        except Exception as e:
            self.logger.error(f"Error checking open positions for {symbol}: {e}")
    
    def analyze_symbol(self, symbol: str) -> Dict:
        """Analyze a single symbol and return current status"""
        try:
            # Get fresh data from API first
            df = self.coinbase_client.get_historical_data(symbol, days=7, granularity=3600)
            
            if df.empty or len(df) < 50:
                # Try with more days if needed
                df = self.coinbase_client.get_historical_data(symbol, days=14, granularity=3600)
            
            if df.empty or len(df) < 50:
                return {'error': f'Insufficient data available for {symbol} (got {len(df)} points, need 50+)'}
            
            # Store in database for future use
            self.database.store_price_data(symbol, df)
            
            # Calculate indicators
            indicators = self.technical_analysis.calculate_all_indicators(df)
            
            # Get current price
            ticker = self.coinbase_client.get_product_ticker(symbol)
            if not ticker:
                # Use last close price from historical data
                current_price = df['close'].iloc[-1]
            else:
                current_price = float(ticker['price'])
            
            # Generate signal
            signal = self.trading_signals.generate_comprehensive_signal(
                indicators, current_price
            )
            
            # Get trend direction
            trend = self.technical_analysis.get_trend_direction(df)
            
            # Get support/resistance
            sr_levels = self.technical_analysis.calculate_support_resistance(df)
            
            # Calculate volatility
            volatility = self.technical_analysis.calculate_volatility(df)
            
            return {
                'symbol': symbol,
                'current_price': current_price,
                'signal': signal,
                'trend': trend,
                'volatility': volatility,
                'support_resistance': sr_levels,
                'data_points': len(df),
                'last_updated': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing {symbol}: {e}")
            return {'error': str(e)}
    
    def get_portfolio_summary(self) -> Dict:
        """Get portfolio summary and statistics"""
        try:
            # Get trading statistics
            stats = self.database.get_trading_statistics(days=30)
            
            # Get open positions
            open_positions = self.database.get_open_positions()
            
            # Get recent signals
            recent_signals = self.database.get_recent_signals(limit=10)
            
            return {
                'trading_statistics': stats,
                'open_positions': open_positions,
                'recent_signals': recent_signals,
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting portfolio summary: {e}")
            return {'error': str(e)}
    
    def start_monitoring(self):
        """Start the monitoring loop"""
        self.logger.info("Starting crypto trading bot monitoring...")
        
        # Schedule regular updates
        update_frequency = self.config['data_collection']['update_frequency_seconds']
        schedule.every(update_frequency).seconds.do(self.update_market_data)
        
        # Schedule daily cleanup
        schedule.every().day.at("02:00").do(self.database.cleanup_old_data)
        
        self.running = True
        
        # Initial update
        self.update_market_data()
        
        # Start monitoring loop
        while self.running:
            try:
                schedule.run_pending()
                time.sleep(1)
            except KeyboardInterrupt:
                self.logger.info("Received interrupt signal, stopping...")
                self.running = False
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                time.sleep(10)  # Wait before retrying
    
    def stop_monitoring(self):
        """Stop the monitoring loop"""
        self.running = False
        self.logger.info("Crypto trading bot stopped")
    
    def run_analysis(self):
        """Run one-time analysis on all symbols"""
        print("🚀 Crypto Trading Bot - Analysis Report")
        print("=" * 60)
        
        for symbol in self.config['trading_pairs']:
            print(f"\n📊 Analyzing {symbol}...")
            analysis = self.analyze_symbol(symbol)
            
            if 'error' in analysis:
                print(f"❌ Error: {analysis['error']}")
                continue
            
            signal = analysis['signal']
            print(f"💰 Current Price: ${analysis['current_price']:.2f}")
            print(f"📈 Recommendation: {signal['recommendation']}")
            print(f"🔥 Buy Strength: {signal['buy_strength']:.1%}")
            print(f"🔥 Sell Strength: {signal['sell_strength']:.1%}")
            print(f"📊 Trend: {analysis['trend']}")
            
            # Show key indicators
            signals = signal.get('signals', {})
            if 'rsi_value' in signals:
                print(f"   RSI: {signals['rsi_value']:.1f}")
            if 'macd_value' in signals:
                print(f"   MACD: {signals['macd_value']:.4f}")
            
            # Support/Resistance
            sr = analysis.get('support_resistance', {})
            if 'support' in sr and 'resistance' in sr:
                print(f"   Support: ${sr['support']:.2f}")
                print(f"   Resistance: ${sr['resistance']:.2f}")
        
        # Portfolio summary
        print(f"\n📈 Portfolio Summary")
        print("=" * 40)
        portfolio = self.get_portfolio_summary()
        stats = portfolio.get('trading_statistics', {})
        
        if stats:
            print(f"Total Trades: {stats.get('total_trades', 0)}")
            print(f"Win Rate: {stats.get('win_rate', 0):.1f}%")
            print(f"Total P&L: ${stats.get('total_pnl', 0):.2f}")

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Crypto Trading Bot')
    parser.add_argument('--config', default='config/config.json',
                       help='Path to configuration file')
    parser.add_argument('--mode', choices=['monitor', 'analyze'], default='analyze',
                       help='Run mode: monitor (continuous) or analyze (one-time)')
    parser.add_argument('--symbol', help='Analyze specific symbol only')
    
    args = parser.parse_args()
    
    # Initialize bot
    bot = CryptoTradingBot(args.config)
    
    if args.mode == 'monitor':
        try:
            bot.start_monitoring()
        except KeyboardInterrupt:
            bot.stop_monitoring()
    else:
        if args.symbol:
            # Analyze specific symbol
            print(f"🔍 Analyzing {args.symbol}...")
            analysis = bot.analyze_symbol(args.symbol)
            print(json.dumps(analysis, indent=2, default=str))
        else:
            # Run full analysis
            bot.run_analysis()

if __name__ == "__main__":
    main()
