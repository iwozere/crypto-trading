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
use_talib : bool
    Whether to use TA-Lib for calculations (default: True)
"""

import backtrader as bt
import numpy as np
from src.exit.base_exit_mixin import BaseExitMixin
from typing import Dict, Any, Optional
from src.notification.logger import setup_logger
from src.indicator.talib_atr import TALibATR

logger = setup_logger()

class ATRExitMixin(BaseExitMixin):
    """Exit mixin based on ATR"""

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        """Initialize the mixin with parameters"""
        super().__init__(params)
        self.atr_name = 'exit_atr'

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

        try:
            data = self.strategy.data
            use_talib = self.strategy.use_talib

            if use_talib:
                setattr(self.strategy, self.atr_name, TALibATR(
                    data,
                    period=self.get_param("atr_period")
                ))
            else:
                setattr(self.strategy, self.atr_name, bt.indicators.ATR(
                    data,
                    period=self.get_param("atr_period")
                ))
        except Exception as e:
            logger.error(f"Error initializing indicators: {e}")
            raise

    def should_exit(self) -> bool:
        """Check if we should exit a position"""
        if not hasattr(self.strategy, self.atr_name):
            return False
        atr = getattr(self.strategy, self.atr_name)
        atr_val = atr[0] if hasattr(atr, '__getitem__') else atr.lines.atr[0]
        stop_loss = self.strategy.data.close[0] - (atr_val * self.get_param("atr_multiplier"))
        return self.strategy.data.close[0] < stop_loss
