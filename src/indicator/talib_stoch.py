"""
TA-Lib Stochastic Oscillator Indicator

This module implements Stochastic Oscillator using TA-Lib for optimized calculation.
The Stochastic Oscillator is a momentum indicator comparing a particular closing price
of a security to a range of its prices over a certain period of time.

Parameters:
    fastk_period (int): Period for %K calculation
    slowk_period (int): Period for smoothing %K
    slowd_period (int): Period for smoothing %D
"""

import backtrader as bt
import numpy as np
import talib

class TALibStoch(bt.Indicator):
    """Stochastic Oscillator indicator using TA-Lib"""
    
    lines = ('slowk', 'slowd')
    params = (
        ('fastk_period', 5),
        ('slowk_period', 3),
        ('slowd_period', 3),
    )
    
    def __init__(self):
        super(TALibStoch, self).__init__()
        
        # Initialize lines with 0
        self.lines.slowk = bt.LineNum(0)
        self.lines.slowd = bt.LineNum(0)
        
        # Convert data to numpy arrays
        high_data = np.array([self.data.high[i] for i in range(len(self.data))])
        low_data = np.array([self.data.low[i] for i in range(len(self.data))])
        close_data = np.array([self.data.close[i] for i in range(len(self.data))])
        
        # Calculate Stochastic using TA-Lib
        slowk, slowd = talib.STOCH(
            high_data,
            low_data,
            close_data,
            fastk_period=self.p.fastk_period,
            slowk_period=self.p.slowk_period,
            slowk_matype=0,  # Simple Moving Average
            slowd_period=self.p.slowd_period,
            slowd_matype=0   # Simple Moving Average
        )
        
        # Assign values to lines
        self.lines.slowk.array = slowk
        self.lines.slowd.array = slowd 