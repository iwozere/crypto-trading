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

from typing import Any, Dict

import backtrader as bt
import numpy as np
from src.entry.base_entry_mixin import BaseEntryMixin


class BBVolumeSupertrendEntryMixin(BaseEntryMixin):
    """Entry mixin based on Bollinger Bands, Volume, and Supertrend"""

    def get_required_params(self) -> list:
        """There are no required parameters - all have default values"""
        return []

    def get_default_params(self) -> Dict[str, Any]:
        """Default parameters"""
        return {
            "bb_period": 20,
            "bb_stddev": 2.0,
            "atr_period": 10,
            "atr_multiplier": 3.0,
            "volume_ma_period": 20,
            "min_volume_ratio": 1.5,
            "use_bb_touch": True,  # Require touching the Bollinger Bands
        }

    def _init_indicators(self):
        """Initialize Bollinger Bands, Volume, and Supertrend indicators"""
        if self.strategy is None:
            raise ValueError("Strategy must be set before initializing indicators")

        data = self.strategy.data

        # Initialize indicators
        if self.strategy.p.use_talib:
            try:
                import talib
                # Convert data to numpy arrays
                close_data = np.array(data.close.get(size=len(data)))
                high_data = np.array(data.high.get(size=len(data)))
                low_data = np.array(data.low.get(size=len(data)))
                volume_data = np.array(data.volume.get(size=len(data)))
                
                # Create Bollinger Bands using TA-Lib
                bb_upper, bb_middle, bb_lower = talib.BBANDS(
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
                self.indicators["bb_upper"] = bb.lines.top
                self.indicators["bb_middle"] = bb.lines.mid
                self.indicators["bb_lower"] = bb.lines.bot
                
                # Update the arrays with TA-Lib values
                self.indicators["bb_upper"].array = bb_upper
                self.indicators["bb_middle"].array = bb_middle
                self.indicators["bb_lower"].array = bb_lower

                # Create ATR using TA-Lib
                atr_values = talib.ATR(
                    high_data,
                    low_data,
                    close_data,
                    timeperiod=self.get_param("atr_period")
                )
                self.indicators["atr"] = bt.indicators.ATR(
                    data,
                    period=self.get_param("atr_period"),
                    plot=False
                )
                self.indicators["atr"].lines[0].array = atr_values

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
                self.indicators["vol_ma"].lines[0].array = vol_ma_values

            except ImportError:
                self.log("TA-Lib not available, falling back to Backtrader indicators")
                self._init_backtrader_indicators()
        else:
            self._init_backtrader_indicators()

        # Calculate Supertrend
        atr = self.indicators["atr"]
        multiplier = self.get_param("atr_multiplier")

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
            devfactor=self.get_param("bb_stddev")
        )
        self.indicators["bb_upper"] = bb.lines.top
        self.indicators["bb_middle"] = bb.lines.mid
        self.indicators["bb_lower"] = bb.lines.bot

        # Create ATR indicator
        self.indicators["atr"] = bt.indicators.ATR(
            data,
            period=self.get_param("atr_period")
        )

        # Create Volume MA indicator
        self.indicators["vol_ma"] = bt.indicators.SMA(
            data.volume,
            period=self.get_param("volume_ma_period")
        )

    def should_enter(self) -> bool:
        """
        Entry logic: Price touching lower BB, volume above MA, and Supertrend bullish
        """
        if not self.indicators:
            return False

        current_price = self.strategy.data.close[0]
        volume = self.strategy.data.volume[0]
        vol_ma = self.indicators["vol_ma"][0]
        direction = self.indicators["direction"][0]

        # Check volume
        volume_ok = volume >= vol_ma * self.get_param("min_volume_ratio")

        # Check touching the Bollinger Bands (if enabled)
        bb_condition = True
        if self.get_param("use_bb_touch"):
            bb_lower = self.indicators["bb_lower"][0]
            bb_condition = current_price <= bb_lower * 1.01  # Small tolerance

        # Check Supertrend (bullish when price is above Supertrend)
        supertrend_bullish = direction > 0

        return volume_ok and bb_condition and supertrend_bullish
