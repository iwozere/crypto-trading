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
from src.exit.exit_mixin import BaseExitMixin


class ATRExitMixin(BaseExitMixin):
    """Exit mixin based on Average True Range (ATR)"""

    params = {
        "atr_period": 14,
        "atr_multiplier": 2.0,
    }

    def get_required_params(self) -> list:
        """There are no required parameters - all have default values"""
        return []

    def get_default_params(self) -> dict:
        """Default parameters"""
        return {
            "atr_period": 14,
            "atr_multiplier": 2.0,
        }

    def _init_indicators(self):
        """Initialize ATR indicator"""
        if self.strategy is None:
            raise ValueError("Strategy must be set before initializing indicators")

        # Initialize ATR
        if self.strategy.p.use_talib:
            try:
                import talib
                # Convert data to numpy arrays
                high_data = np.array(self.strategy.data.high.get(size=len(self.strategy.data)))
                low_data = np.array(self.strategy.data.low.get(size=len(self.strategy.data)))
                close_data = np.array(self.strategy.data.close.get(size=len(self.strategy.data)))
                
                # Create ATR using TA-Lib
                atr_values = talib.ATR(
                    high_data,
                    low_data,
                    close_data,
                    timeperiod=self.get_param("atr_period")
                )
                self.indicators["atr"] = bt.indicators.ATR(
                    self.strategy.data,
                    period=self.get_param("atr_period"),
                    plot=False
                )
                # Update ATR values one by one
                for i, value in enumerate(atr_values):
                    if i < len(self.indicators["atr"].lines[0]):
                        self.indicators["atr"].lines[0][i] = value
            except ImportError:
                self.log("TA-Lib not available, falling back to Backtrader ATR")
                self.indicators["atr"] = bt.indicators.ATR(
                    self.strategy.data,
                    period=self.get_param("atr_period")
                )
        else:
            self.indicators["atr"] = bt.indicators.ATR(
                self.strategy.data,
                period=self.get_param("atr_period")
            )

    def should_exit(self):
        """Check if we should exit the position"""
        if not self.indicators:
            return False

        # Get current ATR value
        atr = self.indicators["atr"][0]
        current_price = self.strategy.data.close[0]
        
        # Calculate stop loss based on position type
        if self.strategy.position.size > 0:  # Long position
            stop_loss = current_price - (atr * self.get_param("atr_multiplier"))
            return current_price < stop_loss
        elif self.strategy.position.size < 0:  # Short position
            stop_loss = current_price + (atr * self.get_param("atr_multiplier"))
            return current_price > stop_loss
        
        return False
