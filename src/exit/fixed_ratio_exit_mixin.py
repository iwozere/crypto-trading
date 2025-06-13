"""
Fixed Ratio Exit Mixin

This module implements an exit strategy based on fixed profit and loss ratios.
The strategy exits a position when:
1. Price reaches the take profit level (entry price * (1 + profit_ratio))
2. Price reaches the stop loss level (entry price * (1 - stop_loss_ratio))

Parameters:
    profit_ratio (float): Ratio for take profit level (default: 0.02)
    stop_loss_ratio (float): Ratio for stop loss level (default: 0.01)
    use_trailing_stop (bool): Whether to use trailing stop (default: False)
    trail_percent (float): Percentage to trail the stop (default: 0.5)

This strategy is particularly effective for:
1. Setting clear profit targets
2. Managing risk with fixed stop losses
3. Protecting profits with trailing stops
"""

from typing import Any, Dict

import backtrader as bt
import numpy as np
from src.exit.exit_mixin import BaseExitMixin


class FixedRatioExitMixin(BaseExitMixin):
    """Exit mixin based on fixed profit and loss ratios"""

    def get_required_params(self) -> list:
        """There are no required parameters - all have default values"""
        return []

    def get_default_params(self) -> Dict[str, Any]:
        """Default parameters"""
        return {
            "profit_ratio": 0.02,  # 2% profit target
            "stop_loss_ratio": 0.01,  # 1% stop loss
            "use_trailing_stop": False,
            "trail_percent": 0.5,
        }

    def _init_indicators(self):
        """Initialize any required indicators"""
        if self.strategy is None:
            raise ValueError("Strategy must be set before initializing indicators")

        # Initialize trailing stop variables
        self.highest_price = 0
        self.lowest_price = float('inf')

    def should_exit(self) -> bool:
        """
        Exit logic: Price reaches take profit or stop loss level
        """
        if not self.strategy.position:
            return False

        current_price = self.strategy.data.close[0]
        position = self.strategy.position
        entry_price = position.price

        if position.size > 0:  # Long position
            # Update highest price for trailing stop
            self.highest_price = max(self.highest_price, current_price)

            # Check take profit
            take_profit = entry_price * (1 + self.get_param("profit_ratio"))
            if current_price >= take_profit:
                return True

            # Check stop loss
            if self.get_param("use_trailing_stop"):
                stop_price = self.highest_price * (1 - self.get_param("trail_percent") / 100)
            else:
                stop_price = entry_price * (1 - self.get_param("stop_loss_ratio"))
            return current_price <= stop_price

        else:  # Short position
            # Update lowest price for trailing stop
            self.lowest_price = min(self.lowest_price, current_price)

            # Check take profit
            take_profit = entry_price * (1 - self.get_param("profit_ratio"))
            if current_price <= take_profit:
                return True

            # Check stop loss
            if self.get_param("use_trailing_stop"):
                stop_price = self.lowest_price * (1 + self.get_param("trail_percent") / 100)
            else:
                stop_price = entry_price * (1 + self.get_param("stop_loss_ratio"))
            return current_price >= stop_price 