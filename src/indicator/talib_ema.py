"""
TA-Lib SMA (Simple Moving Average) Indicator Wrapper for Backtrader

This module provides a wrapper for TA-Lib's SMA calculation that integrates
seamlessly with Backtrader's indicator framework. It uses TA-Lib's optimized
SMA calculation while maintaining compatibility with Backtrader's line interface.
"""

import backtrader as bt
import numpy as np
import talib

class TALibEMA(bt.Indicator):
    """
    TA-Lib EMA (Exponential Moving Average) Indicator Wrapper
    
    This indicator calculates the Exponential Moving Average using TA-Lib's optimized
    implementation while maintaining compatibility with Backtrader's line interface.
    
    Parameters:
        period (int): Period for EMA calculation (default: 20)
        data (bt.Data): The data source to calculate EMA on (default: None)
    """
    
    lines = ('ema',)  # Single line for SMA values
    params = (('period', 20),)  # Default period is 20
        
    def __init__(self, data=None):
        super(TALibEMA, self).__init__()
        
        # Convert data to numpy array
        data_array = np.array(self.data.get(size=len(self.data)))
        
        # Calculate EMA using TA-Lib
        ema_values = talib.EMA(
            data_array,
            timeperiod=self.p.period
        )
        
        # Update the indicator's line with calculated values
        for i, value in enumerate(ema_values):
            if i < len(self.lines[0]):
                self.lines[0][i] = value
    
    def next(self):
        """
        This method is called for each new bar and is required by Backtrader.
        Since we pre-calculate all values in __init__, this method is empty.
        """
        pass 