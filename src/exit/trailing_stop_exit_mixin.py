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
    use_talib (bool): Whether to use TA-Lib for ATR calculation (default: False)

This strategy is particularly effective for:
1. Capturing trends while protecting profits
2. Letting winners run while managing risk
3. Adapting to market volatility when using ATR-based stops
4. Preventing premature exits in strong trends
"""

from typing import Any, Dict, Optional

import backtrader as bt
from src.exit.base_exit_mixin import BaseExitMixin
import numpy as np
from src.notification.logger import get_logger

logger = get_logger(__name__)

class TrailingStopExitMixin(BaseExitMixin):
    """Exit mixin based on trailing stop"""

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        """Initialize the mixin with parameters"""
        super().__init__(params)
        self.highest_price = 0
        self.atr_name = 'exit_atr'

    def get_required_params(self) -> list:
        """There are no required parameters - all have default values"""
        return []

    @classmethod
    def get_default_params(cls) -> Dict[str, Any]:
        """Default parameters"""
        return {
            "trail_pct": 0.02,
            "activation_pct": 0.0,
            "use_atr": False,
            "atr_multiplier": 2.0,
            "use_talib": False,
        }

    def _init_indicators(self):
        """Initialize trailing stop indicators"""
        if not hasattr(self, 'strategy'):
            return
        data = self.strategy.data
        if self.get_param("use_atr", False):
            use_talib = self.get_param("use_talib", False)
            try:
                if use_talib:
                    import talib
                    high_prices = np.array([data.high[i] for i in range(len(data))])
                    low_prices = np.array([data.low[i] for i in range(len(data))])
                    close_prices = np.array([data.close[i] for i in range(len(data))])
                    atr_values = talib.ATR(high_prices, low_prices, close_prices, timeperiod=14)
                    class TALibATR(bt.Indicator):
                        lines = ('atr',)
                        def __init__(self):
                            self.addminperiod(self.p.period)
                        def next(self):
                            idx = len(self.data) - 1
                            if idx < len(atr_values):
                                self.lines.atr[0] = atr_values[idx]
                    setattr(self.strategy, self.atr_name, TALibATR(data, period=14))
                else:
                    setattr(self.strategy, self.atr_name, bt.indicators.ATR(data, period=14, plot=False))
            except ImportError:
                logger.warning("TA-Lib not available, using Backtrader's ATR")
                setattr(self.strategy, self.atr_name, bt.indicators.ATR(data, period=14, plot=False))
            except Exception as e:
                logger.error(f"Error initializing ATR indicator: {str(e)}")
                raise

    def should_exit(self) -> bool:
        """Check if we should exit a position"""
        if not self.strategy.position:
            return False

        price = self.strategy.data.close[0]
        entry_price = self.strategy.position.price

        # Update highest price if current price is higher
        if price > self.highest_price:
            self.highest_price = price

        # Calculate trailing stop level
        if self.get_param("use_atr", False):
            if not hasattr(self.strategy, self.atr_name):
                return False
            atr = getattr(self.strategy, self.atr_name)
            atr_val = atr[0] if hasattr(atr, '__getitem__') else atr.lines.atr[0]
            stop_level = self.highest_price - (atr_val * self.get_param("atr_multiplier"))
        else:
            stop_level = self.highest_price * (1 - self.get_param("trail_pct"))

        # Check if trailing stop should be activated
        if self.get_param("activation_pct", 0.0) > 0:
            profit_pct = (price - entry_price) / entry_price
            if profit_pct < self.get_param("activation_pct"):
                return False

        # Exit if price falls below trailing stop
        return price < stop_level
