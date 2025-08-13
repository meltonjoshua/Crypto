import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List
import logging
from datetime import datetime

class AlertSystem:
    """
    Alert system for trading signals and notifications
    """
    
    def __init__(self, config: Dict):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        self.email_enabled = config['alerts']['email_enabled']
        self.console_alerts = config['alerts']['console_alerts']
        
        if self.email_enabled:
            self.smtp_server = config['alerts']['email_smtp_server']
            self.port = config['alerts']['email_port']
            self.username = config['alerts']['email_username']
            self.password = config['alerts']['email_password']
            self.recipients = config['alerts']['email_recipients']
    
    def send_trading_signal_alert(self, symbol: str, signal: Dict) -> bool:
        """Send alert for trading signal"""
        try:
            recommendation = signal.get('recommendation', 'HOLD')
            price = signal.get('price', 0)
            buy_strength = signal.get('buy_strength', 0)
            sell_strength = signal.get('sell_strength', 0)
            timestamp = signal.get('timestamp', datetime.now())
            
            # Create alert message
            subject = f"🚨 {recommendation} Signal for {symbol}"
            
            message = self._format_signal_message(symbol, signal)
            
            # Send console alert
            if self.console_alerts:
                self._send_console_alert(subject, message)
            
            # Send email alert
            if self.email_enabled and recommendation in ['BUY', 'STRONG_BUY', 'SELL', 'STRONG_SELL']:
                return self._send_email_alert(subject, message)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error sending trading signal alert: {e}")
            return False
    
    def send_position_alert(self, symbol: str, action: str, details: Dict) -> bool:
        """Send alert for position entry/exit"""
        try:
            subject = f"📍 Position {action.upper()} - {symbol}"
            
            message = self._format_position_message(symbol, action, details)
            
            # Send console alert
            if self.console_alerts:
                self._send_console_alert(subject, message)
            
            # Send email alert for important position updates
            if self.email_enabled:
                return self._send_email_alert(subject, message)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error sending position alert: {e}")
            return False
    
    def send_risk_alert(self, symbol: str, alert_type: str, details: Dict) -> bool:
        """Send risk management alerts"""
        try:
            subject = f"⚠️ Risk Alert - {alert_type.upper()} - {symbol}"
            
            message = self._format_risk_message(symbol, alert_type, details)
            
            # Always send risk alerts to console
            self._send_console_alert(subject, message)
            
            # Send email for critical risk alerts
            if self.email_enabled:
                return self._send_email_alert(subject, message)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error sending risk alert: {e}")
            return False
    
    def send_system_alert(self, alert_type: str, message: str) -> bool:
        """Send system status alerts"""
        try:
            subject = f"🔧 System Alert - {alert_type.upper()}"
            
            # Send console alert
            if self.console_alerts:
                self._send_console_alert(subject, message)
            
            # Send email for critical system alerts
            if self.email_enabled and alert_type.lower() in ['error', 'critical']:
                return self._send_email_alert(subject, message)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error sending system alert: {e}")
            return False
    
    def _send_console_alert(self, subject: str, message: str):
        """Send alert to console"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n{'='*60}")
        print(f"🔔 ALERT - {timestamp}")
        print(f"Subject: {subject}")
        print(f"{'='*60}")
        print(message)
        print(f"{'='*60}\n")
    
    def _send_email_alert(self, subject: str, message: str) -> bool:
        """Send email alert"""
        try:
            if not self.email_enabled:
                return False
            
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.username
            msg['Subject'] = subject
            
            # Add body to email
            msg.attach(MIMEText(message, 'plain'))
            
            # Create secure connection and send email
            context = ssl.create_default_context()
            
            with smtplib.SMTP(self.smtp_server, self.port) as server:
                server.starttls(context=context)
                server.login(self.username, self.password)
                
                for recipient in self.recipients:
                    msg['To'] = recipient
                    server.send_message(msg)
                    del msg['To']
            
            self.logger.info(f"Email alert sent successfully: {subject}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error sending email alert: {e}")
            return False
    
    def _format_signal_message(self, symbol: str, signal: Dict) -> str:
        """Format trading signal message"""
        timestamp = signal.get('timestamp', datetime.now()).strftime("%Y-%m-%d %H:%M:%S")
        recommendation = signal.get('recommendation', 'HOLD')
        price = signal.get('price', 0)
        buy_strength = signal.get('buy_strength', 0)
        sell_strength = signal.get('sell_strength', 0)
        signals = signal.get('signals', {})
        support_resistance = signal.get('support_resistance', {})
        
        message = f"""
