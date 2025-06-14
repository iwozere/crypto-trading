"""
TA-Lib Average True Range (ATR) Indicator

This module implements Average True Range using TA-Lib for optimized calculation.
ATR measures market volatility by decomposing the entire range of an asset price for a period.

Parameters:
    period (int): Period for ATR calculation
"""

import backtrader as bt
import numpy as np
import talib

class TALibATR(bt.Indicator):
    """Average True Range indicator using TA-Lib"""
    
    lines = ('atr',)
    params = (
        ('period', 14),
    )
    
    def __init__(self):
        super(TALibATR, self).__init__()
        
        # Initialize line with 0
        self.lines.atr = bt.LineNum(0)
        
        # Convert data to numpy arrays
        high_data = np.array([self.data.high[i] for i in range(len(self.data))])
        low_data = np.array([self.data.low[i] for i in range(len(self.data))])
        close_data = np.array([self.data.close[i] for i in range(len(self.data))])
        
        # Calculate ATR using TA-Lib
        atr = talib.ATR(
            high_data,
            low_data,
            close_data,
            timeperiod=self.p.period
        )
        
        # Assign values to line
        self.lines.atr.array = atr
    
    def next(self):
        """
        This method is called for each new bar and is required by Backtrader.
        Since we pre-calculate all values in __init__, this method is empty.
        """
        pass 