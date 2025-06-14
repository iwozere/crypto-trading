"""
TA-Lib SMA (Simple Moving Average) Indicator Wrapper for Backtrader

This module provides a wrapper for TA-Lib's SMA calculation that integrates
seamlessly with Backtrader's indicator framework. It uses TA-Lib's optimized
SMA calculation while maintaining compatibility with Backtrader's line interface.
"""

import backtrader as bt
import numpy as np
import talib

class TALibSMA(bt.Indicator):
    """
    TA-Lib SMA (Simple Moving Average) Indicator Wrapper
    
    This indicator calculates the Simple Moving Average using TA-Lib's optimized
    implementation while maintaining compatibility with Backtrader's line interface.
    
    Parameters:
        period (int): Period for SMA calculation (default: 20)
        data (bt.Data): The data source to calculate SMA on (default: None)
    """
    
    lines = ('sma',)  # Single line for SMA values
    params = (('period', 20),)  # Default period is 20
    
    def __init__(self, data=None):
        super(TALibSMA, self).__init__()
        
        # Convert data to numpy array
        data_array = np.array(self.data.get(size=len(self.data)))
        
        # Calculate SMA using TA-Lib
        sma_values = talib.SMA(
            data_array,
            timeperiod=self.p.period
        )
        
        # Update the indicator's line with calculated values
        for i, value in enumerate(sma_values):
            if i < len(self.lines[0]):
                self.lines[0][i] = value
    
    def next(self):
        """
        This method is called for each new bar and is required by Backtrader.
        Since we pre-calculate all values in __init__, this method is empty.
        """
        pass 