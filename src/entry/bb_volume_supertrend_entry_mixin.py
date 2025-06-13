"""
Bollinger Bands, Volume, and Supertrend Entry Mixin

This module implements an entry strategy based on the combination of:
1. Bollinger Bands
2. Volume analysis
3. Supertrend indicator

The strategy enters a position when:
1. Price touches or crosses below the lower Bollinger Band
2. Volume is above its moving average
3. Supertrend indicator shows a bullish signal

Parameters:
    bb_period (int): Period for Bollinger Bands calculation (default: 20)
    bb_stddev (float): Standard deviation multiplier for Bollinger Bands (default: 2.0)
    atr_period (int): Period for ATR calculation (default: 10)
    atr_multiplier (float): Multiplier for ATR in Supertrend (default: 3.0)
    volume_ma_period (int): Period for volume moving average (default: 20)
    min_volume_ratio (float): Minimum volume ratio compared to MA (default: 1.5)
    use_bb_touch (bool): Whether to require price touching the lower band (default: True)

This strategy combines mean reversion (BB) with volume confirmation and trend following (Supertrend)
to identify potential reversal points with strong momentum.
"""

from typing import Any, Dict, Optional

import backtrader as bt
import numpy as np
from src.entry.base_entry_mixin import BaseEntryMixin


class BBVolumeSupertrendEntryMixin(BaseEntryMixin):
    """Entry mixin based on Bollinger Bands, Volume, and Supertrend"""

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        super().__init__(params)

    def get_required_params(self) -> list:
        """There are no required parameters - all have default values"""
        return []

    def get_default_params(self) -> Dict[str, Any]:
        """Default parameters"""
        return {
            "bb_period": 20,
            "bb_stddev": 2.0,
            "use_bb_touch": True,
            "volume_ma_period": 20,
            "min_volume": 1.0,
            "supertrend_period": 10,
            "supertrend_multiplier": 3.0,
            "use_talib": False,
        }

    def _init_indicators(self):
        """Initialize Bollinger Bands, Volume, and Supertrend indicators"""
        if not hasattr(self, 'strategy'):
            return
        data = self.strategy.data
        use_talib = self.get_param("use_talib", False)
        if use_talib:
            try:
                import talib
                # Convert data to numpy arrays
                close_data = np.array(data.close.get(size=len(data)))
                high_data = np.array(data.high.get(size=len(data)))
                low_data = np.array(data.low.get(size=len(data)))
                volume_data = np.array(data.volume.get(size=len(data)))
                
                # Create Bollinger Bands using TA-Lib
                upper, middle, lower = talib.BBANDS(
                    close_data,
                    timeperiod=self.get_param("bb_period"),
                    nbdevup=self.get_param("bb_stddev"),
                    nbdevdn=self.get_param("bb_stddev"),
                    matype=0
                )
                
                # Create Backtrader indicators and update their values
                bb = bt.indicators.BollingerBands(
                    data.close,
                    period=self.get_param("bb_period"),
                    devfactor=self.get_param("bb_stddev"),
                    plot=False
                )
                self.indicators["bb"] = bb
                for i, (u, m, l) in enumerate(zip(upper, middle, lower)):
                    if i < len(bb.lines[0]):
                        bb.lines[0][i] = u
                        bb.lines[1][i] = m
                        bb.lines[2][i] = l

                # Create ATR using TA-Lib
                atr_values = talib.ATR(
                    high_data,
                    low_data,
                    close_data,
                    timeperiod=self.get_param("supertrend_period")
                )
                self.indicators["atr"] = bt.indicators.ATR(
                    data,
                    period=self.get_param("supertrend_period"),
                    plot=False
                )
                for i, value in enumerate(atr_values):
                    if i < len(self.indicators["atr"].lines[0]):
                        self.indicators["atr"].lines[0][i] = value

                # Create Volume MA using TA-Lib
                vol_ma_values = talib.SMA(
                    volume_data,
                    timeperiod=self.get_param("volume_ma_period")
                )
                self.indicators["vol_ma"] = bt.indicators.SMA(
                    data.volume,
                    period=self.get_param("volume_ma_period"),
                    plot=False
                )
                for i, value in enumerate(vol_ma_values):
                    if i < len(self.indicators["vol_ma"].lines[0]):
                        self.indicators["vol_ma"].lines[0][i] = value

            except ImportError:
                self.strategy.logger.warning("TA-Lib not available, using Backtrader's indicators")
                self._init_backtrader_indicators()
        else:
            self._init_backtrader_indicators()

        # Calculate Supertrend
        atr = self.indicators["atr"]
        multiplier = self.get_param("supertrend_multiplier")

        # Calculate basic upper and lower bands
        hl2 = (data.high + data.low) / 2
        basic_upper = hl2 + (multiplier * atr)
        basic_lower = hl2 - (multiplier * atr)

        # Initialize Supertrend arrays
        supertrend = bt.indicators.SMA(data.close, period=1, plot=False)
        direction = bt.indicators.SMA(data.close, period=1, plot=False)

        # Calculate Supertrend values
        for i in range(1, len(data)):
            if data.close[i] > basic_upper[i - 1]:
                direction[i] = 1
            elif data.close[i] < basic_lower[i - 1]:
                direction[i] = -1
            else:
                direction[i] = direction[i - 1]

            if direction[i] == 1:
                supertrend[i] = basic_lower[i]
            else:
                supertrend[i] = basic_upper[i]

        self.indicators["supertrend"] = supertrend
        self.indicators["direction"] = direction

    def _init_backtrader_indicators(self):
        """Initialize indicators using Backtrader's built-in implementations"""
        data = self.strategy.data

        # Create Bollinger Bands indicators
        bb = bt.indicators.BollingerBands(
            data.close,
            period=self.get_param("bb_period"),
            devfactor=self.get_param("bb_stddev"),
            plot=False
        )
        self.indicators["bb"] = bb

        # Create ATR indicator
        self.indicators["atr"] = bt.indicators.ATR(
            data,
            period=self.get_param("supertrend_period"),
            plot=False
        )

        # Create Volume MA indicator
        self.indicators["vol_ma"] = bt.indicators.SMA(
            data.volume,
            period=self.get_param("volume_ma_period"),
            plot=False
        )

    def should_enter(self) -> bool:
        """
        Entry logic: Price touching lower BB, volume above MA, and Supertrend bullish
        """
        if not self.indicators:
            return False

        current_price = self.strategy.data.close[0]
        current_volume = self.strategy.data.volume[0]
        vol_ma = self.indicators["vol_ma"][0]
        direction = self.indicators["direction"][0]
        bb = self.indicators["bb"]

        # Check volume
        volume_ok = current_volume >= vol_ma * self.get_param("min_volume")

        # Check touching the Bollinger Bands (if enabled)
        bb_condition = not self.get_param("use_bb_touch") or current_price <= bb.lines[2][0] * 1.01  # Small tolerance

        # Check Supertrend (bullish when price is above Supertrend)
        supertrend_bullish = direction > 0

        return volume_ok and bb_condition and supertrend_bullish
