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

from typing import Any, Dict, Optional

import backtrader as bt
import numpy as np
from src.exit.base_exit_mixin import BaseExitMixin


class MACrossoverExitMixin(BaseExitMixin):
    """Exit mixin based on Moving Average crossovers"""

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        """Initialize the mixin with parameters"""
        super().__init__(params)

    def get_required_params(self) -> list:
        """There are no required parameters - all have default values"""
        return []

    @classmethod
    def get_default_params(cls) -> Dict[str, Any]:
        """Default parameters"""
        return {
            "fast_period": 10,
            "slow_period": 20,
            "ma_type": "sma",
            "require_confirmation": False,
        }

    def _init_indicators(self):
        """Initialize Moving Average indicators"""
        if not hasattr(self, 'strategy'):
            return

        ma_type = self.get_param("ma_type", "sma")
        if ma_type == "sma":
            self.indicators["fast_ma"] = bt.indicators.SMA(self.strategy.data, period=self.get_param("fast_period"))
            self.indicators["slow_ma"] = bt.indicators.SMA(self.strategy.data, period=self.get_param("slow_period"))
        elif ma_type == "ema":
            self.indicators["fast_ma"] = bt.indicators.EMA(self.strategy.data, period=self.get_param("fast_period"))
            self.indicators["slow_ma"] = bt.indicators.EMA(self.strategy.data, period=self.get_param("slow_period"))
        else:
            raise ValueError(f"Unsupported MA type: {ma_type}")

    def should_exit(self) -> bool:
        """Check if we should exit a position"""
        if not self.strategy.position:
            return False
        fast_ma = self.indicators["fast_ma"][0]
        slow_ma = self.indicators["slow_ma"][0]
        prev_fast_ma = self.indicators["fast_ma"][-1]
        prev_slow_ma = self.indicators["slow_ma"][-1]
        if self.strategy.position.size > 0:
            return prev_fast_ma > prev_slow_ma and fast_ma < slow_ma
        else:
            return prev_fast_ma < prev_slow_ma and fast_ma > slow_ma
