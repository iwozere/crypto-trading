"""
MA Crossover Exit Mixin

This module implements an exit strategy based on Moving Average crossovers.
The strategy exits a position when:
1. Fast MA crosses below Slow MA for long positions
2. Fast MA crosses above Slow MA for short positions

Parameters:
    fast_period (int): Period for fast MA (default: 10)
    slow_period (int): Period for slow MA (default: 20)
    ma_type (str): Type of MA to use ('SMA', 'EMA', 'WMA', 'DEMA', 'TEMA', 'TRIMA', 'KAMA', 'MAMA', 'T3') (default: 'SMA')
    require_confirmation (bool): Whether to require confirmation of crossover (default: False)

This strategy is particularly effective for:
1. Trend following exit signals
2. Reducing false signals with confirmation
3. Adapting to different market conditions with different MA types
"""

from typing import Any, Dict

import backtrader as bt
import numpy as np
from src.exit.exit_mixin import BaseExitMixin


class MACrossoverExitMixin(BaseExitMixin):
    """Exit mixin based on Moving Average crossovers"""

    params = {
        "fast_period": 10,
        "slow_period": 20,
        "ma_type": "SMA",
        "require_confirmation": False,
    }

    def get_required_params(self) -> list:
        """There are no required parameters - all have default values"""
        return []

    def get_default_params(self) -> Dict[str, Any]:
        """Default parameters"""
        return {
            "fast_period": 10,
            "slow_period": 20,
            "ma_type": "SMA",
            "require_confirmation": False,
        }

    def _init_indicators(self):
        """Initialize Moving Average indicators"""
        if self.strategy is None:
            raise ValueError("Strategy must be set before initializing indicators")

        # Initialize indicators
        if self.strategy.p.use_talib:
            try:
                import talib
                # Convert data to numpy arrays
                close_data = np.array(self.strategy.data.close.get(size=len(self.strategy.data)))
                
                # Map MA type to TA-Lib function
                ma_type = self.get_param("ma_type").upper()
                ma_func = getattr(talib, ma_type)
                
                # Create Moving Averages using TA-Lib
                fast_ma_values = ma_func(
                    close_data,
                    timeperiod=self.get_param("fast_period")
                )
                slow_ma_values = ma_func(
                    close_data,
                    timeperiod=self.get_param("slow_period")
                )
                
                # Create Backtrader indicators and update their values
                self.indicators["fast_ma"] = bt.indicators.SMA(
                    self.strategy.data.close,
                    period=self.get_param("fast_period"),
                    plot=False
                )
                self.indicators["slow_ma"] = bt.indicators.SMA(
                    self.strategy.data.close,
                    period=self.get_param("slow_period"),
                    plot=False
                )
                
                # Update the arrays with TA-Lib values one by one
                for i in range(len(fast_ma_values)):
                    if i < len(self.indicators["fast_ma"].lines[0]):
                        self.indicators["fast_ma"].lines[0][i] = fast_ma_values[i]
                        self.indicators["slow_ma"].lines[0][i] = slow_ma_values[i]
                
            except ImportError:
                self.log("TA-Lib not available, falling back to Backtrader indicators")
                self._init_backtrader_indicators()
        else:
            self._init_backtrader_indicators()

    def _init_backtrader_indicators(self):
        """Initialize indicators using Backtrader's built-in implementations"""
        # Map MA type to Backtrader indicator
        ma_type = self.get_param("ma_type").upper()
        if ma_type == "SMA":
            ma_class = bt.indicators.SMA
        elif ma_type == "EMA":
            ma_class = bt.indicators.EMA
        elif ma_type == "WMA":
            ma_class = bt.indicators.WMA
        else:
            self.log(f"Unsupported MA type: {ma_type}, falling back to SMA")
            ma_class = bt.indicators.SMA

        # Create Moving Averages
        self.indicators["fast_ma"] = ma_class(
            self.strategy.data.close,
            period=self.get_param("fast_period")
        )
        self.indicators["slow_ma"] = ma_class(
            self.strategy.data.close,
            period=self.get_param("slow_period")
        )

    def should_exit(self) -> bool:
        """
        Exit logic: Fast MA crosses Slow MA
        """
        if not self.indicators:
            return False

        # Get current and previous values
        fast_ma = self.indicators["fast_ma"]
        slow_ma = self.indicators["slow_ma"]
        
        # Check for crossover
        if self.strategy.position.size > 0:  # Long position
            if self.get_param("require_confirmation"):
                return (
                    fast_ma[-1] > slow_ma[-1] and  # Previous bar: fast above slow
                    fast_ma[0] < slow_ma[0]        # Current bar: fast below slow
                )
            else:
                return fast_ma[0] < slow_ma[0]  # Fast MA below slow MA
        elif self.strategy.position.size < 0:  # Short position
            if self.get_param("require_confirmation"):
                return (
                    fast_ma[-1] < slow_ma[-1] and  # Previous bar: fast below slow
                    fast_ma[0] > slow_ma[0]        # Current bar: fast above slow
                )
            else:
                return fast_ma[0] > slow_ma[0]  # Fast MA above slow MA
        
        return False
