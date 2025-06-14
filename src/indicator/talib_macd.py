"""
TA-Lib MACD (Moving Average Convergence Divergence) Indicator

This module implements MACD using TA-Lib for optimized calculation.
MACD is a trend-following momentum indicator that shows the relationship between
two moving averages of a security's price.

Parameters:
    fast_period (int): Period for fast EMA calculation
    slow_period (int): Period for slow EMA calculation
    signal_period (int): Period for signal line calculation
"""

import backtrader as bt
import numpy as np
import talib

class TALibMACD(bt.Indicator):
    """MACD indicator using TA-Lib"""
    
    lines = ('macd', 'signal', 'histogram')
    params = (
        ('fast_period', 12),
        ('slow_period', 26),
        ('signal_period', 9),
    )
    
    def __init__(self):
        super(TALibMACD, self).__init__()
        
        # Initialize lines with 0
        self.lines.macd = bt.LineNum(0)
        self.lines.signal = bt.LineNum(0)
        self.lines.histogram = bt.LineNum(0)
        
        # Convert data to numpy array
        close_prices = np.array([self.data.close[i] for i in range(len(self.data))])
        
        # Calculate MACD using TA-Lib
        macd, signal, hist = talib.MACD(
            close_prices,
            fastperiod=self.p.fast_period,
            slowperiod=self.p.slow_period,
            signalperiod=self.p.signal_period
        )
        
        # Assign values to lines
        self.lines.macd.array = macd
        self.lines.signal.array = signal
        self.lines.histogram.array = hist 