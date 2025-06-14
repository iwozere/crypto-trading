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

from typing import Any, Dict, Optional
from src.exit.base_exit_mixin import BaseExitMixin


class FixedRatioExitMixin(BaseExitMixin):
    """Exit mixin based on a fixed ratio of profit or loss"""

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        """Initialize the mixin with parameters"""
        super().__init__(params)
        self.highest_price = 0
        self.lowest_price = float('inf')

    def get_required_params(self) -> list:
        """There are no required parameters - all have default values"""
        return []

    @classmethod
    def get_default_params(cls) -> Dict[str, Any]:
        """Default parameters"""
        return {
            "profit_ratio": 0.1,
            "loss_ratio": 0.05,
            "use_trailing_stop": False,
            "trail_percent": 0.5,
        }

    def _init_indicators(self):
        """Initialize any required indicators"""
        if not hasattr(self, 'strategy'):
            return

    def should_exit(self) -> bool:
        """Check if we should exit a position"""
        if not self.strategy.position:
            return False
        entry_price = self.strategy.position.price
        current_price = self.strategy.data.close[0]
        profit_ratio = (current_price - entry_price) / entry_price
        if profit_ratio >= self.get_param("profit_ratio"):
            return True
        if profit_ratio <= -self.get_param("loss_ratio"):
            return True
        return False 