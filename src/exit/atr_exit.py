"""
ATR-based exit logic for trading strategies. Exits a trade based on ATR-based take profit and stop loss levels.
"""

from src.exit.base_exit import BaseExitLogic
import backtrader as bt


class ATRExit(BaseExitLogic):
    def __init__(self, strategy, params=None):
        super().__init__(strategy, params)
        self.atr_value = None
        self.tp_level = None
        self.sl_level = None
        self.tp_multiplier = self.params.get("tp_multiplier", 2.0)
        self.sl_multiplier = self.params.get("sl_multiplier", 1.0)
        self.use_talib = self.params.get("use_talib", False)
        self.atr_period = self.params.get("atr_period", 14)

        # Initialize ATR indicator
        if self.use_talib:
            try:
                import talib
                # Use TA-Lib ATR for calculation
                self.atr = bt.talib.ATR(
                    self.strategy.data.high,
                    self.strategy.data.low,
                    self.strategy.data.close,
                    timeperiod=self.atr_period
                )
            except ImportError:
                self.log("TA-Lib not available, falling back to Backtrader ATR")
                self.atr = bt.indicators.ATR(self.strategy.data, period=self.atr_period)
        else:
            # Use Backtrader's built-in ATR
            self.atr = bt.indicators.ATR(self.strategy.data, period=self.atr_period)

    def initialize(self, entry_price, **kwargs):
        """
        Initialize the exit logic with entry price and ATR value.

        Args:
            entry_price (float): The entry price for the trade
            **kwargs: Additional parameters (not used, ATR is calculated internally)
        """
        super().initialize(entry_price)
        self.atr_value = self.atr[0]
        if self.atr_value is not None:
            self._update_levels()

    def next(self, **kwargs):
        """
        Update ATR-based levels on each new bar.

        Args:
            **kwargs: Additional data (not used, ATR is calculated internally)
        """
        self.atr_value = self.atr[0]
        if self.atr_value is not None:
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
