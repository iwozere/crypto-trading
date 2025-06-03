"""
Trailing stop exit logic for trading strategies. Exits a trade if price falls below a trailing stop percentage.
"""
from src.exit.base_exit import BaseExitLogic

class TrailingStopExit(BaseExitLogic):
    def __init__(self, strategy, params=None):
        super().__init__(strategy)
        params = params or {}
        self.trail_pct = params.get('trail_pct', 0.02)
        self.trailing_stop = None

    def on_entry(self):
        super().on_entry()
        self.trailing_stop = self.entry_price * (1 - self.trail_pct)

    def check_exit(self):
        price = self.strategy.data.close[0]
        new_trailing = price * (1 - self.trail_pct)
        self.trailing_stop = max(self.trailing_stop, new_trailing)

        if price <= self.trailing_stop:
            self.strategy.close()