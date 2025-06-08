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
        self.atr_value = None

    def initialize(self, entry_price):
        """Initialize the exit logic with entry price."""
        super().initialize(entry_price)
        # Initialize with None values - will be updated on first check_exit
        self.tp_price = None
        self.sl_price = None
        self.atr_value = None

    def _update_levels(self, atr_value):
        """Update take profit and stop loss levels based on current ATR value."""
        if atr_value is None:
            return
            
        self.atr_value = atr_value
        self.tp_price = self.entry_price + (self.tp_mult * atr_value)
        self.sl_price = self.entry_price - (self.sl_mult * atr_value)

    def check_exit(self, current_price):
        """
        Check if price has hit take profit or stop loss levels.
        
        Args:
            current_price (float): Current price
            
        Returns:
            tuple: (bool, str) - (should_exit, exit_reason)
        """
        # If we don't have ATR value yet, we can't make exit decisions
        if self.atr_value is None:
            return False, None
            
        if current_price >= self.tp_price:
            return True, "take profit"
        elif current_price <= self.sl_price:
            return True, "stop loss"
        return False, None

    def on_new_candle(self, **kwargs):
        """
        Called on each new candle with any additional data needed.
        Each exit logic can implement what it needs.
        """
        atr_value = kwargs.get('atr_value')
        if atr_value is not None:
            self._update_levels(atr_value)
