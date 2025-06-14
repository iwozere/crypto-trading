"""
TA-Lib Simple Moving Average (SMA) Indicator

This module implements Simple Moving Average using TA-Lib for optimized calculation.
SMA is calculated by taking the arithmetic mean of a set of values over a specified period.

Parameters:
    period (int): Period for moving average calculation
"""

import backtrader as bt
import numpy as np
import talib

class TALibSMA(bt.Indicator):
    """Simple Moving Average indicator using TA-Lib"""
    
    lines = ('sma',)
    params = (
        ('period', 20),
    )
    
    def __init__(self):
        super(TALibSMA, self).__init__()
        
        # Initialize line with 0
        self.lines.sma = bt.LineNum(0)
        
        # Convert data to numpy array
        data_array = np.array([self.data[i] for i in range(len(self.data))])
        
        # Calculate SMA using TA-Lib
        sma = talib.SMA(
            data_array,
            timeperiod=self.p.period
        )
        
        # Assign values to line
        self.lines.sma.array = sma
    
    def next(self):
        """
        This method is called for each new bar and is required by Backtrader.
        Since we pre-calculate all values in __init__, this method is empty.
        """
        pass 