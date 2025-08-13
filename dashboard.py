#!/usr/bin/env python3
"""
Crypto Trading Bot - Web Dashboard
"""

import os
import sys
import json
import dash
from dash import dcc,    def _get_empty_dashboard(self, message: str = "No data available"):
        """Return empty dashboard components with error message"""
        empty_fig = go.Figure()
        empty_fig.add_annotation(
            text=message, 
            xref="paper", yref="paper",
            x=0.5, y=0.5, 
            showarrow=False,
            font=dict(size=16, color="red")
        )
        empty_fig.update_layout(
            title=message,
            showlegend=False,
            xaxis=dict(visible=False),
            yaxis=dict(visible=False)
        )
        
        empty_table = html.Div([
            html.H4("No signals available", style={'color': 'red', 'text-align': 'center'}),
            html.P(message, style={'text-align': 'center'})
        ])
        
        return empty_fig, empty_fig, empty_fig, empty_table

    def setup_callbacks(self):html, Input, Output, callback_context
import plotly.graph_objs as go
import plotly.express as px
import pandas as pd
from datetime import datetime, timedelta
import logging

# Add src to path
sys.path.append('src')

try:
    from coinbase_client import CoinbaseClient
    from technical_analysis import TechnicalAnalysis  
    from trading_signals import TradingSignals
    from database import DatabaseManager
    from error_handler import error_handler, safe_execute
except ImportError as e:
    print(f"❌ Error importing modules: {e}")
    print("Please ensure all required modules are in the src/ directory")
    sys.exit(1)

