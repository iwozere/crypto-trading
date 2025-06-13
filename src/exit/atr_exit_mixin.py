"""
ATR Exit Mixin
-------------

This module implements an exit strategy based on Average True Range (ATR).
The strategy exits a position when the price moves against the position by more than ATR multiplied by a specified multiplier.

Parameters:
-----------
atr_period : int
    Period for ATR calculation (default: 14)
atr_multiplier : float
    Multiplier for ATR to determine exit threshold (default: 2.0)
"""

import backtrader as bt
import numpy as np
from src.exit.base_exit_mixin import BaseExitMixin
from typing import Dict, Any


class ATRExitMixin(BaseExitMixin):
    """Exit mixin based on ATR"""

    def __init__(self, params=None):
        """Initialize the mixin with parameters"""
        super().__init__()
        self.params = params or self.get_default_params()

    def get_required_params(self) -> list:
        """There are no required parameters - all have default values"""
        return []

    @classmethod
    def get_default_params(cls) -> Dict[str, Any]:
        """Default parameters"""
        return {
            "atr_period": 14,
            "atr_multiplier": 2.0,
        }

    def _init_indicators(self):
        """Initialize ATR indicator"""
        if not hasattr(self, 'strategy'):
            return
            
        # Initialize ATR
        use_talib = getattr(self.strategy, 'use_talib', False)
        if use_talib:
            try:
                import talib
                # Calculate ATR using TA-Lib
                high_prices = np.array([self.strategy.data.high[i] for i in range(len(self.strategy.data))])
                low_prices = np.array([self.strategy.data.low[i] for i in range(len(self.strategy.data))])
                close_prices = np.array([self.strategy.data.close[i] for i in range(len(self.strategy.data))])
                
                atr_values = talib.ATR(high_prices, low_prices, close_prices, timeperiod=self.params["atr_period"])
                
                # Initialize Backtrader ATR
                self.strategy.atr = bt.indicators.ATR(
                    self.strategy.data,
                    period=self.params["atr_period"]
                )
                
                # Update ATR values one by one
                for i in range(len(self.strategy.data)):
                    if i < len(atr_values):
                        self.strategy.atr.array[i] = atr_values[i]
            except ImportError:
                self.strategy.logger.warning("TA-Lib not available, using Backtrader's ATR")
                self.strategy.atr = bt.indicators.ATR(
                    self.strategy.data,
                    period=self.params["atr_period"]
                )
        else:
            self.strategy.atr = bt.indicators.ATR(
                self.strategy.data,
                period=self.params["atr_period"]
            )

    def should_exit(self) -> bool:
        """Check if we should exit a position"""
        if not hasattr(self.strategy, 'atr'):
            return False

        # Get current ATR value
        atr = self.strategy.atr[0]
        
        # Calculate stop loss level
        stop_loss = self.strategy.data.close[0] - (atr * self.params["atr_multiplier"])
        
        # Check if price has fallen below stop loss
        return self.strategy.data.close[0] < stop_loss
