"""
TA-Lib Exponential Moving Average (EMA) Indicator

This module implements Exponential Moving Average using TA-Lib for optimized calculation.
EMA gives more weight to recent prices, making it more responsive to price changes than SMA.

Parameters:
    period (int): Period for moving average calculation
"""

import backtrader as bt
import numpy as np
import talib

class TALibEMA(bt.Indicator):
    """Exponential Moving Average indicator using TA-Lib"""
    
    lines = ('ema',)
    params = (
        ('period', 20),
    )
    
    def __init__(self):
        super(TALibEMA, self).__init__()
        
        # Initialize line with 0
        self.lines.ema = bt.LineNum(0)
        
        # Convert data to numpy array
        data_array = np.array([self.data[i] for i in range(len(self.data))])
        
        # Calculate EMA using TA-Lib
        ema = talib.EMA(
            data_array,
            timeperiod=self.p.period
        )
        
        # Assign values to line
        self.lines.ema.array = ema

    def next(self):
        """
        This method is called for each new bar and is required by Backtrader.
        Since we pre-calculate all values in __init__, this method is empty.
        """
        pass 