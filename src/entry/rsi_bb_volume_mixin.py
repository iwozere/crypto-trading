"""
RSI, Bollinger Bands and Volume Entry Mixin

This module implements an entry strategy based on the combination of Relative Strength Index (RSI),
Bollinger Bands, and Volume indicators. The strategy enters a position when:
1. RSI is in the oversold zone (below the configured threshold)
2. Price touches or crosses below the lower Bollinger Band
3. Volume is above its moving average by the specified multiplier

Parameters:
    rsi_period (int): Period for RSI calculation (default: 14)
    rsi_oversold (float): RSI threshold for oversold condition (default: 30)
    bb_period (int): Period for Bollinger Bands calculation (default: 20)
    bb_stddev (float): Standard deviation multiplier for Bollinger Bands (default: 2.0)
    vol_ma_period (int): Period for Volume Moving Average (default: 20)
    use_bb_touch (bool): Whether to require price touching the lower band (default: True)
    min_volume_multiplier (float): Minimum volume multiplier compared to MA (default: 1.0)

This strategy adds volume confirmation to the RSI and Bollinger Bands strategy, making it more
robust by ensuring there is sufficient market participation for the potential reversal.
"""
import backtrader as bt
from typing import Any, Dict

from src.entry.entry_mixin import BaseEntryMixin


class RSIBBVolumeEntryMixin(BaseEntryMixin):
    """Entry mixin based on RSI, Bollinger Bands and Volume"""

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
            "vol_ma_period": 20,
            "use_bb_touch": True,  # Require touching the Bollinger Bands
            "min_volume_multiplier": 1.0,  # Minimum volume multiplier compared to MA
        }

    def _init_indicators(self):
        """Initialization of RSI, Bollinger Bands and Volume indicators"""
        if self.strategy is None:
            raise ValueError("Strategy must be set before initializing indicators")

        # Use common indicators from strategy
        self.indicators["rsi"] = self.strategy.rsi
        self.indicators["bb_upper"] = self.strategy.bb_upper
        self.indicators["bb_middle"] = self.strategy.bb_middle
        self.indicators["bb_lower"] = self.strategy.bb_lower

        # Create volume MA indicator
        if self.strategy.p.use_talib:
            import talib
            self.indicators["vol_ma"] = bt.indicators.TALibIndicator(
                self.strategy.data.volume,
                talib.SMA,
                timeperiod=self.get_param("vol_ma_period")
            )
        else:
            self.indicators["vol_ma"] = bt.indicators.SMA(
                self.strategy.data.volume, 
                period=self.get_param("vol_ma_period")
            )

    def should_enter(self) -> bool:
        """
        Entry logic: RSI in the oversold zone, touching the lower BB band,
        and volume above the moving average
        """
        if not self.indicators:
            return False

        rsi = self.indicators["rsi"][0]
        current_price = self.strategy.data.close[0]
        current_volume = self.strategy.data.volume[0]
        vol_ma = self.indicators["vol_ma"][0]

        # Check RSI
        rsi_oversold = rsi < self.get_param("rsi_oversold")

        # Check volume
        volume_ok = current_volume >= vol_ma * self.get_param("min_volume_multiplier")

        # Check touching the Bollinger Bands (if enabled)
        bb_condition = True
        if self.get_param("use_bb_touch"):
            bb_lower = self.indicators["bb_lower"][0]
            bb_condition = current_price <= bb_lower * 1.01  # Small tolerance

        return rsi_oversold and volume_ok and bb_condition
