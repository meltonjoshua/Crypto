import logging
from typing import Dict, Optional
from datetime import datetime

class RiskManagement:
    """
    Risk management and position sizing logic
    """
    
    def __init__(self, config: Dict):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        self.stop_loss_pct = config['risk_management']['stop_loss_percentage']
        self.take_profit_pct = config['risk_management']['take_profit_percentage']
        self.max_position_size = config['risk_management']['max_position_size']
    
    def calculate_position_size(self, account_balance: float, 
                              current_price: float, 
                              risk_per_trade: float = 0.02) -> Dict:
        """
        Calculate optimal position size based on risk management rules
        
        Args:
            account_balance: Total account balance
            current_price: Current asset price
            risk_per_trade: Risk per trade as percentage of balance (default 2%)
        """
        try:
            # Maximum risk amount
            max_risk_amount = account_balance * risk_per_trade
            
            # Stop loss distance
            stop_loss_distance = current_price * (self.stop_loss_pct / 100)
            
            # Position size based on stop loss
            risk_based_size = max_risk_amount / stop_loss_distance
            
            # Position size in dollar terms
            dollar_position_size = min(risk_based_size * current_price, self.max_position_size)
            
            # Final position size in units
            position_size = dollar_position_size / current_price
            
            # Calculate stop loss and take profit levels
            stop_loss_price = current_price * (1 - self.stop_loss_pct / 100)
            take_profit_price = current_price * (1 + self.take_profit_pct / 100)
            
            return {
                'position_size_units': position_size,
                'position_size_dollars': dollar_position_size,
                'stop_loss_price': stop_loss_price,
                'take_profit_price': take_profit_price,
                'risk_amount': min(max_risk_amount, stop_loss_distance * position_size),
                'risk_reward_ratio': self.take_profit_pct / self.stop_loss_pct
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating position size: {e}")
            return {
                'position_size_units': 0,
                'position_size_dollars': 0,
                'stop_loss_price': current_price,
                'take_profit_price': current_price,
                'risk_amount': 0,
                'risk_reward_ratio': 0
            }
    
    def should_enter_trade(self, signal: Dict, current_price: float, 
                          account_balance: float = 10000) -> Dict:
        """
        Determine if a trade should be entered based on risk management rules
        """
        try:
            recommendation = signal.get('recommendation', 'HOLD')
            buy_strength = signal.get('buy_strength', 0)
            sell_strength = signal.get('sell_strength', 0)
            
            # Minimum signal strength required
            min_strength = 0.4
            
            should_buy = (recommendation in ['BUY', 'STRONG_BUY'] and 
                         buy_strength >= min_strength)
            should_sell = (recommendation in ['SELL', 'STRONG_SELL'] and 
                          sell_strength >= min_strength)
            
            trade_decision = {
                'should_enter': should_buy or should_sell,
                'direction': 'BUY' if should_buy else 'SELL' if should_sell else 'HOLD',
                'confidence': max(buy_strength, sell_strength),
                'reason': self._get_trade_reason(signal)
            }
            
            # Calculate position sizing if trade should be entered
            if trade_decision['should_enter']:
                position_info = self.calculate_position_size(account_balance, current_price)
                trade_decision.update(position_info)
            
            return trade_decision
            
        except Exception as e:
            self.logger.error(f"Error determining trade entry: {e}")
            return {
                'should_enter': False,
                'direction': 'HOLD',
                'confidence': 0,
                'reason': 'Error in analysis'
            }
    
    def should_exit_position(self, entry_price: float, current_price: float, 
                           direction: str, current_pnl_pct: float = None) -> Dict:
        """
        Determine if an existing position should be exited
        """
        try:
            if current_pnl_pct is None:
                if direction == 'BUY':
                    current_pnl_pct = (current_price - entry_price) / entry_price * 100
                else:  # SELL
                    current_pnl_pct = (entry_price - current_price) / entry_price * 100
            
            stop_loss_triggered = current_pnl_pct <= -self.stop_loss_pct
            take_profit_triggered = current_pnl_pct >= self.take_profit_pct
            
            # Trailing stop logic (optional)
            trailing_stop_triggered = False
            if current_pnl_pct > self.stop_loss_pct:
                # Implement trailing stop if position is profitable
                trailing_stop_pct = max(self.stop_loss_pct / 2, current_pnl_pct * 0.5)
                if direction == 'BUY':
                    trailing_stop_price = current_price * (1 - trailing_stop_pct / 100)
                    trailing_stop_triggered = current_price <= trailing_stop_price
                else:
                    trailing_stop_price = current_price * (1 + trailing_stop_pct / 100)
                    trailing_stop_triggered = current_price >= trailing_stop_price
            
            should_exit = stop_loss_triggered or take_profit_triggered or trailing_stop_triggered
            
            exit_reason = ""
            if stop_loss_triggered:
                exit_reason = "Stop loss triggered"
            elif take_profit_triggered:
                exit_reason = "Take profit triggered"
            elif trailing_stop_triggered:
                exit_reason = "Trailing stop triggered"
            
            return {
                'should_exit': should_exit,
                'reason': exit_reason,
                'current_pnl_pct': current_pnl_pct,
                'stop_loss_triggered': stop_loss_triggered,
                'take_profit_triggered': take_profit_triggered,
                'trailing_stop_triggered': trailing_stop_triggered
            }
            
        except Exception as e:
            self.logger.error(f"Error determining position exit: {e}")
            return {
                'should_exit': False,
                'reason': 'Error in analysis',
                'current_pnl_pct': 0
            }
    
    def calculate_max_drawdown(self, portfolio_values: list) -> float:
        """Calculate maximum drawdown from portfolio values"""
        try:
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
            
        except Exception as e:
            self.logger.error(f"Error calculating max drawdown: {e}")
            return 0.0
    
    def calculate_sharpe_ratio(self, returns: list, risk_free_rate: float = 0.02) -> float:
        """Calculate Sharpe ratio for strategy performance"""
        try:
            if len(returns) < 2:
                return 0.0
            
            import numpy as np
            returns_array = np.array(returns)
            excess_returns = returns_array - risk_free_rate / 252  # Daily risk-free rate
            
            if np.std(excess_returns) == 0:
                return 0.0
            
            sharpe = np.mean(excess_returns) / np.std(excess_returns) * np.sqrt(252)
            return sharpe
            
        except Exception as e:
            self.logger.error(f"Error calculating Sharpe ratio: {e}")
            return 0.0
    
    def _get_trade_reason(self, signal: Dict) -> str:
        """Get human-readable reason for trade recommendation"""
        signals = signal.get('signals', {})
        reasons = []
        
        if signals.get('rsi_buy'):
            reasons.append("RSI oversold")
        if signals.get('rsi_sell'):
            reasons.append("RSI overbought")
        if signals.get('macd_buy'):
            reasons.append("MACD bullish signal")
        if signals.get('macd_sell'):
            reasons.append("MACD bearish signal")
        if signals.get('ma_buy'):
            reasons.append("Moving average crossover up")
        if signals.get('ma_sell'):
            reasons.append("Moving average crossover down")
        if signals.get('bb_buy'):
            reasons.append("Bollinger band support")
        if signals.get('bb_sell'):
            reasons.append("Bollinger band resistance")
        
        if not reasons:
            return "Multiple indicators alignment"
        
        return ", ".join(reasons[:3])  # Limit to top 3 reasons
