"""
Base exit logic class for trading strategies. All custom exit logics should inherit from this base class.
"""

class BaseExitLogic:
    def __init__(self, strategy):
        self.strategy = strategy
        self.entry_price = None

    def on_entry(self):
        self.entry_price = self.strategy.data.close[0]

    def check_exit(self):
        raise NotImplementedError