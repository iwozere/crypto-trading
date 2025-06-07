"""
ATR-based exit logic for trading strategies. Exits a trade based on ATR-based take profit and stop loss levels.
"""

from src.exit.base_exit import BaseExitLogic


class ATRExit(BaseExitLogic):
    def __init__(self, params=None):
        super().__init__(params)
        self.sl_mult = self.params.get("sl_mult", 1.5)
        self.tp_mult = self.params.get("tp_mult", 2.0)
        self.tp_price = None
        self.sl_price = None

    def initialize(self, entry_price, atr_value):
        """Initialize the exit logic with entry price and ATR value."""
        super().initialize(entry_price, atr_value)
        self.tp_price = self.entry_price + self.tp_mult * self.atr_value
        self.sl_price = self.entry_price - self.sl_mult * self.atr_value

    def get_stop_loss(self):
        """Get the current stop loss price."""
        return self.sl_price

    def check_exit(self, current_price, highest_price, atr_value):
        """
        Check if price has hit take profit or stop loss levels.

        Args:
            current_price (float): Current price
            highest_price (float): Highest price since entry
            atr_value (float): Current ATR value

        Returns:
            tuple: (bool, str) - (should_exit, exit_reason)
        """
        if current_price >= self.tp_price:
            return True, "take profit"
        elif current_price <= self.sl_price:
            return True, "stop loss"
        return False, None
