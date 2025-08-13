import requests
import json
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import pandas as pd

class CoinbaseClient:
    """
    Client for interacting with Coinbase Pro API
    """
    
    def __init__(self, config: Dict):
        self.api_url = config.get('api_url', 'https://api.exchange.coinbase.com')
        self.sandbox = config.get('sandbox', True)
        self.api_key = config.get('api_key', '')
        self.api_secret = config.get('api_secret', '')
        self.passphrase = config.get('passphrase', '')
        
        if self.sandbox:
            self.api_url = 'https://api-public.sandbox.exchange.coinbase.com'
            
        self.session = requests.Session()
        self.session.headers.update({
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        })
        
        self.logger = logging.getLogger(__name__)
    
    def get_products(self) -> List[Dict]:
        """Get all available trading pairs"""
        try:
            response = self.session.get(f"{self.api_url}/products")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            self.logger.error(f"Error getting products: {e}")
            return []
    
    def get_product_ticker(self, product_id: str) -> Optional[Dict]:
        """Get current ticker for a product"""
        try:
            response = self.session.get(f"{self.api_url}/products/{product_id}/ticker", timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # Validate response data
            if not data or 'price' not in data:
                self.logger.error(f"Invalid ticker data for {product_id}: {data}")
                return None
                
            return data
        except requests.exceptions.Timeout:
            self.logger.error(f"Timeout getting ticker for {product_id}")
            return None
        except requests.exceptions.ConnectionError:
            self.logger.error(f"Connection error getting ticker for {product_id}")
            return None
        except requests.exceptions.HTTPError as e:
            self.logger.error(f"HTTP error getting ticker for {product_id}: {e}")
            return None
        except ValueError as e:
            self.logger.error(f"JSON decode error for {product_id}: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error getting ticker for {product_id}: {e}")
            return None
    
    def get_product_candles(self, product_id: str, start: str, end: str, granularity: int = 300) -> Optional[List[List]]:
        """Get historical candles for a product"""
        try:
            params = {
                'start': start,
                'end': end,
                'granularity': granularity
            }
            
            response = self.session.get(
                f"{self.api_url}/products/{product_id}/candles", 
                params=params, 
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            
            # Validate response data
            if not isinstance(data, list):
                self.logger.error(f"Invalid candles data format for {product_id}: {type(data)}")
                return None
                
            if not data:
                self.logger.warning(f"No candles data returned for {product_id}")
                return []
                
            # Validate each candle has required fields
            for i, candle in enumerate(data[:5]):  # Check first 5 candles
                if not isinstance(candle, list) or len(candle) < 6:
                    self.logger.error(f"Invalid candle format at index {i} for {product_id}: {candle}")
                    return None
                    
            return data
            
        except requests.exceptions.Timeout:
            self.logger.error(f"Timeout getting candles for {product_id}")
            return None
        except requests.exceptions.ConnectionError:
            self.logger.error(f"Connection error getting candles for {product_id}")
            return None
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                self.logger.error(f"Product not found: {product_id}")
            else:
                self.logger.error(f"HTTP error getting candles for {product_id}: {e}")
            return None
        except ValueError as e:
            self.logger.error(f"JSON decode error for {product_id}: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error getting candles for {product_id}: {e}")
            return None
    
    def get_historical_data(self, product_id: str, days: int = 30, 
                          granularity: int = 3600) -> pd.DataFrame:
        """
        Get historical price data as pandas DataFrame
        
        Args:
            product_id: Trading pair
            days: Number of days of history
            granularity: Time interval in seconds
        """
        try:
            end_time = datetime.now()
            start_time = end_time - timedelta(days=days)
            
            start_iso = start_time.isoformat()
            end_iso = end_time.isoformat()
            
            candles = self.get_product_candles(
                product_id, start_iso, end_iso, granularity
            )
            
            if not candles:
                return pd.DataFrame()
            
            # Convert to DataFrame
            df = pd.DataFrame(candles, columns=[
                'timestamp', 'low', 'high', 'open', 'close', 'volume'
            ])
            
            # Convert timestamp to datetime
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
            df.set_index('timestamp', inplace=True)
            
            # Convert price columns to float
            price_columns = ['low', 'high', 'open', 'close', 'volume']
            df[price_columns] = df[price_columns].astype(float)
            
            # Sort by timestamp
            df.sort_index(inplace=True)
            
            return df
            
        except Exception as e:
            self.logger.error(f"Error getting historical data for {product_id}: {e}")
            return pd.DataFrame()
    
    def get_24hr_stats(self, product_id: str) -> Optional[Dict]:
        """Get 24hr stats for a product"""
        try:
            response = self.session.get(f"{self.api_url}/products/{product_id}/stats")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            self.logger.error(f"Error getting 24hr stats for {product_id}: {e}")
            return None
    
    def get_order_book(self, product_id: str, level: int = 1) -> Optional[Dict]:
        """
        Get order book for a product
        
        Args:
            product_id: Trading pair
            level: Level of detail (1, 2, or 3)
        """
        try:
            params = {'level': level}
            response = self.session.get(
                f"{self.api_url}/products/{product_id}/book",
                params=params
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            self.logger.error(f"Error getting order book for {product_id}: {e}")
            return None
    
    def is_market_open(self, product_id: str) -> bool:
        """Check if market is open for trading"""
        try:
            ticker = self.get_product_ticker(product_id)
            return ticker is not None and 'price' in ticker
        except Exception as e:
            self.logger.error(f"Error checking market status for {product_id}: {e}")
            return False