TRADING SIGNAL ALERT
===================

Symbol: {symbol}
Timestamp: {timestamp}
Current Price: ${price:.2f}
Recommendation: {recommendation}

Signal Strengths:
- Buy Strength: {buy_strength:.2%}
- Sell Strength: {sell_strength:.2%}

Technical Indicators:
"""
        
        # Add indicator details
        if 'rsi_value' in signals:
            message += f"- RSI: {signals['rsi_value']:.1f}"
            if signals.get('rsi_buy'):
                message += " (OVERSOLD)"
            elif signals.get('rsi_sell'):
                message += " (OVERBOUGHT)"
            message += "\n"
        
        if 'macd_value' in signals:
            message += f"- MACD: {signals['macd_value']:.4f}"
            if signals.get('macd_buy'):
                message += " (BULLISH)"
            elif signals.get('macd_sell'):
                message += " (BEARISH)"
            message += "\n"
        
        if 'sma_short' in signals and 'sma_long' in signals:
            message += f"- MA Short: ${signals['sma_short']:.2f}\n"
            message += f"- MA Long: ${signals['sma_long']:.2f}\n"
        
        # Add support/resistance levels
        if support_resistance:
            message += f"\nSupport/Resistance Levels:\n"
            if 'support' in support_resistance:
                message += f"- Support: ${support_resistance['support']:.2f}\n"
            if 'resistance' in support_resistance:
                message += f"- Resistance: ${support_resistance['resistance']:.2f}\n"
            if 'pivot' in support_resistance:
                message += f"- Pivot: ${support_resistance['pivot']:.2f}\n"
        
        message += f"\n⚠️ This is for informational purposes only. Always do your own research before trading."
        
        return message
    
    def _format_position_message(self, symbol: str, action: str, details: Dict) -> str:
        """Format position alert message"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        message = f"""
POSITION {action.upper()} ALERT
=====================

Symbol: {symbol}
Timestamp: {timestamp}
Action: {action.upper()}

Position Details:
"""
        
        if 'price' in details:
            message += f"- Price: ${details['price']:.2f}\n"
        if 'position_size_units' in details:
            message += f"- Size: {details['position_size_units']:.4f} units\n"
        if 'position_size_dollars' in details:
            message += f"- Value: ${details['position_size_dollars']:.2f}\n"
        if 'stop_loss_price' in details:
            message += f"- Stop Loss: ${details['stop_loss_price']:.2f}\n"
        if 'take_profit_price' in details:
            message += f"- Take Profit: ${details['take_profit_price']:.2f}\n"
        if 'reason' in details:
            message += f"- Reason: {details['reason']}\n"
        if 'current_pnl_pct' in details:
            message += f"- P&L: {details['current_pnl_pct']:.2f}%\n"
        
        return message
    
    def _format_risk_message(self, symbol: str, alert_type: str, details: Dict) -> str:
        """Format risk alert message"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        message = f"""
RISK MANAGEMENT ALERT
====================

Symbol: {symbol}
Timestamp: {timestamp}
Alert Type: {alert_type.upper()}

Details:
"""
        
        for key, value in details.items():
            if isinstance(value, float):
                if 'pct' in key.lower() or 'percent' in key.lower():
                    message += f"- {key.replace('_', ' ').title()}: {value:.2f}%\n"
                elif 'price' in key.lower():
                    message += f"- {key.replace('_', ' ').title()}: ${value:.2f}\n"
                else:
                    message += f"- {key.replace('_', ' ').title()}: {value:.2f}\n"
            else:
                message += f"- {key.replace('_', ' ').title()}: {value}\n"
        
        message += f"\n⚠️ Please review your positions immediately."
        
        return message
