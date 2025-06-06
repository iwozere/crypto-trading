"""
Base exit logic class for trading strategies. All custom exit logics should inherit from this base class.
"""

class BaseExitLogic:
    def __init__(self, params=None):
        self.params = params or {}
        self.entry_price = None
        self.atr_value = None

    def initialize(self, entry_price, atr_value):
        """Initialize the exit logic with entry price and ATR value."""
        self.entry_price = entry_price
        self.atr_value = atr_value

    def check_exit(self, current_price, highest_price, atr_value):
        """
        Check if an exit condition is met.
        
        Args:
            current_price (float): Current price
            highest_price (float): Highest price since entry
            atr_value (float): Current ATR value
            
        Returns:
            tuple: (bool, str) - (should_exit, exit_reason)
        """
        raise NotImplementedError