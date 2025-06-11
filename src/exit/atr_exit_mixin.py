"""
ATR-based Exit Mixin

This module implements an exit strategy based on the Average True Range (ATR) indicator.
The strategy exits a position when:
1. Price reaches the take profit level (entry price + ATR * tp_multiplier)
2. Price reaches the stop loss level (entry price - ATR * sl_multiplier)

Parameters:
    atr_period (int): Period for ATR calculation (default: 14)
    tp_multiplier (float): Multiplier for take profit level (default: 2.0)
    sl_multiplier (float): Multiplier for stop loss level (default: 1.0)
    use_dynamic_tp (bool): Whether to adjust TP based on ATR changes (default: False)
    use_dynamic_sl (bool): Whether to adjust SL based on ATR changes (default: False)
    use_talib (bool): Whether to use TA-Lib for indicator calculations (default: False)

This strategy uses ATR to dynamically adjust take profit and stop loss levels based on market
volatility. It's particularly effective in volatile markets where fixed percentage stops might
be too tight or too wide.
"""

from typing import Any, Dict

import backtrader as bt
from src.exit.exit_mixin import BaseExitMixin


class ATRExitMixin(BaseExitMixin):
    """
    Exit mixin based on ATR (Average True Range).

    Parameters:
    -----------
    atr_period : int
        Period for ATR calculation (default: 14)
    atr_multiplier : float
        Multiplier for ATR to determine stop loss (default: 2.0)
    use_talib : bool
        Whether to use TA-Lib for indicator calculations (default: False)
    """

    # Define default values as class constants
    DEFAULT_ATR_PERIOD = 14
    DEFAULT_ATR_MULTIPLIER = 2.0
    DEFAULT_STOP_LOSS_RATIO = 0.02
    
    def __init__(self, params: Dict[str, Any]):
        super().__init__(params)
        self.atr_period = params.get("atr_period", self.DEFAULT_ATR_PERIOD)
        self.atr_multiplier = params.get("atr_multiplier", self.DEFAULT_ATR_MULTIPLIER)
        self.stop_loss_ratio = params.get("stop_loss_ratio", self.DEFAULT_STOP_LOSS_RATIO)
        self.use_talib = params.get("use_talib", False)

    def get_required_params(self) -> list:
        """There are no required parameters - all have default values"""
        return []

    def get_default_params(self) -> Dict[str, Any]:
        """Default parameters"""
        return {
            "atr_period": self.DEFAULT_ATR_PERIOD,
            "atr_multiplier": self.DEFAULT_ATR_MULTIPLIER, 
            "stop_loss_ratio": self.DEFAULT_STOP_LOSS_RATIO,
            # Add other default parameters as needed
        }

    def _init_indicators(self):
        """Initialize indicators"""
        if self.use_talib:
            import talib

            # Create ATR indicator using TA-Lib
            self.atr = bt.indicators.TALibIndicator(
                self.strategy.data, talib.ATR, period=self.atr_period
            )
        else:
            # Create ATR indicator using Backtrader
            self.atr = bt.indicators.ATR(self.strategy.data, period=self.atr_period)

    def should_exit(self) -> bool:
        """
        Check if we should exit based on ATR-based stop loss.

        Returns:
        --------
        bool
            True if we should exit, False otherwise
        """
        # Calculate stop loss level
        stop_loss = self.strategy.data.close[0] - (self.atr[0] * self.atr_multiplier)

        # Exit if price falls below stop loss
        return self.strategy.data.close[0] < stop_loss
