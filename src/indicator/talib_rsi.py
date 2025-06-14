"""
TA-Lib RSI Indicator Wrapper

This module provides a Backtrader-compatible wrapper for TA-Lib's RSI indicator.
It allows using TA-Lib's optimized RSI calculation while maintaining Backtrader's
indicator interface for compatibility with other components.
"""

import backtrader as bt
import numpy as np
import talib


class TALibRSI(bt.Indicator):
    """
    TA-Lib RSI indicator wrapper for Backtrader.
    
    This indicator uses TA-Lib's RSI calculation for better performance while
    maintaining Backtrader's indicator interface.
    
    Parameters:
    -----------
    period : int
        The period for RSI calculation (default: 14)
    """
    
    lines = ('rsi',)
    params = (('period', 14),)
    
    def __init__(self):
        super(TALibRSI, self).__init__()
        self.lines.rsi = bt.LineNum()
        
        # Calculate RSI for all available data
        close_prices = np.array([self.data.close[i] for i in range(len(self.data))])
        self.rsi_values = talib.RSI(close_prices, timeperiod=self.p.period)
    
    def next(self):
        """Update the indicator value for the current bar"""
        self.lines.rsi[0] = self.rsi_values[len(self) - 1] 