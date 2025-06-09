"""
ATR-based exit logic for trading strategies. Exits a trade based on ATR-based take profit and stop loss levels.
"""

from src.exit.base_exit import BaseExitLogic


class ATRExit(BaseExitLogic):
    def __init__(self, params=None):
        super().__init__(params)
        self.atr_value = None
        self.tp_level = None
        self.sl_level = None
        self.tp_multiplier = self.params.get("tp_multiplier", 2.0)
        self.sl_multiplier = self.params.get("sl_multiplier", 1.0)

    def initialize(self, entry_price, **kwargs):
        """
        Initialize the exit logic with entry price and ATR value.

        Args:
            entry_price (float): The entry price for the trade
            **kwargs: Additional parameters including:
                - atr_value (float): Current ATR value
        """
        super().initialize(entry_price)
        self.atr_value = kwargs.get("atr_value")
        if self.atr_value is not None:
            self._update_levels()

    def next(self, **kwargs):
        """
        Update ATR-based levels if ATR value is provided.

        Args:
            **kwargs: Additional data including:
                - atr_value (float): Current ATR value
        """
        atr_value = kwargs.get("atr_value")
        if atr_value is not None:
            self.atr_value = atr_value
            self._update_levels()

    def _update_levels(self):
        """Update TP and SL levels based on current ATR value."""
        if self.atr_value is not None and self.entry_price is not None:
            self.tp_level = self.entry_price + (self.atr_value * self.tp_multiplier)
            self.sl_level = self.entry_price - (self.atr_value * self.sl_multiplier)

    def check_exit(self, current_price):
        """
        Check if price has hit TP or SL levels.

        Args:
            current_price (float): Current price

        Returns:
            tuple: (bool, str) - (should_exit, exit_reason)
        """
        if self.tp_level is None or self.sl_level is None:
            return False, None

        if current_price >= self.tp_level:
            return True, "TP"
        elif current_price <= self.sl_level:
            return True, "SL"
        return False, None
