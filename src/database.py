import sqlite3
import pandas as pd
import json
from typing import Dict, List, Optional, Tuple, Any, Union
from datetime import datetime, timedelta
import logging
import os

class DatabaseManager:
    """
    Database manager for storing price data, signals, and trading history
    """
    
    def __init__(self, db_path: str = 'data/trading_data.db'):
        """Initialize database connection"""
        try:
            # Ensure data directory exists
            import os
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
            
            self.db_path = db_path
            self.logger = logging.getLogger(__name__)
            
            # Test database connection
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("SELECT 1")
                self.logger.info(f"Database connection established: {db_path}")
                
            self._initialize_database()
            
        except sqlite3.Error as e:
            self.logger.error(f"Database initialization error: {e}")
            raise
        except OSError as e:
            self.logger.error(f"File system error creating database: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error initializing database: {e}")
            raise
        
        # Ensure data directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        self._initialize_database()
    
    def _initialize_database(self):
        """Initialize database tables"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Price data table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS price_data (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        symbol TEXT NOT NULL,
                        timestamp DATETIME NOT NULL,
                        open_price REAL NOT NULL,
                        high_price REAL NOT NULL,
                        low_price REAL NOT NULL,
                        close_price REAL NOT NULL,
                        volume REAL NOT NULL,
                        UNIQUE(symbol, timestamp)
                    )
                ''')
                
                # Trading signals table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS trading_signals (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        symbol TEXT NOT NULL,
                        timestamp DATETIME NOT NULL,
                        price REAL NOT NULL,
                        recommendation TEXT NOT NULL,
                        buy_strength REAL NOT NULL,
                        sell_strength REAL NOT NULL,
                        signals_json TEXT NOT NULL,
                        support_resistance_json TEXT
                    )
                ''')
                
                # Portfolio positions table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS positions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        symbol TEXT NOT NULL,
                        entry_timestamp DATETIME NOT NULL,
                        exit_timestamp DATETIME,
                        direction TEXT NOT NULL,
                        entry_price REAL NOT NULL,
                        exit_price REAL,
                        position_size REAL NOT NULL,
                        stop_loss_price REAL,
                        take_profit_price REAL,
                        pnl_amount REAL,
                        pnl_percentage REAL,
                        status TEXT DEFAULT 'OPEN'
                    )
                ''')
                
                # Performance metrics table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS performance_metrics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        date DATE NOT NULL,
                        total_value REAL NOT NULL,
                        daily_return REAL,
                        drawdown REAL,
                        winning_trades INTEGER DEFAULT 0,
                        losing_trades INTEGER DEFAULT 0,
                        total_trades INTEGER DEFAULT 0,
                        UNIQUE(date)
                    )
                ''')
                
                # Create indexes for better performance
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_price_symbol_timestamp ON price_data(symbol, timestamp)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_signals_symbol_timestamp ON trading_signals(symbol, timestamp)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_positions_symbol ON positions(symbol)')
                
                conn.commit()
                self.logger.info("Database initialized successfully")
                
        except Exception as e:
            self.logger.error(f"Error initializing database: {e}")
    
    def store_price_data(self, symbol: str, df: pd.DataFrame) -> bool:
        """Store price data in database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Prepare data for insertion
                df_copy = df.copy()
                df_copy['symbol'] = symbol
                df_copy = df_copy.reset_index()
                
                # Rename columns to match database schema
                df_copy = df_copy.rename(columns={
                    'timestamp': 'timestamp',
                    'open': 'open_price',
                    'high': 'high_price',
                    'low': 'low_price',
                    'close': 'close_price',
                    'volume': 'volume'
                })
                
                # Insert data using replace to handle duplicates
                df_copy.to_sql('price_data', conn, if_exists='append', index=False)
                
                self.logger.info(f"Stored {len(df_copy)} price records for {symbol}")
                return True
                
        except Exception as e:
            self.logger.error(f"Error storing price data for {symbol}: {e}")
            return False
    
    def get_price_data(self, symbol: str, start_date: datetime = None, 
                      end_date: datetime = None) -> pd.DataFrame:
        """Retrieve price data from database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                query = "SELECT * FROM price_data WHERE symbol = ?"
                params = [symbol]
                
                if start_date:
                    query += " AND timestamp >= ?"
                    params.append(start_date)
                
                if end_date:
                    query += " AND timestamp <= ?"
                    params.append(end_date)
                
                query += " ORDER BY timestamp ASC"
                
                df = pd.read_sql_query(query, conn, params=params)
                
                if not df.empty:
                    df['timestamp'] = pd.to_datetime(df['timestamp'])
                    df.set_index('timestamp', inplace=True)
                
                return df
                
        except Exception as e:
            self.logger.error(f"Error retrieving price data for {symbol}: {e}")
            return pd.DataFrame()
    
    def store_trading_signal(self, symbol: str, signal: Dict) -> bool:
        """Store trading signal in database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT OR REPLACE INTO trading_signals 
                    (symbol, timestamp, price, recommendation, buy_strength, sell_strength, 
                     signals_json, support_resistance_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    symbol,
                    signal['timestamp'],
                    signal['price'],
                    signal['recommendation'],
                    signal['buy_strength'],
                    signal['sell_strength'],
                    json.dumps(signal['signals']),
                    json.dumps(signal.get('support_resistance', {}))
                ))
                
                conn.commit()
                return True
                
        except Exception as e:
            self.logger.error(f"Error storing trading signal for {symbol}: {e}")
            return False
    
    def get_recent_signals(self, symbol: str = None, limit: int = 50) -> List[Dict]:
        """Get recent trading signals"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                if symbol:
                    query = '''
                        SELECT * FROM trading_signals 
                        WHERE symbol = ? 
                        ORDER BY timestamp DESC 
                        LIMIT ?
                    '''
                    params = [symbol, limit]
                else:
                    query = '''
                        SELECT * FROM trading_signals 
                        ORDER BY timestamp DESC 
                        LIMIT ?
                    '''
                    params = [limit]
                
                cursor = conn.cursor()
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                signals = []
                for row in rows:
                    signals.append({
                        'id': row[0],
                        'symbol': row[1],
                        'timestamp': row[2],
                        'price': row[3],
                        'recommendation': row[4],
                        'buy_strength': row[5],
                        'sell_strength': row[6],
                        'signals': json.loads(row[7]),
                        'support_resistance': json.loads(row[8]) if row[8] else {}
                    })
                
                return signals
                
        except Exception as e:
            self.logger.error(f"Error retrieving recent signals: {e}")
            return []
    
    def store_position(self, position: Dict) -> bool:
        """Store trading position in database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO positions 
                    (symbol, entry_timestamp, direction, entry_price, position_size, 
                     stop_loss_price, take_profit_price, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    position['symbol'],
                    position['entry_timestamp'],
                    position['direction'],
                    position['entry_price'],
                    position['position_size'],
                    position.get('stop_loss_price'),
                    position.get('take_profit_price'),
                    'OPEN'
                ))
                
                conn.commit()
                return True
                
        except Exception as e:
            self.logger.error(f"Error storing position: {e}")
            return False
    
    def update_position(self, position_id: int, exit_data: Dict) -> bool:
        """Update position with exit data"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    UPDATE positions 
                    SET exit_timestamp = ?, exit_price = ?, pnl_amount = ?, 
                        pnl_percentage = ?, status = 'CLOSED'
                    WHERE id = ?
                ''', (
                    exit_data['exit_timestamp'],
                    exit_data['exit_price'],
                    exit_data['pnl_amount'],
                    exit_data['pnl_percentage'],
                    position_id
                ))
                
                conn.commit()
                return True
                
        except Exception as e:
            self.logger.error(f"Error updating position {position_id}: {e}")
            return False
    
    def get_open_positions(self, symbol: str = None) -> List[Dict]:
        """Get open positions"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                if symbol:
                    query = "SELECT * FROM positions WHERE symbol = ? AND status = 'OPEN'"
                    params = [symbol]
                else:
                    query = "SELECT * FROM positions WHERE status = 'OPEN'"
                    params = []
                
                cursor = conn.cursor()
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                positions = []
                for row in rows:
                    positions.append({
                        'id': row[0],
                        'symbol': row[1],
                        'entry_timestamp': row[2],
                        'direction': row[4],
                        'entry_price': row[5],
                        'position_size': row[7],
                        'stop_loss_price': row[8],
                        'take_profit_price': row[9]
                    })
                
                return positions
                
        except Exception as e:
            self.logger.error(f"Error retrieving open positions: {e}")
            return []
    
    def get_trading_statistics(self, days: int = 30) -> Dict:
        """Get trading statistics for the specified period"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                start_date = datetime.now() - timedelta(days=days)
                
                # Get closed positions
                cursor.execute('''
                    SELECT * FROM positions 
                    WHERE status = 'CLOSED' AND entry_timestamp >= ?
                ''', (start_date,))
                
                positions = cursor.fetchall()
                
                if not positions:
                    return {
                        'total_trades': 0,
                        'winning_trades': 0,
                        'losing_trades': 0,
                        'win_rate': 0,
                        'total_pnl': 0,
                        'avg_win': 0,
                        'avg_loss': 0,
                        'profit_factor': 0
                    }
                
                total_trades = len(positions)
                winning_trades = sum(1 for pos in positions if pos[10] and pos[10] > 0)  # pnl_amount > 0
                losing_trades = total_trades - winning_trades
                
                win_pnl = sum(pos[10] for pos in positions if pos[10] and pos[10] > 0)
                loss_pnl = sum(abs(pos[10]) for pos in positions if pos[10] and pos[10] < 0)
                
                stats = {
                    'total_trades': total_trades,
                    'winning_trades': winning_trades,
                    'losing_trades': losing_trades,
                    'win_rate': (winning_trades / total_trades) * 100 if total_trades > 0 else 0,
                    'total_pnl': sum(pos[10] for pos in positions if pos[10]),
                    'avg_win': win_pnl / winning_trades if winning_trades > 0 else 0,
                    'avg_loss': loss_pnl / losing_trades if losing_trades > 0 else 0,
                    'profit_factor': win_pnl / loss_pnl if loss_pnl > 0 else 0
                }
                
                return stats
                
        except Exception as e:
            self.logger.error(f"Error retrieving trading statistics: {e}")
            return {}
    
    def cleanup_old_data(self, days_to_keep: int = 90):
        """Clean up old data to prevent database from growing too large"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cutoff_date = datetime.now() - timedelta(days=days_to_keep)
                
                # Clean old price data
                cursor.execute('DELETE FROM price_data WHERE timestamp < ?', (cutoff_date,))
                
                # Clean old signals (keep closed positions)
                cursor.execute('DELETE FROM trading_signals WHERE timestamp < ?', (cutoff_date,))
                
                conn.commit()
                self.logger.info(f"Cleaned up data older than {days_to_keep} days")
                
        except Exception as e:
            self.logger.error(f"Error cleaning up old data: {e}")
