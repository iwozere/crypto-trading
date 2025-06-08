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
        """Basic initialization with just entry price"""
        super().initialize(entry_price)
        self.atr_value = None
        # Set initial TP/SL levels
        self._update_levels(None)

    def _update_levels(self, atr_value):
        """Update take profit and stop loss levels based on current ATR value."""
        self.tp_price = self.entry_price + self.tp_mult * atr_value if atr_value else None
        self.sl_price = self.entry_price - self.sl_mult * atr_value if atr_value else None

    def get_stop_loss(self):
        """Get the current stop loss price."""
        return self.sl_price

    def on_new_candle(self, **kwargs):
        """
        Called on each new candle with any additional data needed.
        Each exit logic can implement what it needs.
        """
        self.atr_value = kwargs.get('atr_value')
        if self.atr_value is None:
            raise ValueError("ATR value required")
        self._update_levels(self.atr_value)

    def check_exit(self, current_price):
        """Basic exit check with just price data"""
        # Update TP/SL levels with current ATR value
        self._update_levels(self.atr_value)
        
        if current_price >= self.tp_price:
            return True, "take profit"
        elif current_price <= self.sl_price:
            return True, "stop loss"
        return False, None
