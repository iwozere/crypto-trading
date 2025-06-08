"""
Moving Average crossover exit logic for trading strategies. Exits a trade when price crosses below a moving average.
"""

import numpy as np
from src.exit.base_exit import BaseExitLogic


class MACrossoverExit(BaseExitLogic):
    def __init__(self, params=None):
        super().__init__(params)
        self.ma_period = self.params.get("ma_period", 20)
        self.prices = []
        self.ma_values = []

    def initialize(self, entry_price):
        """Initialize the exit logic with entry price."""
        super().initialize(entry_price)
        self.prices = [entry_price]
        self.ma_values = [entry_price]

    def check_exit(self, current_price):
        """
        Check if price has crossed below the moving average.

        Args:
            current_price (float): Current price

        Returns:
            tuple: (bool, str) - (should_exit, exit_reason)
        """
        self.prices.append(current_price)
        if len(self.prices) > self.ma_period:
            self.prices.pop(0)

        ma = np.mean(self.prices)
        self.ma_values.append(ma)

        if len(self.ma_values) > 2:
            prev_ma = self.ma_values[-2]
            if current_price < ma and current_price > prev_ma:
                return True, "ma crossover"
        return False, None
