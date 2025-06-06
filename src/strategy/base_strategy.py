"""
Base Strategy Module
-------------------

This module defines the BaseStrategy class, which provides a foundation for implementing trading strategies in Backtrader. It includes trade logging, notification integration, and utility methods for recording and notifying about trades and errors.

Main Features:
- Trade logging and recording
- Integration with notification systems (Telegram)
- Utility hooks for trade entry, exit, and error handling
- Designed for extension by concrete strategy classes

Classes:
- BaseStrategy: Abstract base class for trading strategies
"""
import backtrader as bt
from src.notification.logger import _logger
from src.notification.telegram_notifier import create_notifier
import os
import json
from typing import Any, Dict, Optional
import datetime
from src.exit.exit_registry import get_exit_class

class BaseStrategy(bt.Strategy):
    """
    Abstract base class for trading strategies. Accepts a single params/config dictionary.
    The notify flag (self.notify) is set from params['notify'] if present.
    """
    def __init__(self, params: dict):
        """
        Initialize the strategy with parameters.
        
        Args:
            params (dict): Dictionary of strategy parameters
        """
        self.params = params
        self.notify = params.get('notify', False)
        self.printlog = params.get('printlog', False)
        self.trades = []
        self.notifier = create_notifier() if self.notify else None
        # Exit logic instantiation
        exit_logic_name = params.get('exit_logic_name', 'atr_exit')
        exit_params = params.get('exit_params', {})
        self.exit_logic = get_exit_class(exit_logic_name)(params=exit_params)

    def log(self, txt: str, dt: Optional[datetime.datetime] = None, doprint: bool = False, level: str = "info") -> None:
        """
        Log a message using the configured logger.
        - level: "info" (default) for normal messages, "error" for errors.
        """
        if self.printlog or doprint:
            if level == "error":
                _logger.error(txt)
            else:
                _logger.info(txt)

    def record_trade(self, trade_dict: Dict[str, Any]) -> None:
        self.trades.append(trade_dict)
        self._save_trade_json(trade_dict)
        self.on_trade_exit(trade_dict)

    def _save_trade_json(self, trade_dict: Dict[str, Any]) -> None:
        """
        Save the trade as a JSON file in logs/json and append to a master trades.json file.
        """
        folder = os.path.join('logs', 'json')
        os.makedirs(folder, exist_ok=True)
        # Use entry_time or current time for filename
        ts = trade_dict.get('entry_time')
        if hasattr(ts, 'isoformat'):
            ts = ts.isoformat()
        elif ts is None:
            import datetime
            ts = datetime.datetime.now().isoformat()
        symbol = trade_dict.get('symbol', 'UNKNOWN')
        fname = f"{symbol}_{ts.replace(':', '').replace('-', '').replace('T', '_')}.json"
        fpath = os.path.join(folder, fname)
        # Write individual trade file
        try:
            with open(fpath, 'w', encoding='utf-8') as f:
                json.dump(trade_dict, f, default=str, indent=2)
        except Exception as e:
            self.log(f"Failed to write trade JSON: {e}", level="error")
        # Append to master trades.json
        master_path = os.path.join(folder, 'trades.json')
        try:
            if os.path.exists(master_path):
                with open(master_path, 'r+', encoding='utf-8') as f:
                    try:
                        all_trades = json.load(f)
                    except Exception:
                        all_trades = []
                    all_trades.append(trade_dict)
                    f.seek(0)
                    json.dump(all_trades, f, default=str, indent=2)
                    f.truncate()
            else:
                with open(master_path, 'w', encoding='utf-8') as f:
                    json.dump([trade_dict], f, default=str, indent=2)
        except Exception as e:
            self.log(f"Failed to append to master trades.json: {e}", level="error")

    def on_trade_entry(self, trade_dict: Dict[str, Any]) -> None:
        if self.notify and self.notifier:
            self.notifier.send_trade_notification(trade_dict)

    def on_trade_exit(self, trade_dict: Dict[str, Any]) -> None:
        if self.notify and self.notifier:
            self.notifier.send_trade_update(trade_dict)

    def on_error(self, error: Exception) -> None:
        if self.notify and self.notifier:
            self.notifier.send_error_notification(str(error))

    def notify_trade(self, trade):
        """
        Handle trade notifications.
        
        Args:
            trade: Trade object
        """
        if not trade.isclosed:
            return
            
        self.log(f'OPERATION PROFIT, GROSS {trade.pnl:.2f}, NET {trade.pnlcomm:.2f}')
        
    def get_trades(self):
        """Return the list of recorded trades for this strategy instance."""
        return self.trades
            
