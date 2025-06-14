"""
TA-Lib ATR (Average True Range) Indicator Wrapper for Backtrader

This module provides a wrapper for TA-Lib's ATR calculation that integrates
seamlessly with Backtrader's indicator framework. It uses TA-Lib's optimized
ATR calculation while maintaining compatibility with Backtrader's line interface.
"""

import backtrader as bt
import numpy as np
import talib

class TALibATR(bt.Indicator):
    """
    TA-Lib ATR (Average True Range) Indicator Wrapper
    
    This indicator calculates the Average True Range using TA-Lib's optimized
    implementation while maintaining compatibility with Backtrader's line interface.
    
    Parameters:
        period (int): Period for ATR calculation (default: 14)
    """
    
    lines = ('atr',)  # Single line for ATR values
    params = (('period', 14),)  # Default period is 14
    
    def __init__(self):
        super(TALibATR, self).__init__()
        
        # Convert data to numpy arrays
        high_data = np.array(self.data.high.get(size=len(self.data)))
        low_data = np.array(self.data.low.get(size=len(self.data)))
        close_data = np.array(self.data.close.get(size=len(self.data)))
        
        # Calculate ATR using TA-Lib
        atr_values = talib.ATR(
            high_data,
            low_data,
            close_data,
            timeperiod=self.p.period
        )
        
        # Update the indicator's line with calculated values
        for i, value in enumerate(atr_values):
            if i < len(self.lines[0]):
                self.lines[0][i] = value
    
    def next(self):
        """
        This method is called for each new bar and is required by Backtrader.
        Since we pre-calculate all values in __init__, this method is empty.
        """
        pass 