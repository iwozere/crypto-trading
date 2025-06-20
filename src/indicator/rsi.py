"""
TA-Lib RSI Indicator Wrapper

This module provides a Backtrader-compatible wrapper for TA-Lib's RSI indicator.
It allows using TA-Lib's optimized RSI calculation while maintaining Backtrader's
indicator interface for compatibility with other components.
"""

import backtrader as bt
import pandas as pd
import pandas_ta as ta
from src.notification.logger import setup_logger

logger = setup_logger(__name__)


class RSI(bt.Indicator):
    """
    TA-Lib RSI indicator wrapper for Backtrader.

    This indicator uses TA-Lib's RSI calculation for better performance while
    maintaining Backtrader's indicator interface.

    Parameters:
    -----------
    period : int
        The period for RSI calculation (default: 14)
    indicator_type : str
        The type of indicator to use (default: 'bt', values: 'bt', 'bt-talib', 'pandas-ta' or 'talib')
    """

    lines = ("rsi",)
    params = (
        ("period", 14),
        ("indicator_type", "bt"),
    )

    def __init__(self):
        super(RSI, self).__init__()
        self.lines.rsi = bt.LineNum(0)  # Initialize with 0
        self.addminperiod(self.p.period)  # Ensure we have enough data

        try:
            if self.p.indicator_type == "bt":
                self.rsi = bt.indicators.RSI(self.data.close, period=self.p.period)
            elif self.p.indicator_type == "bt-talib":
                self.rsi = bt.talib.RSI(self.data.close, timeperiod=self.p.period)
            elif self.p.indicator_type == "pandas-ta":
                # For pandas-ta, we'll calculate in next()
                raise ValueError("pandas-ta indicator type is not supported for RSI")
            elif self.p.indicator_type == "talib":
                import talib

                self.rsi = talib.RSI(self.data.close, timeperiod=self.p.period)
        except Exception as e:
            logger.error(
                f"Error initializing RSI indicator: {e}. Falling back to bt.indicators.RSI",
                exc_info=e,
            )
            self.rsi = bt.indicators.RSI(self.data.close, period=self.p.period)

    def next(self):
        """Update the indicator values for the current bar"""
        if self.p.indicator_type in ["bt", "bt-talib"]:
            self.lines.rsi[0] = self.rsi[0]
        elif self.p.indicator_type == "talib":
            self.lines.rsi[0] = self.rsi[len(self.data) - 1]
