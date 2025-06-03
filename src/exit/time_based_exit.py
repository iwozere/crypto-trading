"""
Time-based exit logic for trading strategies. Exits a trade after a fixed number of bars.
"""
from src.exit.base_exit import BaseExitLogic
import backtrader as bt

class TimeBasedExit(BaseExitLogic):
    def __init__(self, strategy, hold_bars=10):
        super().__init__(strategy)
        self.hold_bars = hold_bars

    def on_entry(self):
        super().on_entry()
        self.entry_bar = len(self)

    def check_exit(self):
        if len(self) - self.entry_bar >= self.hold_bars:
            self.strategy.close()