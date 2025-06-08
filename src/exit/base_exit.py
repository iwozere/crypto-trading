"""
Base exit logic class for trading strategies. All custom exit logics should inherit from this base class.
"""


class BaseExitLogic:
    def __init__(self, params=None):
        self.params = params or {}
        self.entry_price = None

    def initialize(self, entry_price):
        """Initialize the exit logic with entry price."""
        self.entry_price = entry_price

    def check_exit(self, current_price):
        """
        Check if an exit condition is met.

        Args:
            current_price (float): Current price

        Returns:
            tuple: (bool, str) - (should_exit, exit_reason)
        """
        raise NotImplementedError
