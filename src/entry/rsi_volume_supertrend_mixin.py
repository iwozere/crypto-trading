"""
RSI, Volume and SuperTrend Entry Mixin

This module implements an entry strategy based on the combination of Relative Strength Index (RSI),
Volume, and SuperTrend indicators. The strategy enters a position when:
1. RSI is in the oversold zone (below the configured threshold)
2. Volume is above its moving average by the specified multiplier
3. Price is above the SuperTrend indicator (indicating bullish trend)

Parameters:
    rsi_period (int): Period for RSI calculation (default: 14)
    rsi_oversold (float): RSI threshold for oversold condition (default: 30)
    vol_ma_period (int): Period for Volume Moving Average (default: 20)
    st_period (int): Period for SuperTrend calculation (default: 10)
    st_multiplier (float): Multiplier for SuperTrend ATR calculation (default: 3.0)
    min_volume_multiplier (float): Minimum volume multiplier compared to MA (default: 1.0)

This strategy combines mean reversion (RSI), volume confirmation, and trend following (SuperTrend)
to identify potential entry points. It's particularly effective in trending markets where you want
to enter on pullbacks with strong volume confirmation.
"""

from typing import Any, Dict

import backtrader as bt
from src.entry.entry_mixin import BaseEntryMixin


class RSIVolumeSuperTrendEntryMixin(BaseEntryMixin):
    """Entry mixin based on RSI, Volume and SuperTrend"""

    def get_required_params(self) -> list:
        """There are no required parameters - all have default values"""
        return []

    def get_default_params(self) -> Dict[str, Any]:
        """Default parameters"""
        return {
            "rsi_period": 14,
            "rsi_oversold": 30,
            "vol_ma_period": 20,
            "st_period": 10,
            "st_multiplier": 3.0,
            "min_volume_multiplier": 1.0,  # Minimum volume multiplier compared to MA
        }

    def _init_indicators(self):
        """Initialization of RSI, Volume and SuperTrend indicators"""
        if self.strategy is None:
            raise ValueError("Strategy must be set before initializing indicators")

        # Create indicators with parameters from configuration
        self.indicators["rsi"] = bt.indicators.RSI(
            self.strategy.data.close, period=self.get_param("rsi_period")
        )

        self.indicators["vol_ma"] = bt.indicators.SMA(
            self.strategy.data.volume, period=self.get_param("vol_ma_period")
        )

        # Create ATR for SuperTrend
        atr = bt.indicators.ATR(self.strategy.data, period=self.get_param("st_period"))

        # Create SuperTrend
        self.indicators["supertrend"] = bt.indicators.SuperTrend(
            self.strategy.data,
            period=self.get_param("st_period"),
            multiplier=self.get_param("st_multiplier"),
            atr=atr,
        )

    def should_enter(self, strategy) -> bool:
        """
        Entry logic: RSI in oversold zone, volume above MA,
        and price above SuperTrend
        """
        if not self.indicators:
            return False

        rsi = self.indicators["rsi"][0]
        current_price = strategy.data.close[0]
        current_volume = strategy.data.volume[0]
        vol_ma = self.indicators["vol_ma"][0]
        supertrend = self.indicators["supertrend"][0]

        # Check RSI
        rsi_oversold = rsi < self.get_param("rsi_oversold")

        # Check volume
        volume_ok = current_volume >= vol_ma * self.get_param("min_volume_multiplier")

        # Check SuperTrend
        supertrend_condition = supertrend < current_price

        return rsi_oversold and volume_ok and supertrend_condition
