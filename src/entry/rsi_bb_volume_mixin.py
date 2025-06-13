"""
RSI + Bollinger Bands + Volume Entry Mixin

This module implements an entry strategy based on RSI, Bollinger Bands, and Volume.
The strategy enters a position when:
1. RSI is in the oversold zone (below rsi_oversold)
2. Price touches or is below the lower Bollinger Band (if use_bb_touch is True)
3. Volume is above its moving average

Parameters:
    rsi_period (int): Period for RSI calculation (default: 14)
    rsi_oversold (float): RSI level considered oversold (default: 30)
    bb_period (int): Period for Bollinger Bands calculation (default: 20)
    bb_stddev (float): Number of standard deviations for Bollinger Bands (default: 2.0)
    use_bb_touch (bool): Whether to require price to touch lower band (default: True)
    volume_ma_period (int): Period for Volume MA calculation (default: 20)
    min_volume (float): Minimum volume required for entry (default: 1.0)
"""

from typing import Any, Dict

import backtrader as bt
import numpy as np
from src.entry.entry_mixin import BaseEntryMixin


class RSIBBVolumeEntryMixin(BaseEntryMixin):
    """Entry mixin combining RSI, Bollinger Bands, and Volume indicators"""

    def get_required_params(self) -> list:
        """There are no required parameters - all have default values"""
        return []

    def get_default_params(self) -> Dict[str, Any]:
        """Default parameters"""
        return {
            "rsi_period": 14,
            "rsi_oversold": 30,
            "bb_period": 20,
            "bb_stddev": 2.0,
            "use_bb_touch": True,
            "volume_ma_period": 20,
            "min_volume": 1.0,
        }

    def _init_indicators(self):
        """Initialize RSI, Bollinger Bands, and Volume indicators"""
        data = self.strategy.data

        # Initialize indicators
        if self.strategy.p.use_talib:
            try:
                import talib
                # Convert data to numpy arrays
                close_data = np.array(data.close.get(size=len(data)))
                volume_data = np.array(data.volume.get(size=len(data)))
                
                # Create RSI using TA-Lib
                rsi_values = talib.RSI(
                    close_data,
                    timeperiod=self.get_param("rsi_period")
                )
                self.indicators["rsi"] = bt.indicators.RSI(
                    data.close,
                    period=self.get_param("rsi_period"),
                    plot=False
                )
                # Update RSI values one by one
                for i, value in enumerate(rsi_values):
                    if i < len(self.indicators["rsi"].lines[0]):
                        self.indicators["rsi"].lines[0][i] = value

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
                
                # Update BB values one by one
                for i in range(len(bb_upper)):
                    if i < len(self.indicators["bb_upper"]):
                        self.indicators["bb_upper"][i] = bb_upper[i]
                        self.indicators["bb_middle"][i] = bb_middle[i]
                        self.indicators["bb_lower"][i] = bb_lower[i]

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
                # Update Volume MA values one by one
                for i, value in enumerate(vol_ma_values):
                    if i < len(self.indicators["vol_ma"].lines[0]):
                        self.indicators["vol_ma"].lines[0][i] = value
                
            except ImportError:
                self.log("TA-Lib not available, falling back to Backtrader indicators")
                self._init_backtrader_indicators()
        else:
            self._init_backtrader_indicators()

    def _init_backtrader_indicators(self):
        """Initialize indicators using Backtrader's built-in functions"""
        data = self.strategy.data
        
        # Initialize RSI
        self.indicators["rsi"] = bt.indicators.RSI(
            data.close,
            period=self.get_param("rsi_period")
        )
        
        # Initialize Bollinger Bands
        bb = bt.indicators.BollingerBands(
            data.close,
            period=self.get_param("bb_period"),
            devfactor=self.get_param("bb_stddev")
        )
        self.indicators["bb_upper"] = bb.lines.top
        self.indicators["bb_middle"] = bb.lines.mid
        self.indicators["bb_lower"] = bb.lines.bot
        
        # Initialize Volume MA
        self.indicators["vol_ma"] = bt.indicators.SMA(
            data.volume,
            period=self.get_param("volume_ma_period")
        )

    def should_enter(self) -> bool:
        """Check if we should enter a position"""
        # Check RSI condition
        rsi_oversold = self.indicators["rsi"][0] < self.get_param("rsi_oversold")
        
        # Check Bollinger Bands condition if enabled
        bb_condition = True
        if self.get_param("use_bb_touch"):
            bb_condition = self.strategy.data.close[0] <= self.indicators["bb_lower"][0]
        
        # Check Volume condition
        volume_condition = (
            self.strategy.data.volume[0] > self.indicators["vol_ma"][0] * self.get_param("min_volume")
        )
        
        return rsi_oversold and bb_condition and volume_condition
