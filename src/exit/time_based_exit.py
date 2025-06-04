"""
Time-based exit logic for trading strategies. Exits a trade after a fixed number of bars.
"""
from src.exit.base_exit import BaseExitLogic
import backtrader as bt

class TimeBasedExit(BaseExitLogic):
    def __init__(self, strategy, params=None):
        super().__init__(strategy)
        self.hold_bars = params.get('time_period', 10) if params else 10

    def on_entry(self):
        super().on_entry()
        self.entry_bar = len(self)

    def check_exit(self):
        if len(self) - self.entry_bar >= self.hold_bars:
            self.strategy.close()