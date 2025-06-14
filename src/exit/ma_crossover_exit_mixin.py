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
    use_talib (bool): Whether to use TA-Lib for calculations (default: True)

This strategy is particularly effective for:
1. Trend following exit signals
2. Reducing false signals with confirmation
3. Adapting to different market conditions with different MA types
"""

from typing import Any, Dict, Optional

import backtrader as bt
import numpy as np
from src.exit.base_exit_mixin import BaseExitMixin
from src.indicator.talib_sma import TALibSMA
from src.indicator.talib_ema import TALibEMA
from src.notification.logger import setup_logger

logger = setup_logger(__name__)

class MACrossoverExitMixin(BaseExitMixin):
    """Exit mixin based on Moving Average crossovers"""

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        """Initialize the mixin with parameters"""
        super().__init__(params)
        self.fast_ma_name = 'exit_fast_ma'
        self.slow_ma_name = 'exit_slow_ma'

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
            "use_talib": True,
        }

    def _init_indicators(self):
        """Initialize Moving Average indicators"""
        if not hasattr(self, 'strategy'):
            return

        try:
            data = self.strategy.data
            use_talib = self.strategy.use_talib

            if use_talib:
                if self.get_param("ma_type", "sma").lower() == "sma":
                    setattr(self.strategy, self.fast_ma_name, TALibSMA(data, period=self.get_param("fast_period")))
                    setattr(self.strategy, self.slow_ma_name, TALibSMA(data, period=self.get_param("slow_period")))
                elif self.get_param("ma_type", "sma").lower() == "ema":
                    setattr(self.strategy, self.fast_ma_name, TALibEMA(data, period=self.get_param("fast_period")))
                    setattr(self.strategy, self.slow_ma_name, TALibEMA(data, period=self.get_param("slow_period")))
                else:
                    raise ValueError(f"Unsupported MA type: {self.get_param('ma_type')}")
            else:
                if self.get_param("ma_type", "sma").lower() == "sma":
                    setattr(self.strategy, self.fast_ma_name, bt.indicators.SMA(data, period=self.get_param("fast_period")))
                    setattr(self.strategy, self.slow_ma_name, bt.indicators.SMA(data, period=self.get_param("slow_period")))
                elif self.get_param("ma_type", "sma").lower() == "ema":
                    setattr(self.strategy, self.fast_ma_name, bt.indicators.EMA(data, period=self.get_param("fast_period")))
                    setattr(self.strategy, self.slow_ma_name, bt.indicators.EMA(data, period=self.get_param("slow_period")))
                else:
                    raise ValueError(f"Unsupported MA type: {self.get_param('ma_type')}")

        except Exception as e:
            logger.error(f"Error initializing indicators: {str(e)}")
            raise

    def should_exit(self) -> bool:
        """Check if we should exit a position"""
        if not self.strategy.position:
            return False

        if not all(hasattr(self.strategy, name) for name in [self.fast_ma_name, self.slow_ma_name]):
            return False

        fast_ma = getattr(self.strategy, self.fast_ma_name)
        slow_ma = getattr(self.strategy, self.slow_ma_name)

        # Get current and previous values
        fast_ma_current = fast_ma[0]
        slow_ma_current = slow_ma[0]
        fast_ma_prev = fast_ma[-1]
        slow_ma_prev = slow_ma[-1]

        # Check for crossover based on position
        if self.strategy.position.size > 0:  # Long position
            return_value = fast_ma_prev > slow_ma_prev and fast_ma_current < slow_ma_current
        else:  # Short position
            return_value = fast_ma_prev < slow_ma_prev and fast_ma_current > slow_ma_current

        if return_value:
            logger.info(f"EXIT: Price: {self.strategy.data.close[0]}, "
                       f"Fast MA: {fast_ma_current}, Slow MA: {slow_ma_current}, "
                       f"Position: {'long' if self.strategy.position.size > 0 else 'short'}")
        return return_value

    def get_exit_reason(self) -> str:
        """Get the reason for exiting the position"""
        if not self.strategy.position:
            return "unknown"
            
        if not all(hasattr(self.strategy, name) for name in [self.fast_ma_name, self.slow_ma_name]):
            return "unknown"
            
        ma_type = self.get_param("ma_type", "sma").lower()
        return f"{ma_type}_crossover"
