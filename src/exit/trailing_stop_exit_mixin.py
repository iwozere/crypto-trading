"""
Trailing Stop Exit Mixin

This module implements a trailing stop exit strategy that dynamically adjusts the stop loss
level as the price moves in favor of the position. The strategy exits when:
1. Price falls below the trailing stop level
2. The trailing stop level is calculated as: highest_price * (1 - trail_pct)
3. Optionally, the trailing stop can be based on ATR for dynamic adjustment

Parameters:
    trail_pct (float): Percentage for trailing stop calculation (default: 0.02)
    activation_pct (float): Minimum profit percentage before trailing stop activates (default: 0.0)
    use_atr (bool): Whether to use ATR for dynamic trailing stop (default: False)
    atr_multiplier (float): Multiplier for ATR-based trailing stop (default: 2.0)

This strategy is particularly effective for:
1. Capturing trends while protecting profits
2. Letting winners run while managing risk
3. Adapting to market volatility when using ATR-based stops
4. Preventing premature exits in strong trends
"""

from typing import Any, Dict

import backtrader as bt
from src.exit.base_exit_mixin import BaseExitMixin


class TrailingStopExitMixin(BaseExitMixin):
    """Exit mixin based on trailing stop"""

    # Define default values as class constants
    DEFAULT_TRAIL_PCT = 0.02
    DEFAULT_ACTIVATION_PCT = 0.0
    DEFAULT_USE_ATR = False
    DEFAULT_ATR_MULTIPLIER = 2.0

    def __init__(self, params: Dict[str, Any]):
        super().__init__(params)
        self.trail_pct = params.get("trail_pct", self.DEFAULT_TRAIL_PCT)
        self.activation_pct = params.get("activation_pct", self.DEFAULT_ACTIVATION_PCT)
        self.use_atr = params.get("use_atr", self.DEFAULT_USE_ATR)
        self.atr_multiplier = params.get("atr_multiplier", self.DEFAULT_ATR_MULTIPLIER)

    def get_required_params(self) -> list:
        """There are no required parameters - all have default values"""
        return []

    def get_default_params(self) -> Dict[str, Any]:
        """Default parameters"""
        return {
            "trail_pct": self.DEFAULT_TRAIL_PCT,
            "activation_pct": self.DEFAULT_ACTIVATION_PCT,
            "use_atr": self.DEFAULT_USE_ATR,
            "atr_multiplier": self.DEFAULT_ATR_MULTIPLIER,
        }

    def _init_indicators(self):
        """Initialization of indicators if needed"""
        self.highest_price = 0.0

        if self.use_atr:
            if self.strategy is None:
                raise ValueError("Strategy must be set before initializing indicators")
            self.indicators["atr"] = bt.indicators.ATR(self.strategy.data, period=14)

    def should_exit(self) -> bool:
        """
        Exit logic: Exit when price falls below trailing stop level
        """
        if not self.strategy.position:
            return False

        price = self.strategy.data.close[0]
        entry_price = self.strategy.position.price

        # Update highest price if current price is higher
        if price > self.highest_price:
            self.highest_price = price

        # Calculate trailing stop level
        if self.use_atr:
            atr = self.indicators["atr"][0]
            stop_level = self.highest_price - (atr * self.atr_multiplier)
        else:
            stop_level = self.highest_price * (1 - self.trail_pct)

        # Check if trailing stop should be activated
        if self.activation_pct > 0:
            profit_pct = (price - entry_price) / entry_price
            if profit_pct < self.activation_pct:
                return False

        # Exit if price falls below trailing stop
        return price < stop_level
