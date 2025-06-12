"""
Fixed Ratio Exit Mixin

This module implements a simple exit strategy based on fixed percentage take profit and
stop loss levels. The strategy exits when:
1. Price reaches the take profit level (entry_price * (1 + take_profit))
2. Price reaches the stop loss level (entry_price * (1 - stop_loss))

Parameters:
    take_profit (float): Take profit percentage (default: 0.02)
    stop_loss (float): Stop loss percentage (default: 0.01)

This strategy is particularly effective for:
1. Short-term trading
2. Ranging markets
3. When you want predictable risk/reward ratios
4. When you need simple and clear exit rules

The strategy is simple but can be powerful when combined with proper position sizing
and risk management. It's often used as a baseline exit strategy that can be enhanced
with more sophisticated exit rules.
"""

from typing import Any, Dict

from src.exit.exit_mixin import BaseExitMixin


class FixedRatioExitMixin(BaseExitMixin):
    """Exit mixin based on fixed ratio take profit and stop loss"""

    # Define default values as class constants
    DEFAULT_TAKE_PROFIT = 0.02  # 2% take profit
    DEFAULT_STOP_LOSS = 0.01    # 1% stop loss

    def __init__(self, params: Dict[str, Any]):
        super().__init__(params)
        self.take_profit = params.get("take_profit", self.DEFAULT_TAKE_PROFIT)
        self.stop_loss = params.get("stop_loss", self.DEFAULT_STOP_LOSS)

    def get_required_params(self) -> list:
        """There are no required parameters - all have default values"""
        return []

    def get_default_params(self) -> Dict[str, Any]:
        """Default parameters"""
        return {
            "take_profit": self.DEFAULT_TAKE_PROFIT,
            "stop_loss": self.DEFAULT_STOP_LOSS,
        }

    def _init_indicators(self):
        """No indicators needed for fixed ratio exit"""
        pass

    def should_exit(self) -> bool:
        """
        Exit logic: Exit when price reaches take profit or stop loss levels
        based on fixed percentage ratios
        """
        if not self.strategy.position:
            return False

        price = self.strategy.data.close[0]
        entry_price = self.strategy.position.price

        # Calculate profit/loss percentage
        pnl_pct = (price - entry_price) / entry_price

        # Exit if take profit or stop loss is hit
        return pnl_pct >= self.take_profit or pnl_pct <= -self.stop_loss
