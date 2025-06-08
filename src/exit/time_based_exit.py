"""
Time-based exit logic for trading strategies. Exits a trade after a specified number of periods.
"""

from src.exit.base_exit import BaseExitLogic


class TimeBasedExit(BaseExitLogic):
    def __init__(self, params=None):
        super().__init__(params)
        self.time_period = self.params.get("time_period", 10)
        self.periods_elapsed = 0

    def initialize(self, entry_price):
        """Initialize the exit logic with entry price."""
        super().initialize(entry_price)
        self.periods_elapsed = 0

    def check_exit(self, current_price):
        """
        Check if the specified time period has elapsed.

        Args:
            current_price (float): Current price

        Returns:
            tuple: (bool, str) - (should_exit, exit_reason)
        """
        self.periods_elapsed += 1
        if self.periods_elapsed >= self.time_period:
            return True, "time based"
        return False, None
