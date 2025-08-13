"""
Centralized error handling for the crypto trading bot
"""
import logging
import traceback
from functools import wraps
from typing import Any, Callable, Dict, Optional
import time

class ErrorHandler:
    """Centralized error handling and recovery"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.error_counts = {}
        self.max_retries = 3
        self.retry_delay = 1  # seconds
    
    def with_error_handling(self, operation_name: str = "operation", 
                          max_retries: int = None, 
                          retry_delay: float = None,
                          default_return: Any = None):
        """Decorator for automatic error handling with retries"""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs) -> Any:
                retries = max_retries if max_retries is not None else self.max_retries
                delay = retry_delay if retry_delay is not None else self.retry_delay
                
                for attempt in range(retries + 1):
                    try:
                        result = func(*args, **kwargs)
                        
                        # Reset error count on success
                        if operation_name in self.error_counts:
                            del self.error_counts[operation_name]
                            
                        return result
                        
                    except Exception as e:
                        # Track error count
                        self.error_counts[operation_name] = self.error_counts.get(operation_name, 0) + 1
                        
                        if attempt < retries:
                            self.logger.warning(
                                f"{operation_name} failed (attempt {attempt + 1}/{retries + 1}): {e}. "
                                f"Retrying in {delay} seconds..."
                            )
                            time.sleep(delay)
                            delay *= 2  # Exponential backoff
                        else:
                            self.logger.error(
                                f"{operation_name} failed after {retries + 1} attempts: {e}\n"
                                f"Traceback: {traceback.format_exc()}"
                            )
                            return default_return
                            
                return default_return
            return wrapper
        return decorator
    
    def handle_api_error(self, error: Exception, operation: str) -> Dict:
        """Handle API-related errors with specific responses"""
        error_msg = str(error)
        
        if "timeout" in error_msg.lower():
            self.logger.error(f"API timeout in {operation}: {error}")
            return {
                'error': 'API_TIMEOUT',
                'message': 'API request timed out',
                'retry_suggested': True
            }
        elif "connection" in error_msg.lower():
            self.logger.error(f"Connection error in {operation}: {error}")
            return {
                'error': 'CONNECTION_ERROR',
                'message': 'Failed to connect to API',
                'retry_suggested': True
            }
        elif "404" in error_msg:
            self.logger.error(f"Resource not found in {operation}: {error}")
            return {
                'error': 'NOT_FOUND',
                'message': 'Requested resource not found',
                'retry_suggested': False
            }
        elif "rate limit" in error_msg.lower():
            self.logger.error(f"Rate limit exceeded in {operation}: {error}")
            return {
                'error': 'RATE_LIMITED',
                'message': 'API rate limit exceeded',
                'retry_suggested': True,
                'retry_delay': 60
            }
        else:
            self.logger.error(f"Unknown API error in {operation}: {error}")
            return {
                'error': 'API_ERROR',
                'message': f'API error: {error}',
                'retry_suggested': True
            }
    
    def handle_data_error(self, error: Exception, operation: str, data_type: str = "data") -> Dict:
        """Handle data-related errors"""
        error_msg = str(error)
        
        if "empty" in error_msg.lower() or "no data" in error_msg.lower():
            self.logger.warning(f"Empty {data_type} in {operation}: {error}")
            return {
                'error': 'EMPTY_DATA',
                'message': f'No {data_type} available',
                'retry_suggested': True
            }
        elif "insufficient" in error_msg.lower():
            self.logger.warning(f"Insufficient {data_type} in {operation}: {error}")
            return {
                'error': 'INSUFFICIENT_DATA',
                'message': f'Insufficient {data_type} for analysis',
                'retry_suggested': False
            }
        elif "invalid" in error_msg.lower() or "format" in error_msg.lower():
            self.logger.error(f"Invalid {data_type} format in {operation}: {error}")
            return {
                'error': 'INVALID_DATA',
                'message': f'Invalid {data_type} format',
                'retry_suggested': False
            }
        else:
            self.logger.error(f"Data error in {operation}: {error}")
            return {
                'error': 'DATA_ERROR',
                'message': f'Data processing error: {error}',
                'retry_suggested': True
            }
    
    def handle_calculation_error(self, error: Exception, operation: str, indicator: str = "indicator") -> Dict:
        """Handle calculation/computation errors"""
        error_msg = str(error)
        
        if "division by zero" in error_msg.lower() or "divide" in error_msg.lower():
            self.logger.error(f"Division by zero in {indicator} calculation ({operation}): {error}")
            return {
                'error': 'DIVISION_BY_ZERO',
                'message': f'Division by zero in {indicator} calculation',
                'retry_suggested': False
            }
        elif "overflow" in error_msg.lower():
            self.logger.error(f"Numeric overflow in {indicator} calculation ({operation}): {error}")
            return {
                'error': 'NUMERIC_OVERFLOW',
                'message': f'Numeric overflow in {indicator} calculation',
                'retry_suggested': False
            }
        elif "nan" in error_msg.lower() or "inf" in error_msg.lower():
            self.logger.warning(f"Invalid numeric values in {indicator} calculation ({operation}): {error}")
            return {
                'error': 'INVALID_NUMERIC',
                'message': f'Invalid numeric values in {indicator} calculation',
                'retry_suggested': True
            }
        else:
            self.logger.error(f"Calculation error in {indicator} ({operation}): {error}")
            return {
                'error': 'CALCULATION_ERROR',
                'message': f'Calculation error in {indicator}: {error}',
                'retry_suggested': True
            }
    
    def get_error_stats(self) -> Dict:
        """Get error statistics"""
        return {
            'error_counts': self.error_counts.copy(),
            'total_errors': sum(self.error_counts.values()),
            'operations_with_errors': len(self.error_counts)
        }
    
    def reset_error_stats(self):
        """Reset error statistics"""
        self.error_counts.clear()
        self.logger.info("Error statistics reset")

# Global error handler instance
error_handler = ErrorHandler()

def safe_execute(operation_name: str = "operation", 
                max_retries: int = 3,
                retry_delay: float = 1.0,
                default_return: Any = None):
    """Convenience decorator for error handling"""
    return error_handler.with_error_handling(
        operation_name=operation_name,
        max_retries=max_retries,
        retry_delay=retry_delay,
        default_return=default_return
    )

def validate_dataframe(df, name: str = "DataFrame", min_rows: int = 1, required_columns: list = None):
    """Validate DataFrame with descriptive errors"""
    if df is None:
        raise ValueError(f"{name} is None")
    
    if df.empty:
        raise ValueError(f"{name} is empty")
    
    if len(df) < min_rows:
        raise ValueError(f"{name} has insufficient data: {len(df)} rows (need {min_rows})")
    
    if required_columns:
        missing_cols = [col for col in required_columns if col not in df.columns]
        if missing_cols:
            raise ValueError(f"{name} missing required columns: {missing_cols}")

def validate_price_data(price: float, symbol: str = "Unknown"):
    """Validate price data"""
    if price is None:
        raise ValueError(f"Price is None for {symbol}")
    
    if not isinstance(price, (int, float)):
        raise ValueError(f"Price must be numeric for {symbol}, got {type(price)}")
    
    if price <= 0:
        raise ValueError(f"Price must be positive for {symbol}, got {price}")
    
    if price > 1000000:  # Sanity check
        raise ValueError(f"Price seems unreasonably high for {symbol}: {price}")
