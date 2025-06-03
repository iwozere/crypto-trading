"""
Moving average crossover exit logic for trading strategies. Exits when short MA crosses long MA.
"""
from src.exit.base_exit import BaseExitLogic
import backtrader as bt

class MACrossoverExit(BaseExitLogic):
    def __init__(self, strategy, params=None):
        super().__init__(strategy)
        params = params or {}
        short_ma_period = params.get('short_ma_period', 20)
        long_ma_period = params.get('long_ma_period', 50)
        self.short_ma = bt.ind.SMA(strategy.data, period=short_ma_period)
        self.long_ma = bt.ind.SMA(strategy.data, period=long_ma_period)
        self.sl = None
        self.tp = None

    def on_entry(self):
        super().on_entry()
        atr_val = self.atr[0]
        self.sl = self.entry_price - self.sl_mult * atr_val
        self.tp = self.entry_price + self.tp_mult * atr_val

    def check_exit(self):
        # Example: exit if short MA crosses below long MA
        if self.short_ma[0] < self.long_ma[0] and self.short_ma[-1] >= self.long_ma[-1]:
            self.strategy.close()