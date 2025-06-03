"""
ATR-based exit logic for trading strategies. Sets stop-loss and take-profit based on ATR multiples.
"""
from src.exit.base_exit import BaseExitLogic
import backtrader as bt

class ATRExit(BaseExitLogic):
    def __init__(self, strategy, params=None):
        super().__init__(strategy)
        params = params or {}
        atr_period = params.get('atr_period', 14)
        self.sl_mult = params.get('sl_mult', 1.5)
        self.tp_mult = params.get('tp_mult', 3.0)
        self.atr = bt.ind.ATR(strategy.data, period=atr_period)
        self.sl = None
        self.tp = None

    def on_entry(self):
        super().on_entry()
        atr_val = self.atr[0]
        self.sl = self.entry_price - self.sl_mult * atr_val
        self.tp = self.entry_price + self.tp_mult * atr_val

    def check_exit(self):
        price = self.strategy.data.close[0]
        if price <= self.sl or price >= self.tp:
            self.strategy.close()