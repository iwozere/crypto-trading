"""
Custom Strategy Module

This module implements a custom trading strategy with support for modular entry/exit mixins.
It provides:
1. Flexible entry and exit logic through mixins
2. Position and trade tracking
3. Equity curve tracking
4. Performance metrics collection
"""

from typing import Any, Dict

import backtrader as bt
from src.entry.entry_mixin_factory import (get_entry_mixin,
                                           get_entry_mixin_from_config,
                                           ENTRY_MIXIN_REGISTRY)
from src.exit.exit_mixin_factory import (get_exit_mixin,
                                         get_exit_mixin_from_config,
                                         EXIT_MIXIN_REGISTRY)
from src.notification.logger import _logger, log_exception


class CustomStrategy(bt.Strategy):
    """
    Main strategy with support for modular entry/exit mixins.

    Parameters:
    -----------
    strategy_config : dict
        Configuration dictionary containing:
        - entry_logic: Entry mixin configuration
        - exit_logic: Exit mixin configuration
        - position_size: Position size as fraction of capital (default: 0.1)
        - use_talib: Whether to use TA-Lib for indicator calculations
    """

    params = (
        ("strategy_config", None),  # Strategy configuration
        ("position_size", 1.0),     # Default position size
    )

    def __init__(self):
        """Initialize strategy with configuration"""
        try:
            super().__init__()  # Call parent's __init__ first
            
            # Initialize basic attributes
            self._use_talib = False  # Default value
            self.entry_logic = None
            self.exit_logic = None
            
            # Initialize trade tracking
            self.trades = []
            self.has_position = False
            self.current_exit_reason = None  # Track current exit reason
            
            # Initialize equity curve tracking
            self.equity_curve = []
            self.equity_dates = []
            
            # Initialize entry and exit mixins
            self.entry_mixin = None
            self.exit_mixin = None
            
            # Set configuration from params
            if self.p.strategy_config:
                self._use_talib = self.p.strategy_config.get("use_talib", False)
                self.entry_logic = self.p.strategy_config.get("entry_logic")
                self.exit_logic = self.p.strategy_config.get("exit_logic")
            
            # Create mixins
            if self.entry_logic:
                entry_mixin_class = ENTRY_MIXIN_REGISTRY[self.entry_logic["name"]]
                if entry_mixin_class:
                    self.entry_mixin = entry_mixin_class(params=self.entry_logic["params"])
                    self.entry_mixin.strategy = self
                    self.entry_mixin._init_indicators()
            
            if self.exit_logic:
                exit_mixin_class = EXIT_MIXIN_REGISTRY[self.exit_logic["name"]]
                if exit_mixin_class:
                    self.exit_mixin = exit_mixin_class(params=self.exit_logic["params"])
                    self.exit_mixin.strategy = self
                    self.exit_mixin._init_indicators()
        except Exception as e:
            log_exception(_logger)
            raise

    @property
    def use_talib(self):
        """Get whether to use TA-Lib"""
        return self._use_talib

    def next(self):
        """Main strategy logic"""
        try:
            # Track equity curve
            self.equity_curve.append(self.broker.getvalue())
            self.equity_dates.append(self.data.datetime.datetime())
            
            if not self.has_position and self.entry_mixin and self.entry_mixin.should_enter():
                self.buy(size=self.p.position_size)
                self.has_position = True
            elif self.has_position and self.exit_mixin and self.exit_mixin.should_exit():
                self.current_exit_reason = self.exit_mixin.get_exit_reason()  # Get reason before selling
                self.sell(size=self.p.position_size)
                self.has_position = False
        except Exception as e:
            log_exception(_logger)
            raise

    def notify_trade(self, trade):
        """Record trade information"""
        try:
            _logger.info(f"Trade notification received - Status: {'CLOSED' if trade.isclosed else 'OPEN'}, "
                        f"Size: {trade.size}, PnL: {trade.pnl}, "
                        f"Open Price: {trade.priceopen}, Close Price: {trade.priceclose}")
            
            if trade.isclosed:
                self.trades.append({
                    'entry_time': trade.dtopen,
                    'entry_price': trade.priceopen,
                    'exit_time': trade.dtclose,
                    'exit_price': trade.priceclose,
                    'pnl': trade.pnl,
                    'size': trade.size,
                    'symbol': self.data._name,
                    'direction': 'long' if trade.size > 0 else 'short',
                    'commission': trade.commission,
                    'pnl_comm': trade.pnlcomm,
                    'exit_reason': self.current_exit_reason or 'unknown'  # Add exit reason
                })
                self.has_position = False
                self.current_exit_reason = None  # Reset exit reason
        except Exception as e:
            log_exception(_logger)
            raise


# Example of creating a strategy with a new approach
def create_strategy_example():
    """Example of creating a strategy with different configurations"""

    # Configuration 1: Simple RSI + BB strategy
    strategy_config_1 = {
        "entry_logic": {
            "name": "RSIBBMixin",
            "params": {
                "rsi_period": 14,
                "rsi_oversold": 30,
                "bb_period": 20,
                "use_bb_touch": True,
            },
        },
        "exit_logic": {
            "name": "FixedRatioExitMixin",
            "params": {"profit_ratio": 1.5, "stop_loss_ratio": 0.5},
        },
        "position_size": 0.1,
        "use_talib": False,
    }

    # Configuration 2: More complex strategy with RSI + Ichimoku
    strategy_config_2 = {
        "entry_logic": {
            "name": "RSIIchimokuMixin",
            "params": {
                "rsi_period": 21,
                "rsi_oversold": 25,
                "tenkan_period": 9,
                "kijun_period": 26,
                "require_above_cloud": True,
            },
        },
        "exit_logic": {
            "name": "TrailingStopExitMixin",
            "params": {"trail_percent": 5.0, "min_profit_percent": 2.0},
        },
        "position_size": 0.1,
        "use_talib": False,
    }

    return strategy_config_1, strategy_config_2


class StrategyConfigBuilder:
    """Helper for creating strategy configurations"""

    def __init__(self):
        self.config = {
            "entry_logic": None,
            "exit_logic": None,
            "position_size": 0.1,
            "use_talib": False,
        }

    def set_entry_mixin(self, name: str, params: Dict[str, Any] = None):
        """Set entry mixin configuration"""
        self.config["entry_logic"] = {"name": name, "params": params or {}}
        return self

    def set_exit_mixin(self, name: str, params: Dict[str, Any] = None):
        """Set exit mixin configuration"""
        self.config["exit_logic"] = {"name": name, "params": params or {}}
        return self

    def set_position_size(self, size: float):
        """Set position size as fraction of capital"""
        if not 0 < size <= 1:
            raise ValueError("Position size must be between 0 and 1")
        self.config["position_size"] = size
        return self

    def set_use_talib(self, use_talib: bool):
        """Set whether to use TA-Lib"""
        self.config["use_talib"] = use_talib
        return self

    def build(self) -> Dict[str, Any]:
        """Build the final strategy configuration"""
        if not self.config["entry_logic"]:
            raise ValueError("Entry mixin configuration is required")
        if not self.config["exit_logic"]:
            raise ValueError("Exit mixin configuration is required")
        return self.config
