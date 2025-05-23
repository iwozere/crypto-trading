"""
Super Trend Indicator Module
---------------------------

This module implements the Super Trend technical indicator for use in trading strategies. The Super Trend indicator is used to identify the prevailing market trend and generate buy/sell signals based on price and volatility.

Main Features:
- Calculate Super Trend values for a given price series
- Generate trend direction and signal outputs
- Suitable for integration with trading and backtesting frameworks

Functions/Classes:
- super_trend: Main function to compute the Super Trend indicator
"""

import backtrader as bt
import numpy as np
import math

# Custom SuperTrend Indicator
class SuperTrend(bt.Indicator):
    lines = ('supertrend', 'direction',) # supertrend line and direction (-1 for short, 1 for long)
    params = (('period', 10), ('multiplier', 3.0),)

    def __init__(self):
        self.addminperiod(self.p.period + 1)
        self.atr = bt.indicators.ATR(self.datas[0], period=self.p.period)
        self.final_ub_list = []
        self.final_lb_list = []

    def next(self):
        hl2 = (self.datas[0].high[0] + self.datas[0].low[0]) / 2
        atr = self.atr[0]
        basic_ub = hl2 + self.p.multiplier * atr
        basic_lb = hl2 - self.p.multiplier * atr

        # Calculate final upper/lower bands
        if len(self.final_ub_list) == 0:
            prev_final_ub = basic_ub
        else:
            prev_final_ub = self.final_ub_list[-1]
        if len(self.final_lb_list) == 0:
            prev_final_lb = basic_lb
        else:
            prev_final_lb = self.final_lb_list[-1]
        prev_close = self.datas[0].close[-1] if len(self) > 1 else self.datas[0].close[0]
        final_ub = basic_ub if (basic_ub < prev_final_ub or prev_close > prev_final_ub) else prev_final_ub
        final_lb = basic_lb if (basic_lb > prev_final_lb or prev_close < prev_final_lb) else prev_final_lb

        self.final_ub_list.append(final_ub)
        self.final_lb_list.append(final_lb)

        # Set initial direction if it's undefined (first proper calculation)
        if len(self) == 1 or math.isnan(self.lines.direction[-1]) or self.lines.direction[-1] == 0:
            if self.datas[0].close[0] > final_ub:
                self.lines.direction[0] = 1
            elif self.datas[0].close[0] < final_lb:
                self.lines.direction[0] = -1
            else:
                self.lines.direction[0] = 0 # Still undefined
                self.lines.supertrend[0] = np.nan
                return
        else:
            # Determine current direction
            if self.lines.direction[-1] == 1: # Previous trend was up
                if self.datas[0].close[0] < final_lb:
                    self.lines.direction[0] = -1
                else:
                    self.lines.direction[0] = 1
            elif self.lines.direction[-1] == -1: # Previous trend was down
                if self.datas[0].close[0] > final_ub:
                    self.lines.direction[0] = 1
                else:
                    self.lines.direction[0] = -1
            else:
                self.lines.direction[0] = 0

        # Set SuperTrend line value
        if self.lines.direction[0] == 1:
            self.lines.supertrend[0] = final_lb
        elif self.lines.direction[0] == -1:
            self.lines.supertrend[0] = final_ub
        else:
            self.lines.supertrend[0] = np.nan

