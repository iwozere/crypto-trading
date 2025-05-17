import sqlite3
from typing import Dict, List, Any
from datetime import datetime
import json

class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._create_tables()
        
    def _create_tables(self):
        """Create necessary database tables if they don't exist."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Create trades table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME,
                    type TEXT,
                    entry_price REAL,
                    exit_price REAL,
                    pnl REAL,
                    balance REAL,
                    reason TEXT,
                    indicators TEXT
                )
            ''')
            
            # Create performance_metrics table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS performance_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME,
                    total_trades INTEGER,
                    winning_trades INTEGER,
                    losing_trades INTEGER,
                    win_rate REAL,
                    total_pnl REAL,
                    max_drawdown REAL,
                    sharpe_ratio REAL,
                    parameters TEXT
                )
            ''')
            
            conn.commit()
            
    def save_trade(self, trade: Dict[str, Any]):
        """Save a trade to the database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO trades (
                    timestamp, type, entry_price, exit_price, pnl,
                    balance, reason, indicators
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                trade['timestamp'],
                trade['type'],
                trade['entry_price'],
                trade['exit_price'],
                trade['pnl'],
                trade['balance'],
                trade['reason'],
                json.dumps(trade.get('indicators', {}))
            ))
            
            conn.commit()
            
    def save_performance_metrics(self, metrics: Dict[str, Any], parameters: Dict[str, Any]):
        """Save performance metrics to the database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO performance_metrics (
                    timestamp, total_trades, winning_trades, losing_trades,
                    win_rate, total_pnl, max_drawdown, sharpe_ratio, parameters
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                datetime.now(),
                metrics['total_trades'],
                metrics['winning_trades'],
                metrics['losing_trades'],
                metrics['win_rate'],
                metrics['total_pnl'],
                metrics['max_drawdown'],
                metrics['sharpe_ratio'],
                json.dumps(parameters)
            ))
            
            conn.commit()
            
    def get_trades(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Retrieve recent trades from the database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM trades
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (limit,))
            
            columns = [description[0] for description in cursor.description]
            trades = []
            
            for row in cursor.fetchall():
                trade = dict(zip(columns, row))
                trade['indicators'] = json.loads(trade['indicators'])
                trades.append(trade)
                
            return trades
            
    def get_performance_metrics(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Retrieve recent performance metrics from the database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM performance_metrics
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (limit,))
            
            columns = [description[0] for description in cursor.description]
            metrics = []
            
            for row in cursor.fetchall():
                metric = dict(zip(columns, row))
                metric['parameters'] = json.loads(metric['parameters'])
                metrics.append(metric)
                
            return metrics 