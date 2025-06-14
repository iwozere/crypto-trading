"""
TA-Lib Bollinger Bands Indicator Wrapper

This module provides a Backtrader-compatible wrapper for TA-Lib's Bollinger Bands indicator.
It allows using TA-Lib's optimized BB calculation while maintaining Backtrader's
indicator interface for compatibility with other components.
"""

import backtrader as bt
import numpy as np
import talib


class TALibBB(bt.Indicator):
    """
    TA-Lib Bollinger Bands indicator wrapper for Backtrader.
    
    This indicator uses TA-Lib's BB calculation for better performance while
    maintaining Backtrader's indicator interface.
    
    Parameters:
    -----------
    period : int
        The period for moving average calculation (default: 20)
    devfactor : float
        The number of standard deviations for the bands (default: 2.0)
    """
    
    lines = ('bb_upper', 'bb_middle', 'bb_lower',)
    params = (
        ('period', 20),
        ('devfactor', 2.0),
    )
    
    def __init__(self):
        super(TALibBB, self).__init__()
        self.lines.bb_upper = bt.LineNum()
        self.lines.bb_middle = bt.LineNum()
        self.lines.bb_lower = bt.LineNum()
        
        # Calculate BB for all available data
        close_prices = np.array([self.data.close[i] for i in range(len(self.data))])
        self.bb_upper, self.bb_middle, self.bb_lower = talib.BBANDS(
            close_prices,
            timeperiod=self.p.period,
            nbdevup=self.p.devfactor,
            nbdevdn=self.p.devfactor,
            matype=0  # Simple Moving Average
        )
    
    def next(self):
        """Update the indicator values for the current bar"""
        self.lines.bb_upper[0] = self.bb_upper[len(self) - 1]
        self.lines.bb_middle[0] = self.bb_middle[len(self) - 1]
        self.lines.bb_lower[0] = self.bb_lower[len(self) - 1] 