"""
Time-based exit logic for trading strategies. Exits a trade after a specified number of periods.
"""

from src.exit.base_exit import BaseExitLogic


class TimeBasedExit(BaseExitLogic):
    def __init__(self, params=None):
        super().__init__(params)
        self.time_period = self.params.get("time_period", 10)
        self.periods_elapsed = 0

    def initialize(self, entry_price, atr_value):
        """Initialize the exit logic with entry price and ATR value."""
        super().initialize(entry_price, atr_value)
        self.periods_elapsed = 0

    def check_exit(self, current_price, highest_price, atr_value):
        """
        Check if the specified time period has elapsed.

        Args:
            current_price (float): Current price
            highest_price (float): Highest price since entry
            atr_value (float): Current ATR value

        Returns:
            tuple: (bool, str) - (should_exit, exit_reason)
        """
        self.periods_elapsed += 1
        if self.periods_elapsed >= self.time_period:
            return True, "time based"
        return False, None
