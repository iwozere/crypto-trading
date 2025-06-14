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
        - use_talib: Whether to use TA-Lib for indicator calculations (default: False)
    """

    params = (
        ("strategy_config", None),  # Strategy configuration
        ("position_size", 1.0),     # Default position size
        ("use_talib", True),        # Whether to use TA-Lib
    )

    def __init__(self):
        """Initialize strategy with configuration"""
        self.strategy_config = self.p.strategy_config
        self.entry_logic = self.strategy_config["entry_logic"]
        self.exit_logic = self.strategy_config["exit_logic"]
        
        # Initialize entry and exit mixins
        self.entry_mixin = self._create_entry_mixin()
        self.exit_mixin = self._create_exit_mixin()
        
        # Initialize trade tracking
        self.trades = []
        self.has_position = False
        
        # Initialize equity curve tracking
        self.equity_curve = []
        self.equity_dates = []

    def _create_entry_mixin(self):
        """Create entry mixin based on configuration"""
        if not self.entry_logic:
            return None
            
        entry_mixin_class = ENTRY_MIXIN_REGISTRY[self.entry_logic["name"]]
        if entry_mixin_class:
            # Get default parameters for the entry mixin
            default_params = entry_mixin_class.get_default_params()
            
            # Create entry mixin with parameters
            entry_mixin = entry_mixin_class(params=default_params)
            entry_mixin.strategy = self
            entry_mixin._init_indicators()
            return entry_mixin
        return None

    def _create_exit_mixin(self):
        """Create exit mixin based on configuration"""
        if not self.exit_logic:
            return None
            
        exit_mixin_class = EXIT_MIXIN_REGISTRY[self.exit_logic["name"]]
        if exit_mixin_class:
            # Get default parameters for the exit mixin
            default_params = exit_mixin_class.get_default_params()
            
            # Create exit mixin with parameters
            exit_mixin = exit_mixin_class(params=default_params)
            exit_mixin.strategy = self
            exit_mixin._init_indicators()
            return exit_mixin
        return None

    def next(self):
        """Main strategy logic"""
        # Track equity curve
        self.equity_curve.append(self.broker.getvalue())
        self.equity_dates.append(self.data.datetime.datetime())
        
        if not self.has_position and self.entry_mixin.should_enter():
            self.buy(size=self.p.position_size)
            self.has_position = True
        elif self.has_position and self.exit_mixin.should_exit():
            self.sell(size=self.p.position_size)
            self.has_position = False

    def notify_trade(self, trade):
        """Record trade information"""
        if trade.isclosed:
            self.trades.append({
                'entry_date': trade.dtopen,
                'entry_price': trade.price,
                'exit_date': trade.dtclose,
                'exit_price': trade.price,  # Use actual exit price, not PnL
                'pnl': trade.pnl,
                'size': trade.size
            })
            self.has_position = False


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
