# Crypto Trading Bot

__version__ = "1.0.0"
__author__ = "Crypto Trading Bot"
__description__ = "A comprehensive cryptocurrency trading analysis software"

from .coinbase_client import CoinbaseClient
from .technical_analysis import TechnicalAnalysis
from .trading_signals import TradingSignals
from .risk_management import RiskManagement
from .alerts import AlertSystem
from .database import DatabaseManager

__all__ = [
    'CoinbaseClient',
    'TechnicalAnalysis', 
    'TradingSignals',
    'RiskManagement',
    'AlertSystem',
    'DatabaseManager'
]
