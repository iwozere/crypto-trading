"""
Fixed stop-loss and take-profit exit logic for trading strategies, using a risk-reward ratio and stop-loss percentage.
"""
from src.exit.base_exit import BaseExitLogic

class FixedTP_SL_Exit(BaseExitLogic):
    def __init__(self, strategy, params=None):
        super().__init__(strategy)
        params = params or {}
        self.rr = params.get('rr', 2.0)
        self.sl_pct = params.get('sl_pct', 0.01)

    def check_exit(self):
        price = self.strategy.data.close[0]
        tp = self.entry_price * (1 + self.rr * self.sl_pct)
        sl = self.entry_price * (1 - self.sl_pct)

        if price >= tp or price <= sl:
            self.strategy.close()