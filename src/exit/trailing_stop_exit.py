"""
Trailing stop exit logic for trading strategies. Exits a trade if price falls below a trailing stop percentage.
"""

from src.exit.base_exit import BaseExitLogic


class TrailingStopExit(BaseExitLogic):
    def __init__(self, strategy, params=None):
        super().__init__(strategy, params)
        self.trail_pct = self.params.get("trail_pct", 0.02)
        self.trailing_stop = None

    def initialize(self, entry_price):
        """Initialize the exit logic with entry price."""
        super().initialize(entry_price)
        self.trailing_stop = self.entry_price * (1 - self.trail_pct)

    def check_exit(self, current_price):
        """
        Check if price has fallen below the trailing stop.

        Args:
            current_price (float): Current price

        Returns:
            tuple: (bool, str) - (should_exit, exit_reason)
        """
        # Update trailing stop if price has moved higher
        new_trailing = current_price * (1 - self.trail_pct)
        self.trailing_stop = max(self.trailing_stop, new_trailing)

        if current_price <= self.trailing_stop:
            return True, "TS"
        return False, None
