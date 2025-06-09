"""
Base Strategy Module
-------------------

This module defines the BaseStrategy class, which provides a foundation for implementing trading strategies in Backtrader. It includes trade logging, notification integration, and utility methods for recording and notifying about trades and errors.

Main Features:
- Trade logging and recording
- Integration with notification systems (Telegram)
- Utility hooks for trade entry, exit, and error handling
- Pluggable exit logic system for flexible position management
- Designed for extension by concrete strategy classes

Classes:
- BaseStrategy: Abstract base class for trading strategies
"""

import datetime
import json
import os
from typing import Any, Dict, Optional

import backtrader as bt
from src.exit.exit_registry import get_exit_class
from src.notification.logger import _logger
from src.notification.telegram_notifier import create_notifier


class BaseStrategy(bt.Strategy):
    """
    Abstract base class for trading strategies. Accepts a single params/config dictionary.
    The notify flag (self.notify) is set from params['notify'] if present.

    Exit Logic:
    - Uses a pluggable exit logic system that can be configured via parameters
    - Available exit logics include:
        - ATR-based exits (atr_exit)
        - Fixed take profit/stop loss (fixed_tp_sl_exit)
        - Moving average crossover (ma_crossover_exit)
        - Time-based exits (time_based_exit)
        - Trailing stop exits (trailing_stop_exit)
    - Exit logic is configured via:
        - exit_logic_name: Name of the exit logic to use
        - exit_params: Dictionary of parameters for the selected exit logic
    """

    def __init__(self, params: dict):
        """
        Initialize the strategy with parameters.

        Args:
            params (dict): Dictionary of strategy parameters
        """
        super().__init__()  # Initialize bt.Strategy first
        self.params = params
        self.notify = params.get("notify", False)
        self.printlog = params.get("printlog", False)
        self.trades = []
        self.notifier = create_notifier() if self.notify else None
        
        # Initialize exit logic
        exit_logic_name = self.params.get("exit_logic_name", "atr_exit")
        exit_params = self.params.get("exit_params", {})
        exit_class = get_exit_class(exit_logic_name)
        self.exit_logic = exit_class(exit_params)

        # Initialize ATR indicator if using ATR-based exit
        if exit_logic_name == "atr_exit":
            use_talib = self.params.get("use_talib", False)
            atr_period = self.params.get("atr_period", 14)
            if use_talib:
                self.atr = bt.talib.ATR(
                    self.data.high,
                    self.data.low,
                    self.data.close,
                    timeperiod=atr_period
                )
            else:
                self.atr = bt.ind.ATR(period=atr_period)

        self.order = None
        self.entry_price = None
        self.highest_price = None
        self.current_trade = None
        self.trade_active = False
        self.last_exit_reason = None

    def next(self):
        """
        Called on each new bar. Updates exit logic with current ATR value if using ATR-based exits.
        Should be called on each new bar before check_exit is called.
        """
        # Call exit logic's next method with ATR value if using ATR-based exits
        if hasattr(self, 'atr'):
            self.exit_logic.next(atr_value=self.atr[0])

    def log(
        self,
        txt: str,
        dt: Optional[datetime.datetime] = None,
        doprint: bool = False,
        level: str = "info",
    ) -> None:
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
        folder = os.path.join("logs", "json")
        os.makedirs(folder, exist_ok=True)
        # Use entry_time or current time for filename
        ts = trade_dict.get("entry_time")
        if hasattr(ts, "isoformat"):
            ts = ts.isoformat()
        elif ts is None:
            import datetime
            ts = datetime.datetime.now().isoformat()
        symbol = trade_dict.get("symbol", "UNKNOWN")
        fname = (
            f"{symbol}_{ts.replace(':', '').replace('-', '').replace('T', '_')}.json"
        )
        fpath = os.path.join(folder, fname)
        # Write individual trade file
        try:
            with open(fpath, "w", encoding="utf-8") as f:
                json.dump(trade_dict, f, default=str, indent=2)
        except Exception as e:
            self.log(f"Failed to write trade JSON: {e}", level="error")
        # Append to master trades.json
        master_path = os.path.join(folder, "trades.json")
        try:
            if os.path.exists(master_path):
                with open(master_path, "r+", encoding="utf-8") as f:
                    try:
                        all_trades = json.load(f)
                    except Exception:
                        all_trades = []
                    all_trades.append(trade_dict)
                    f.seek(0)
                    json.dump(all_trades, f, default=str, indent=2)
                    f.truncate()
            else:
                with open(master_path, "w", encoding="utf-8") as f:
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

        self.log(f"OPERATION PROFIT, GROSS {trade.pnl:.2f}, NET {trade.pnlcomm:.2f}")

    def get_trades(self):
        """Return the list of recorded trades for this strategy instance."""
        return self.trades
