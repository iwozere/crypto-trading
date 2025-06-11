"""
RSI and Bollinger Bands Entry Mixin

This module implements an entry strategy based on the combination of Relative Strength Index (RSI)
and Bollinger Bands indicators. The strategy enters a position when:
1. RSI is in the oversold zone (below the configured threshold)
2. Price touches or crosses below the lower Bollinger Band
3. Optional volume conditions are met

Parameters:
    rsi_period (int): Period for RSI calculation (default: 14)
    rsi_oversold (float): RSI threshold for oversold condition (default: 30)
    bb_period (int): Period for Bollinger Bands calculation (default: 20)
    bb_stddev (float): Standard deviation multiplier for Bollinger Bands (default: 2.0)
    use_bb_touch (bool): Whether to require price touching the lower band (default: True)
    min_volume (float): Minimum volume required for entry (default: 0)

This strategy is particularly effective in ranging markets where price tends to revert to the mean
after reaching extreme levels.
"""

from typing import Any, Dict

import backtrader as bt
from src.entry.entry_mixin import BaseEntryMixin


class RSIBBEntryMixin(BaseEntryMixin):
    """Entry mixin based on RSI and Bollinger Bands"""

    def get_required_params(self) -> list:
        """There are no required parameters - all have default values"""
        return []

    def get_default_params(self) -> Dict[str, Any]:
        """Default parameters"""
        return {
            "rsi_period": 14,
            "rsi_oversold": 30,
            "rsi_overbought": 70,
            "bb_period": 20,
            "bb_stddev": 2.0,
            "use_bb_touch": True,  # Require touching the Bollinger Bands
            "min_volume": 0,  # Minimum volume for entry
        }

    def _init_indicators(self):
        """Initialization of RSI and Bollinger Bands indicators"""
        if self.strategy is None:
            raise ValueError("Strategy must be set before initializing indicators")

        # Create indicators with parameters from configuration
        self.indicators["rsi"] = bt.indicators.RSI(
            self.strategy.data.close, period=self.get_param("rsi_period")
        )

        self.indicators["bb"] = bt.indicators.BollingerBands(
            self.strategy.data.close,
            period=self.get_param("bb_period"),
            devfactor=self.get_param("bb_stddev"),
        )

    def should_enter(self, strategy) -> bool:
        """
        Entry logic: RSI in the oversold zone and (optionally) touching the lower BB band
        """
        if not self.indicators:
            return False

        rsi = self.indicators["rsi"][0]
        current_price = strategy.data.close[0]
        volume = strategy.data.volume[0]

        # Check RSI
        rsi_oversold = rsi < self.get_param("rsi_oversold")

        # Check volume
        volume_ok = volume >= self.get_param("min_volume")

        # Check touching the Bollinger Bands (if enabled)
        bb_condition = True
        if self.get_param("use_bb_touch"):
            bb_lower = self.indicators["bb"].lines.bot[0]
            bb_condition = (
                current_price <= bb_lower * 1.01
            )  # Small tolerance for floating point comparison

        return rsi_oversold and volume_ok and bb_condition
