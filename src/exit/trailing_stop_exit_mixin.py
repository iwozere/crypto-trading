import backtrader as bt
from typing import Dict, Any

class TrailingStopExitMixin:
    """Mixin for implementing a trailing stop exit strategy"""

    def __init__(self, strategy_config: Dict[str, Any]):
        """Initialize the mixin with configuration parameters"""
        self.strategy = None
        self.highest_price = 0
        self.trailing_stop_percent = strategy_config.get("trailing_stop_percent", 0.02)

    def set_strategy(self, strategy: bt.Strategy):
        """Set the strategy instance and initialize indicators"""
        self.strategy = strategy
        self._init_indicators()

    def _init_indicators(self):
        """Initialize trailing stop indicators"""
        if self.strategy is None:
            raise ValueError("Strategy must be set before initializing indicators")

        # No indicators needed for trailing stop
        self.highest_price = 0

    def should_exit(self) -> bool:
        """Check if we should exit based on trailing stop"""
        if not self.strategy.position:
            return False

        current_price = self.strategy.data.close[0]
        
        # Update highest price if current price is higher
        if current_price > self.highest_price:
            self.highest_price = current_price

        # Calculate stop loss level
        stop_loss = self.highest_price * (1 - self.trailing_stop_percent)

        # Exit if price falls below stop loss
        return current_price < stop_loss

    def get_default_params(self) -> Dict[str, Any]:
        """Get default parameters for the mixin"""
        return {
            "trailing_stop_percent": 0.02  # 2% trailing stop
        } 