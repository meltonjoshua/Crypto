#!/usr/bin/env python3
"""
Crypto Trading Bot - Backtesting Module
"""

import os
import sys
import json
import argparse
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import logging

# Add src directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from coinbase_client import CoinbaseClient
from technical_analysis import TechnicalAnalysis
from trading_signals import TradingSignals
from risk_management import RiskManagement

class Backtester:
    """
    Backtesting engine for trading strategies
    """
    
    def __init__(self, config_path: str = "config/config.json"):
        # Load configuration
        with open(config_path, 'r') as f:
            self.config = json.load(f)
        
        # Initialize components
        self.coinbase_client = CoinbaseClient(self.config['coinbase'])
        self.technical_analysis = TechnicalAnalysis(self.config)
        self.trading_signals = TradingSignals(self.config)
        self.risk_management = RiskManagement(self.config)
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Backtesting parameters
        self.initial_balance = 10000.0
        self.commission_rate = 0.005  # 0.5% commission
        
    def get_historical_data(self, symbol: str, days: int) -> pd.DataFrame:
        """Get historical data for backtesting"""
        try:
            df = self.coinbase_client.get_historical_data(symbol, days=days)
            if df.empty:
                self.logger.error(f"No historical data available for {symbol}")
                return pd.DataFrame()
            
            self.logger.info(f"Retrieved {len(df)} data points for {symbol}")
            return df
            
        except Exception as e:
            self.logger.error(f"Error getting historical data: {e}")
            return pd.DataFrame()
    
    def run_backtest(self, symbol: str, start_date: datetime, 
                    end_date: datetime) -> Dict:
        """
        Run backtest for specified symbol and date range
        """
        try:
            # Calculate days difference (limit to reasonable range)
            total_days = (end_date - start_date).days
            total_days = min(total_days, 30)  # Limit to 30 days max for API limits
            df = self.get_historical_data(symbol, total_days + 7)  # Extra data for indicators
            
            if df.empty:
                return {'error': 'No data available for backtesting'}
            
            # Filter data to date range
            df = df[start_date:end_date]
            
            if len(df) < 50:
                return {'error': 'Insufficient data for backtesting'}
            
            # Initialize backtest variables
            portfolio = {
                'balance': self.initial_balance,
                'position': 0,  # Number of shares/units
                'position_value': 0,
                'entry_price': 0,
                'entry_time': None,
                'direction': None,
                'total_value': self.initial_balance
            }
            
            trades = []
            portfolio_values = []
            signals_log = []
            
            # Run backtest
            for i in range(50, len(df)):  # Start after enough data for indicators
                current_data = df.iloc[:i+1]
                current_price = df.iloc[i]['close']
                current_time = df.index[i]
                
                # Calculate indicators
                indicators = self.technical_analysis.calculate_all_indicators(current_data)
                
                if not indicators:
                    continue
                
                # Generate signal
                signal = self.trading_signals.generate_comprehensive_signal(
                    indicators, current_price
                )
                
                signals_log.append({
                    'timestamp': current_time,
                    'price': current_price,
                    'signal': signal
                })
                
                # Check for trade entry
                if portfolio['position'] == 0:  # No open position
                    trade_decision = self.risk_management.should_enter_trade(
                        signal, current_price, portfolio['balance']
                    )
                    
                    if trade_decision['should_enter']:
                        # Enter trade
                        direction = trade_decision['direction']
                        position_size_dollars = min(
                            trade_decision.get('position_size_dollars', portfolio['balance'] * 0.1),
                            portfolio['balance'] * 0.95  # Leave some cash for commission
                        )
                        
                        commission = position_size_dollars * self.commission_rate
                        position_size_units = (position_size_dollars - commission) / current_price
                        
                        if direction == 'BUY' and position_size_dollars > commission:
                            portfolio['balance'] -= position_size_dollars
                            portfolio['position'] = position_size_units
                            portfolio['entry_price'] = current_price
                            portfolio['entry_time'] = current_time
                            portfolio['direction'] = direction
                            
                            self.logger.info(f"BUY: {position_size_units:.4f} units at ${current_price:.2f}")
                
                # Check for trade exit
                elif portfolio['position'] > 0:  # Open position
                    exit_decision = self.risk_management.should_exit_position(
                        portfolio['entry_price'],
                        current_price,
                        portfolio['direction']
                    )
                    
                    # Force exit on strong opposite signal
                    if (portfolio['direction'] == 'BUY' and 
                        signal['recommendation'] in ['STRONG_SELL'] and 
                        signal['sell_strength'] > 0.7):
                        exit_decision['should_exit'] = True
                        exit_decision['reason'] = 'Strong opposite signal'
                    
                    if exit_decision['should_exit']:
                        # Exit trade
                        exit_value = portfolio['position'] * current_price
                        commission = exit_value * self.commission_rate
                        net_exit_value = exit_value - commission
                        
                        portfolio['balance'] += net_exit_value
                        
                        # Calculate P&L
                        entry_value = portfolio['position'] * portfolio['entry_price']
                        pnl = net_exit_value - entry_value
                        pnl_pct = (pnl / entry_value) * 100
                        
                        # Record trade
                        trade = {
                            'entry_time': portfolio['entry_time'],
                            'exit_time': current_time,
                            'direction': portfolio['direction'],
                            'entry_price': portfolio['entry_price'],
                            'exit_price': current_price,
                            'position_size': portfolio['position'],
                            'pnl': pnl,
                            'pnl_pct': pnl_pct,
                            'reason': exit_decision['reason'],
                            'duration': current_time - portfolio['entry_time']
                        }
                        trades.append(trade)
                        
                        self.logger.info(f"SELL: {portfolio['position']:.4f} units at ${current_price:.2f} "
                                       f"(P&L: ${pnl:.2f}, {pnl_pct:.2f}%)")
                        
                        # Reset position
                        portfolio['position'] = 0
                        portfolio['entry_price'] = 0
                        portfolio['entry_time'] = None
                        portfolio['direction'] = None
                
                # Update portfolio value
                if portfolio['position'] > 0:
                    portfolio['position_value'] = portfolio['position'] * current_price
                else:
                    portfolio['position_value'] = 0
                
                portfolio['total_value'] = portfolio['balance'] + portfolio['position_value']
                portfolio_values.append({
                    'timestamp': current_time,
                    'total_value': portfolio['total_value'],
                    'balance': portfolio['balance'],
                    'position_value': portfolio['position_value']
                })
            
            # Close any remaining position
            if portfolio['position'] > 0:
                current_price = df.iloc[-1]['close']
                current_time = df.index[-1]
                
                exit_value = portfolio['position'] * current_price
                commission = exit_value * self.commission_rate
                net_exit_value = exit_value - commission
                
                portfolio['balance'] += net_exit_value
                
                entry_value = portfolio['position'] * portfolio['entry_price']
                pnl = net_exit_value - entry_value
                pnl_pct = (pnl / entry_value) * 100
                
                trade = {
                    'entry_time': portfolio['entry_time'],
                    'exit_time': current_time,
                    'direction': portfolio['direction'],
                    'entry_price': portfolio['entry_price'],
                    'exit_price': current_price,
                    'position_size': portfolio['position'],
                    'pnl': pnl,
                    'pnl_pct': pnl_pct,
                    'reason': 'End of backtest',
                    'duration': current_time - portfolio['entry_time']
                }
                trades.append(trade)
                
                portfolio['position'] = 0
                portfolio['position_value'] = 0
                portfolio['total_value'] = portfolio['balance']
            
            # Calculate performance metrics
            performance = self._calculate_performance_metrics(
                trades, portfolio_values, self.initial_balance
            )
            
            return {
                'symbol': symbol,
                'start_date': start_date,
                'end_date': end_date,
                'initial_balance': self.initial_balance,
                'final_balance': portfolio['balance'],
                'final_value': portfolio['total_value'],
                'total_return': ((portfolio['total_value'] - self.initial_balance) / self.initial_balance) * 100,
                'trades': trades,
                'portfolio_values': portfolio_values,
                'performance_metrics': performance,
                'signals_log': signals_log[-10:]  # Last 10 signals
            }
            
        except Exception as e:
            self.logger.error(f"Error running backtest: {e}")
            return {'error': str(e)}
    
    def _calculate_performance_metrics(self, trades: List[Dict], 
                                     portfolio_values: List[Dict], 
                                     initial_balance: float) -> Dict:
        """Calculate comprehensive performance metrics"""
        try:
            if not trades:
                return {
                    'total_trades': 0,
                    'winning_trades': 0,
                    'losing_trades': 0,
                    'win_rate': 0,
                    'avg_win': 0,
                    'avg_loss': 0,
                    'profit_factor': 0,
                    'max_drawdown': 0,
                    'sharpe_ratio': 0,
                    'total_pnl': 0
                }
            
            # Basic trade statistics
            total_trades = len(trades)
            winning_trades = len([t for t in trades if t['pnl'] > 0])
            losing_trades = total_trades - winning_trades
            
            win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0
            
            # P&L calculations
            total_pnl = sum(t['pnl'] for t in trades)
            wins = [t['pnl'] for t in trades if t['pnl'] > 0]
            losses = [abs(t['pnl']) for t in trades if t['pnl'] < 0]
            
            avg_win = np.mean(wins) if wins else 0
            avg_loss = np.mean(losses) if losses else 0
            
            gross_profit = sum(wins)
            gross_loss = sum(losses)
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
            
            # Drawdown calculation
            portfolio_vals = [pv['total_value'] for pv in portfolio_values]
            max_drawdown = self._calculate_max_drawdown(portfolio_vals)
            
            # Sharpe ratio
            returns = []
            for i in range(1, len(portfolio_vals)):
                ret = (portfolio_vals[i] - portfolio_vals[i-1]) / portfolio_vals[i-1]
                returns.append(ret)
            
            sharpe_ratio = self._calculate_sharpe_ratio(returns)
            
            # Additional metrics
            avg_trade_duration = np.mean([
                t['duration'].total_seconds() / 3600 for t in trades  # in hours
            ]) if trades else 0
            
            return {
                'total_trades': total_trades,
                'winning_trades': winning_trades,
                'losing_trades': losing_trades,
                'win_rate': win_rate,
                'avg_win': avg_win,
                'avg_loss': avg_loss,
                'profit_factor': profit_factor,
                'max_drawdown': max_drawdown,
                'sharpe_ratio': sharpe_ratio,
                'total_pnl': total_pnl,
                'avg_trade_duration_hours': avg_trade_duration,
                'best_trade': max(t['pnl'] for t in trades) if trades else 0,
                'worst_trade': min(t['pnl'] for t in trades) if trades else 0
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating performance metrics: {e}")
            return {}
    
    def _calculate_max_drawdown(self, portfolio_values: List[float]) -> float:
        """Calculate maximum drawdown"""
        if len(portfolio_values) < 2:
            return 0.0
        
        peak = portfolio_values[0]
        max_drawdown = 0.0
        
        for value in portfolio_values:
            if value > peak:
                peak = value
            drawdown = (peak - value) / peak
            max_drawdown = max(max_drawdown, drawdown)
        
        return max_drawdown * 100  # Return as percentage
    
    def _calculate_sharpe_ratio(self, returns: List[float], 
                              risk_free_rate: float = 0.02) -> float:
        """Calculate Sharpe ratio"""
        if len(returns) < 2:
            return 0.0
        
        returns_array = np.array(returns)
        excess_returns = returns_array - risk_free_rate / 252  # Daily risk-free rate
        
        if np.std(excess_returns) == 0:
            return 0.0
        
        sharpe = np.mean(excess_returns) / np.std(excess_returns) * np.sqrt(252)
        return sharpe
    
    def print_backtest_results(self, results: Dict):
        """Print formatted backtest results"""
        if 'error' in results:
            print(f"❌ Backtest Error: {results['error']}")
            return
        
        print("\n" + "="*60)
        print("🚀 BACKTEST RESULTS")
        print("="*60)
        
        print(f"📊 Symbol: {results['symbol']}")
        print(f"📅 Period: {results['start_date'].strftime('%Y-%m-%d')} to {results['end_date'].strftime('%Y-%m-%d')}")
        print(f"💰 Initial Balance: ${results['initial_balance']:,.2f}")
        print(f"💰 Final Value: ${results['final_value']:,.2f}")
        print(f"📈 Total Return: {results['total_return']:.2f}%")
        
        performance = results['performance_metrics']
        
        print(f"\n📊 TRADING STATISTICS")
        print("-" * 30)
        print(f"Total Trades: {performance['total_trades']}")
        print(f"Winning Trades: {performance['winning_trades']}")
        print(f"Losing Trades: {performance['losing_trades']}")
        print(f"Win Rate: {performance['win_rate']:.1f}%")
        print(f"Average Win: ${performance['avg_win']:.2f}")
        print(f"Average Loss: ${performance['avg_loss']:.2f}")
        print(f"Profit Factor: {performance['profit_factor']:.2f}")
        print(f"Best Trade: ${performance['best_trade']:.2f}")
        print(f"Worst Trade: ${performance['worst_trade']:.2f}")
        
        print(f"\n📊 RISK METRICS")
        print("-" * 30)
        print(f"Maximum Drawdown: {performance['max_drawdown']:.2f}%")
        print(f"Sharpe Ratio: {performance['sharpe_ratio']:.2f}")
        print(f"Avg Trade Duration: {performance['avg_trade_duration_hours']:.1f} hours")
        
        # Show recent trades
        if results['trades']:
            print(f"\n📋 RECENT TRADES (Last 5)")
            print("-" * 50)
            for trade in results['trades'][-5:]:
                direction_icon = "🟢" if trade['direction'] == 'BUY' else "🔴"
                pnl_icon = "💚" if trade['pnl'] > 0 else "❤️"
                print(f"{direction_icon} {trade['entry_time'].strftime('%m-%d %H:%M')} - "
                      f"${trade['entry_price']:.2f} → ${trade['exit_price']:.2f} "
                      f"{pnl_icon} ${trade['pnl']:.2f} ({trade['pnl_pct']:.1f}%)")
        
        print("\n" + "="*60)
    
    def run_strategy_comparison(self, symbol: str, days: int) -> Dict:
        """Compare different strategy parameters"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Test different RSI parameters
        original_rsi = self.config['technical_indicators']['rsi'].copy()
        results = {}
        
        rsi_periods = [10, 14, 21]
        for period in rsi_periods:
            self.config['technical_indicators']['rsi']['period'] = period
            self.trading_signals = TradingSignals(self.config)
            
            result = self.run_backtest(symbol, start_date, end_date)
            if 'error' not in result:
                results[f'RSI_{period}'] = {
                    'total_return': result['total_return'],
                    'win_rate': result['performance_metrics']['win_rate'],
                    'max_drawdown': result['performance_metrics']['max_drawdown'],
                    'sharpe_ratio': result['performance_metrics']['sharpe_ratio']
                }
        
        # Restore original config
        self.config['technical_indicators']['rsi'] = original_rsi
        self.trading_signals = TradingSignals(self.config)
        
        return results

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Crypto Trading Bot Backtester')
    parser.add_argument('--config', default='config/config.json',
                       help='Path to configuration file')
    parser.add_argument('--symbol', default='BTC-USD',
                       help='Trading pair to backtest')
    parser.add_argument('--days', type=int, default=30,
                       help='Number of days to backtest')
    parser.add_argument('--compare', action='store_true',
                       help='Run strategy comparison')
    
    args = parser.parse_args()
    
    # Initialize backtester
    backtester = Backtester(args.config)
    
    if args.compare:
        print(f"🔄 Running strategy comparison for {args.symbol}...")
        comparison = backtester.run_strategy_comparison(args.symbol, args.days)
        
        print("\n📊 STRATEGY COMPARISON")
        print("="*50)
        for strategy, metrics in comparison.items():
            print(f"\n{strategy}:")
            print(f"  Total Return: {metrics['total_return']:.2f}%")
            print(f"  Win Rate: {metrics['win_rate']:.1f}%")
            print(f"  Max Drawdown: {metrics['max_drawdown']:.2f}%")
            print(f"  Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
    else:
        # Run single backtest
        end_date = datetime.now()
        start_date = end_date - timedelta(days=args.days)
        
        print(f"🔄 Running backtest for {args.symbol} ({args.days} days)...")
        results = backtester.run_backtest(args.symbol, start_date, end_date)
        
        backtester.print_backtest_results(results)

if __name__ == "__main__":
    main()
