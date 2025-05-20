import backtrader as bt
import numpy as np

# Custom SuperTrend Indicator
class SuperTrend(bt.Indicator):
    lines = ('supertrend', 'direction',) # supertrend line and direction (-1 for short, 1 for long)
    params = (('period', 10), ('multiplier', 3.0),)

    def __init__(self):
        self.atr = bt.indicators.ATR(self.datas[0], period=self.p.period)
        # Basic Upper Band = (High + Low) / 2 + Multiplier * ATR
        # Basic Lower Band = (High + Low) / 2 - Multiplier * ATR
        self.basic_ub = ((self.datas[0].high + self.datas[0].low) / 2) + self.p.multiplier * self.atr
        self.basic_lb = ((self.datas[0].high + self.datas[0].low) / 2) - self.p.multiplier * self.atr

        # Final Upper Band and Final Lower Band
        self.final_ub = bt.indicators.Max(self.basic_ub) # Placeholder, logic will be in next
        self.final_lb = bt.indicators.Min(self.basic_lb) # Placeholder, logic will be in next
        # Do not assign to self.lines.direction[0] or self.lines.supertrend[0] here

    def next(self):
        # If ATR is not yet valid, do nothing or carry forward
        if len(self.atr.lines.atr) < self.p.period or len(self) < 2:
            self.lines.supertrend[0] = np.nan
            self.lines.direction[0] = 0 # Undefined
            return

        # Calculate current final upper and lower bands
        # Only use negative indices if len(self) > 1
        prev_final_ub = self.final_ub[-1] if len(self) > 1 else self.basic_ub[0]
        prev_final_lb = self.final_lb[-1] if len(self) > 1 else self.basic_lb[0]
        prev_close = self.datas[0].close[-1] if len(self) > 1 else self.datas[0].close[0]

        if self.basic_ub[0] < prev_final_ub or prev_close > prev_final_ub:
            self.final_ub[0] = self.basic_ub[0]
        else:
            self.final_ub[0] = prev_final_ub

        if self.basic_lb[0] > prev_final_lb or prev_close < prev_final_lb:
            self.final_lb[0] = self.basic_lb[0]
        else:
            self.final_lb[0] = prev_final_lb
        
        # Set initial direction if it's undefined (first proper calculation)
        if self.lines.direction[-1] == 0:
            if self.datas[0].close[0] > prev_final_ub:
                self.lines.direction[0] = 1
            elif self.datas[0].close[0] < prev_final_lb:
                self.lines.direction[0] = -1
            else:
                self.lines.direction[0] = 0 # Still undefined
                self.lines.supertrend[0] = np.nan
                return

        # Determine current direction and SuperTrend line
        if self.lines.direction[-1] == 1: # Previous trend was up
            if self.datas[0].close[0] < self.final_lb[0]:
                self.lines.direction[0] = -1
            else:
                self.lines.direction[0] = 1
        elif self.lines.direction[-1] == -1: # Previous trend was down
            if self.datas[0].close[0] > self.final_ub[0]:
                self.lines.direction[0] = 1
            else:
                self.lines.direction[0] = -1

        # Set SuperTrend line value
        if self.lines.direction[0] == 1:
            self.lines.supertrend[0] = self.final_lb[0]
        elif self.lines.direction[0] == -1:
            self.lines.supertrend[0] = self.final_ub[0]
        else: # Direction is 0 (undetermined initial state)
            self.lines.supertrend[0] = np.nan