class TradingDashboard:
    """
    Web dashboard for monitoring trading bot
    """
    
    def __init__(self, config_path: str = "config/config.json"):
        # Load configuration
        with open(config_path, 'r') as f:
            self.config = json.load(f)
        
        # Initialize components
        self.coinbase_client = CoinbaseClient(self.config['coinbase'])
        self.technical_analysis = TechnicalAnalysis(self.config)
        self.database = DatabaseManager()
        
        # Initialize Dash app
        self.app = dash.Dash(__name__)
        self.app.title = "Crypto Trading Bot Dashboard"
        
        # Setup layout
        self._setup_layout()
        self._setup_callbacks()
    
    def _setup_layout(self):
        """Setup dashboard layout"""
        self.app.layout = html.Div([
            # Header
            html.Div([
                html.H1("🚀 Crypto Trading Bot Dashboard", 
                       className="text-center mb-4",
                       style={'color': '#2c3e50', 'margin': '20px 0'}),
                
                # Symbol selector
                html.Div([
                    html.Label("Select Trading Pair:", style={'font-weight': 'bold'}),
                    dcc.Dropdown(
                        id='symbol-dropdown',
                        options=[{'label': symbol, 'value': symbol} 
                                for symbol in self.config['trading_pairs']],
                        value=self.config['trading_pairs'][0],
                        style={'margin': '10px 0'}
                    )
                ], style={'width': '300px', 'margin': '0 auto'}),
                
                # Auto-refresh toggle
                html.Div([
                    dcc.Interval(
                        id='interval-component',
                        interval=60*1000,  # Update every minute
                        n_intervals=0
                    )
                ])
            ], style={'text-align': 'center', 'margin-bottom': '30px'}),
            
            # Main content
            html.Div([
                # Current status row
                html.Div([
                    html.Div([
                        html.H3("📊 Current Status", style={'color': '#34495e'}),
                        html.Div(id='current-status')
                    ], className='col-md-6'),
                    
                    html.Div([
                        html.H3("🎯 Trading Signals", style={'color': '#34495e'}),
                        html.Div(id='trading-signals')
                    ], className='col-md-6')
                ], className='row', style={'margin-bottom': '30px'}),
                
                # Price chart
                html.Div([
                    html.H3("📈 Price Chart with Technical Analysis", style={'color': '#34495e'}),
                    dcc.Graph(id='price-chart')
                ], style={'margin-bottom': '30px'}),
                
                # Indicators row
                html.Div([
                    html.Div([
                        html.H4("RSI", style={'color': '#34495e'}),
                        dcc.Graph(id='rsi-chart')
                    ], className='col-md-6'),
                    
                    html.Div([
                        html.H4("MACD", style={'color': '#34495e'}),
                        dcc.Graph(id='macd-chart')
                    ], className='col-md-6')
                ], className='row', style={'margin-bottom': '30px'}),
                
                # Portfolio and stats
                html.Div([
                    html.Div([
                        html.H3("💼 Portfolio Statistics", style={'color': '#34495e'}),
                        html.Div(id='portfolio-stats')
                    ], className='col-md-6'),
                    
                    html.Div([
                        html.H3("📋 Recent Signals", style={'color': '#34495e'}),
                        html.Div(id='recent-signals')
                    ], className='col-md-6')
                ], className='row')
            ], className='container-fluid')
        ])
    
    def _setup_callbacks(self):
        """Setup dashboard callbacks"""
        
        @self.app.callback(
            [Output('current-status', 'children'),
             Output('trading-signals', 'children'),
             Output('price-chart', 'figure'),
             Output('rsi-chart', 'figure'),
             Output('macd-chart', 'figure'),
             Output('portfolio-stats', 'children'),
             Output('recent-signals', 'children')],
            [Input('symbol-dropdown', 'value'),
             Input('interval-component', 'n_intervals')]
        )
        def update_dashboard(selected_symbol, n):
            try:
                # Get price data
                df = self.database.get_price_data(
                    selected_symbol, 
                    start_date=datetime.now() - timedelta(days=30)
                )
                
                if df.empty:
                    # Try to get fresh data
                    df = self.coinbase_client.get_historical_data(selected_symbol, days=30)
                    if not df.empty:
                        self.database.store_price_data(selected_symbol, df)
                
                # Get current ticker
                ticker = self.coinbase_client.get_product_ticker(selected_symbol)
                current_price = float(ticker['price']) if ticker else 0
                
                # Calculate indicators
                indicators = self.technical_analysis.calculate_all_indicators(df)
                
                # Get latest signal
                recent_signals = self.database.get_recent_signals(selected_symbol, limit=1)
                latest_signal = recent_signals[0] if recent_signals else None
                
                # Create components
                status_component = self._create_status_component(
                    selected_symbol, current_price, ticker, df
                )
                
                signals_component = self._create_signals_component(latest_signal)
                
                price_chart = self._create_price_chart(df, indicators, selected_symbol)
                rsi_chart = self._create_rsi_chart(indicators)
                macd_chart = self._create_macd_chart(indicators)
                
                portfolio_component = self._create_portfolio_component()
                recent_signals_component = self._create_recent_signals_component()
                
                return (status_component, signals_component, price_chart, 
                       rsi_chart, macd_chart, portfolio_component, recent_signals_component)
                
            except Exception as e:
                logging.error(f"Error updating dashboard: {e}")
                error_msg = html.Div(f"Error: {str(e)}", style={'color': 'red'})
                empty_fig = {'data': [], 'layout': {}}
                return error_msg, error_msg, empty_fig, empty_fig, empty_fig, error_msg, error_msg
    
    def _create_status_component(self, symbol, current_price, ticker, df):
        """Create current status component"""
        try:
            if ticker:
                stats_24h = self.coinbase_client.get_24hr_stats(symbol)
                
                price_change = 0
                price_change_pct = 0
                
                if stats_24h:
                    open_24h = float(stats_24h.get('open', current_price))
                    price_change = current_price - open_24h
                    price_change_pct = (price_change / open_24h * 100) if open_24h > 0 else 0
                
                # Get trend
                trend = self.technical_analysis.get_trend_direction(df) if not df.empty else "UNKNOWN"
                
                # Color based on price change
                price_color = '#27ae60' if price_change >= 0 else '#e74c3c'
                
                return html.Div([
                    html.H4(f"${current_price:.2f}", 
                           style={'color': price_color, 'margin': '10px 0'}),
                    html.P(f"24h Change: ${price_change:.2f} ({price_change_pct:.2f}%)",
                          style={'color': price_color}),
                    html.P(f"Trend: {trend}"),
                    html.P(f"Volume: {ticker.get('volume', 'N/A')}"),
                    html.P(f"Last Updated: {datetime.now().strftime('%H:%M:%S')}")
                ])
            else:
                return html.Div("No ticker data available", style={'color': '#e74c3c'})
                
        except Exception as e:
            return html.Div(f"Error loading status: {e}", style={'color': '#e74c3c'})
    
    def _create_signals_component(self, signal):
        """Create trading signals component"""
        if not signal:
            return html.Div("No recent signals", style={'color': '#7f8c8d'})
        
        recommendation = signal['recommendation']
        buy_strength = signal['buy_strength']
        sell_strength = signal['sell_strength']
        
        # Color based on recommendation
        rec_color = '#27ae60' if 'BUY' in recommendation else '#e74c3c' if 'SELL' in recommendation else '#f39c12'
        
        return html.Div([
            html.H4(recommendation, style={'color': rec_color, 'margin': '10px 0'}),
            html.P(f"Buy Strength: {buy_strength:.1%}"),
            html.P(f"Sell Strength: {sell_strength:.1%}"),
            html.P(f"Signal Time: {signal['timestamp']}")
        ])
    
    def _create_price_chart(self, df, indicators, symbol):
        """Create price chart with technical indicators"""
        if df.empty:
            return {'data': [], 'layout': {'title': 'No data available'}}
        
        fig = go.Figure()
        
        # Candlestick chart
        fig.add_trace(go.Candlestick(
            x=df.index,
            open=df['open_price'] if 'open_price' in df.columns else df['open'],
            high=df['high_price'] if 'high_price' in df.columns else df['high'],
            low=df['low_price'] if 'low_price' in df.columns else df['low'],
            close=df['close_price'] if 'close_price' in df.columns else df['close'],
            name="Price"
        ))
        
        # Add moving averages
        if 'sma_short' in indicators:
            fig.add_trace(go.Scatter(
                x=df.index,
                y=indicators['sma_short'],
                name='SMA 20',
                line=dict(color='blue', width=2)
            ))
        
        if 'sma_long' in indicators:
            fig.add_trace(go.Scatter(
                x=df.index,
                y=indicators['sma_long'],
                name='SMA 50',
                line=dict(color='red', width=2)
            ))
        
        # Add Bollinger Bands
        if 'bb_upper' in indicators:
            fig.add_trace(go.Scatter(
                x=df.index,
                y=indicators['bb_upper'],
                name='BB Upper',
                line=dict(color='gray', dash='dash'),
                opacity=0.5
            ))
            
            fig.add_trace(go.Scatter(
                x=df.index,
                y=indicators['bb_lower'],
                name='BB Lower',
                line=dict(color='gray', dash='dash'),
                fill='tonexty',
                opacity=0.1
            ))
        
        fig.update_layout(
            title=f'{symbol} - Price Chart with Technical Analysis',
            xaxis_title='Date',
            yaxis_title='Price ($)',
            height=400,
            showlegend=True
        )
        
        return fig
    
    def _create_rsi_chart(self, indicators):
        """Create RSI chart"""
        if 'rsi' not in indicators or indicators['rsi'].empty:
            return {'data': [], 'layout': {'title': 'RSI - No data available'}}
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=indicators['rsi'].index,
            y=indicators['rsi'].values,
            name='RSI',
            line=dict(color='purple', width=2)
        ))
        
        # Add overbought/oversold lines
        fig.add_hline(y=70, line_dash="dash", line_color="red", 
                     annotation_text="Overbought (70)")
        fig.add_hline(y=30, line_dash="dash", line_color="green", 
                     annotation_text="Oversold (30)")
        
        fig.update_layout(
            title='Relative Strength Index (RSI)',
            xaxis_title='Date',
            yaxis_title='RSI',
            height=250,
            yaxis=dict(range=[0, 100])
        )
        
        return fig
    
    def _create_macd_chart(self, indicators):
        """Create MACD chart"""
        if 'macd' not in indicators or indicators['macd'].empty:
            return {'data': [], 'layout': {'title': 'MACD - No data available'}}
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=indicators['macd'].index,
            y=indicators['macd'].values,
            name='MACD',
            line=dict(color='blue', width=2)
        ))
        
        if 'macd_signal' in indicators:
            fig.add_trace(go.Scatter(
                x=indicators['macd_signal'].index,
                y=indicators['macd_signal'].values,
                name='Signal',
                line=dict(color='red', width=2)
            ))
        
        if 'macd_histogram' in indicators:
            fig.add_trace(go.Bar(
                x=indicators['macd_histogram'].index,
                y=indicators['macd_histogram'].values,
                name='Histogram',
                opacity=0.3
            ))
        
        fig.update_layout(
            title='MACD (Moving Average Convergence Divergence)',
            xaxis_title='Date',
            yaxis_title='MACD',
            height=250
        )
        
        return fig
    
    def _create_portfolio_component(self):
        """Create portfolio statistics component"""
        try:
            stats = self.database.get_trading_statistics(days=30)
            
            if not stats or stats.get('total_trades', 0) == 0:
                return html.Div("No trading data available", style={'color': '#7f8c8d'})
            
            win_rate_color = '#27ae60' if stats['win_rate'] > 50 else '#e74c3c'
            pnl_color = '#27ae60' if stats['total_pnl'] > 0 else '#e74c3c'
            
            return html.Div([
                html.P(f"Total Trades: {stats['total_trades']}"),
                html.P(f"Win Rate: {stats['win_rate']:.1f}%", 
                      style={'color': win_rate_color}),
                html.P(f"Total P&L: ${stats['total_pnl']:.2f}", 
                      style={'color': pnl_color}),
                html.P(f"Avg Win: ${stats['avg_win']:.2f}"),
                html.P(f"Avg Loss: ${stats['avg_loss']:.2f}"),
                html.P(f"Profit Factor: {stats['profit_factor']:.2f}")
            ])
            
        except Exception as e:
            return html.Div(f"Error loading portfolio stats: {e}", style={'color': '#e74c3c'})
    
    def _create_recent_signals_component(self):
        """Create recent signals component"""
        try:
            signals = self.database.get_recent_signals(limit=5)
            
            if not signals:
                return html.Div("No recent signals", style={'color': '#7f8c8d'})
            
            signal_items = []
            for signal in signals:
                rec_color = ('#27ae60' if 'BUY' in signal['recommendation'] 
                           else '#e74c3c' if 'SELL' in signal['recommendation'] 
                           else '#f39c12')
                
                signal_items.append(html.Div([
                    html.Strong(f"{signal['symbol']}: {signal['recommendation']}", 
                              style={'color': rec_color}),
                    html.Br(),
                    html.Small(f"${signal['price']:.2f} - {signal['timestamp']}")
                ], style={'margin-bottom': '10px', 'padding': '5px', 
                         'border-left': f'3px solid {rec_color}'}))
            
            return html.Div(signal_items)
            
        except Exception as e:
            return html.Div(f"Error loading recent signals: {e}", style={'color': '#e74c3c'})
    
    def run(self, host='0.0.0.0', port=8050, debug=False):
        """Run the dashboard"""
        print(f"🌐 Starting Crypto Trading Dashboard at http://{host}:{port}")
        print("📊 Dashboard Features:")
        print("   • Real-time price monitoring")
        print("   • Technical analysis charts")
        print("   • Trading signal alerts")
        print("   • Portfolio statistics")
        print("\n🔄 Dashboard will auto-refresh every minute")
        print("🛑 Press Ctrl+C to stop")
        
        self.app.run(host=host, port=port, debug=debug)

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Crypto Trading Dashboard')
    parser.add_argument('--config', default='config/config.json',
                       help='Path to configuration file')
    parser.add_argument('--host', default='0.0.0.0',
                       help='Host to bind to')
    parser.add_argument('--port', type=int, default=8050,
                       help='Port to bind to')
    parser.add_argument('--debug', action='store_true',
                       help='Run in debug mode')
    
    args = parser.parse_args()
    
    # Initialize and run dashboard
    dashboard = TradingDashboard(args.config)
    dashboard.run(host=args.host, port=args.port, debug=args.debug)

if __name__ == "__main__":
    main()
