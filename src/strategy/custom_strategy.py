# custom_strategy.py - Improved version with a new approach

from typing import Any, Dict

import backtrader as bt
from src.entry.entry_mixin_factory import (get_entry_mixin,
                                           get_entry_mixin_from_config)
from src.exit.exit_mixin_factory import (get_exit_mixin,
                                         get_exit_mixin_from_config)


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
        ("position_size", 0.1),     # Default position size
        ("use_talib", False),       # Whether to use TA-Lib
    )

    def __init__(self):
        super().__init__()

        strategy_config = self.p.strategy_config

        self.entry_logic = strategy_config["entry_logic"]
        self.exit_logic = strategy_config["exit_logic"]
        self.trades = []  # List to store trade information
        self.has_position = False  # Flag to track if we have an open position

        # Update params from config if provided
        if "position_size" in strategy_config:
            self.p.position_size = strategy_config["position_size"]
        if "use_talib" in strategy_config:
            self.p.use_talib = strategy_config["use_talib"]

        # Validate required parameters
        if not strategy_config:
            raise ValueError("strategy_config parameter is required")

        # Initialize common indicators
        self._init_common_indicators()

        # Initialize mixins
        self._init_entry_mixin()
        self._init_exit_mixin()

    def _init_common_indicators(self):
        """Initialize common indicators used by multiple mixins"""
        if self.p.use_talib:
            import talib

            # Create RSI indicator using TA-Lib
            self.rsi = bt.indicators.TALibIndicator(
                self.data.close,
                talib.RSI,
                period=self.entry_logic["params"].get("rsi_period", 14),
            )

            # Create Bollinger Bands indicator using TA-Lib
            self.bb = bt.indicators.TALibIndicator(
                self.data.close,
                talib.BBANDS,
                period=self.entry_logic["params"].get("bb_period", 20),
            )

            # Create ATR indicator using TA-Lib
            self.atr = bt.indicators.TALibIndicator(
                self.data,
                talib.ATR,
                period=self.exit_logic["params"].get("atr_period", 14),
            )
        else:
            # Create RSI indicator using Backtrader
            self.rsi = bt.indicators.RSI(
                self.data.close, period=self.entry_logic["params"].get("rsi_period", 14)
            )

            # Create Bollinger Bands indicator using Backtrader
            self.bb = bt.indicators.BollingerBands(
                self.data.close, period=self.entry_logic["params"].get("bb_period", 20)
            )

            # Create ATR indicator using Backtrader
            self.atr = bt.indicators.ATR(
                self.data, period=self.exit_logic["params"].get("atr_period", 14)
            )

    def _init_entry_mixin(self):
        """Initialize entry mixin with configuration"""

        # Variant 1: Configuration contains name and parameters separately
        if isinstance(self.entry_logic, dict) and "name" in self.entry_logic:
            entry_name = self.entry_logic["name"]
            entry_params = self.entry_logic.get("params", {})
            entry_params["use_talib"] = self.p.use_talib
            self.entry_mixin = get_entry_mixin(entry_name, entry_params)

        # Variant 2: Full configuration (preferred)
        elif isinstance(self.entry_logic, dict):
            self.entry_logic["params"]["use_talib"] = self.p.use_talib
            self.entry_mixin = get_entry_mixin_from_config(self.entry_logic)

        else:
            raise ValueError(f"Invalid entry_logic format: {self.entry_logic}")

        # Initialize the mixin with the strategy
        self.entry_mixin.init_entry(strategy=self)

    def _init_exit_mixin(self):
        """Initialize exit mixin with configuration"""

        if isinstance(self.exit_logic, dict) and "name" in self.exit_logic:
            exit_name = self.exit_logic["name"]
            exit_params = self.exit_logic.get("params", {})
            exit_params["use_talib"] = self.p.use_talib
            self.exit_mixin = get_exit_mixin(exit_name, exit_params)

        elif isinstance(self.exit_logic, dict):
            self.exit_logic["params"]["use_talib"] = self.p.use_talib
            self.exit_mixin = get_exit_mixin_from_config(self.exit_logic)

        else:
            raise ValueError(f"Invalid exit_logic format: {self.exit_logic}")

        self.exit_mixin.init_exit(strategy=self)

    def notify_trade(self, trade):
        """Called when a trade is completed"""
        if trade.isclosed:
            self.has_position = False  # Reset position flag when trade is closed
            self.trades.append({
                'entry_date': self.data.datetime.datetime(),
                'exit_date': self.data.datetime.datetime(),
                'entry_price': trade.price,
                'exit_price': trade.pnl,
                'pnl': trade.pnl,
                'pnlcomm': trade.pnlcomm,
                'size': trade.size,
                'status': 'closed'
            })

    def next(self):
        """Main strategy logic"""
        # Check entry conditions (if no open positions)
        if not self.has_position:
            if self.entry_mixin.should_enter():
                size = self._calculate_position_size()
                self.buy(size=size)
                self.has_position = True  # Set position flag when entering
                self.trades.append({
                    'entry_date': self.data.datetime.datetime(),
                    'entry_price': self.data.close[0],
                    'size': size,
                    'status': 'open'
                })
                print(
                    f"BUY signal at {self.data.datetime.datetime()} - Price: {self.data.close[0]:.2f}"
                )

        # Check exit conditions (if there are open positions)
        elif self.has_position:
            if self.exit_mixin.should_exit():
                self.sell(size=self.position.size)
                print(
                    f"SELL signal at {self.data.datetime.datetime()} - Price: {self.data.close[0]:.2f}"
                )

    def _calculate_position_size(self) -> float:
        """
        Calculate position size based on available capital and position_size parameter

        Returns:
        --------
        float
            Number of shares to buy
        """
        available_cash = self.broker.get_cash()
        price = self.data.close[0]
        max_shares = int((available_cash * self.p.position_size) / price)
        return max_shares


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
