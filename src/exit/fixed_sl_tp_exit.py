"""
Fixed stop-loss and take-profit exit logic for trading strategies. Exits a trade based on fixed percentage levels.
"""
from src.exit.base_exit import BaseExitLogic

class FixedSLTPExit(BaseExitLogic):
    def __init__(self, params=None):
        super().__init__(params)
        self.sl_pct = self.params.get('sl_pct', 0.02)  # 2% stop loss
        self.rr = self.params.get('rr', 2.0)  # Risk-reward ratio
        self.tp_pct = self.sl_pct * self.rr  # Take profit percentage
        self.tp_price = None
        self.sl_price = None

    def initialize(self, entry_price, atr_value):
        """Initialize the exit logic with entry price and ATR value."""
        super().initialize(entry_price, atr_value)
        self.tp_price = self.entry_price * (1 + self.tp_pct)
        self.sl_price = self.entry_price * (1 - self.sl_pct)

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
            return True, 'take profit'
        elif current_price <= self.sl_price:
            return True, 'stop loss'
        return False, None