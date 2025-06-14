"""
TA-Lib Bollinger Bands Indicator

This module implements Bollinger Bands using TA-Lib for optimized calculation.
Bollinger Bands consist of:
- Middle Band: N-period simple moving average (SMA)
- Upper Band: Middle Band + (K * N-period standard deviation)
- Lower Band: Middle Band - (K * N-period standard deviation)

Parameters:
    period (int): Period for moving average and standard deviation calculation
    devfactor (float): Number of standard deviations for the bands
"""

import backtrader as bt
import numpy as np
import talib

class TALibBB(bt.Indicator):
    """Bollinger Bands indicator using TA-Lib"""
    
    lines = ('bb_upper', 'bb_middle', 'bb_lower')
    params = (
        ('period', 20),
        ('devfactor', 2.0),
    )
    
    def __init__(self):
        super(TALibBB, self).__init__()
        
        # Initialize lines with 0
        self.lines.bb_upper = bt.LineNum(0)
        self.lines.bb_middle = bt.LineNum(0)
        self.lines.bb_lower = bt.LineNum(0)
        
        # Convert data to numpy array
        close_prices = np.array([self.data.close[i] for i in range(len(self.data))])
        
        # Calculate Bollinger Bands using TA-Lib
        upper, middle, lower = talib.BBANDS(
            close_prices,
            timeperiod=self.p.period,
            nbdevup=self.p.devfactor,
            nbdevdn=self.p.devfactor,
            matype=0  # Simple Moving Average
        )
        
        # Assign values to lines
        self.lines.bb_upper.array = upper
        self.lines.bb_middle.array = middle
        self.lines.bb_lower.array = lower

    def next(self):
        """Update the indicator values for the current bar"""
        self.lines.bb_upper[0] = self.lines.bb_upper.array[len(self) - 1]
        self.lines.bb_middle[0] = self.lines.bb_middle.array[len(self) - 1]
        self.lines.bb_lower[0] = self.lines.bb_lower.array[len(self) - 1] 