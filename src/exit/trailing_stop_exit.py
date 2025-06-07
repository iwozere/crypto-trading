"""
Trailing stop exit logic for trading strategies. Exits a trade if price falls below a trailing stop percentage.
"""

from src.exit.base_exit import BaseExitLogic


class TrailingStopExit(BaseExitLogic):
    def __init__(self, params=None):
        super().__init__(params)
        self.trail_pct = self.params.get("trail_pct", 0.02)
        self.trailing_stop = None

    def initialize(self, entry_price, atr_value):
        """Initialize the exit logic with entry price and ATR value."""
        super().initialize(entry_price, atr_value)
        self.trailing_stop = self.entry_price * (1 - self.trail_pct)

    def check_exit(self, current_price, highest_price, atr_value):
        """
        Check if price has fallen below the trailing stop.

        Args:
            current_price (float): Current price
            highest_price (float): Highest price since entry
            atr_value (float): Current ATR value

        Returns:
            tuple: (bool, str) - (should_exit, exit_reason)
        """
        # Update trailing stop if price has moved higher
        new_trailing = current_price * (1 - self.trail_pct)
        self.trailing_stop = max(self.trailing_stop, new_trailing)

        if current_price <= self.trailing_stop:
            return True, "trailing stop"
        return False, None
