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

from typing import Any, Dict, Optional

import backtrader as bt
import numpy as np
from src.entry.base_entry_mixin import BaseEntryMixin


class RSIBBVolumeEntryMixin(BaseEntryMixin):
    """Entry mixin combining RSI, Bollinger Bands, and Volume indicators"""

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        super().__init__(params)

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
            "use_talib": False,
        }

    def _init_indicators(self):
        """Initialize RSI, Bollinger Bands, and Volume indicators"""
        if not hasattr(self, 'strategy'):
            return
        data = self.strategy.data
        use_talib = self.get_param("use_talib", False)
        if use_talib:
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
                self.strategy.logger.warning("TA-Lib not available, using Backtrader's indicators")
                self._init_backtrader_indicators()
        else:
            self._init_backtrader_indicators()

    def _init_backtrader_indicators(self):
        """Initialize indicators using Backtrader's built-in functions"""
        data = self.strategy.data
        
        # Initialize RSI
        self.indicators["rsi"] = bt.indicators.RSI(
            data.close,
            period=self.get_param("rsi_period"),
            plot=False
        )
        
        # Initialize Bollinger Bands
        bb = bt.indicators.BollingerBands(
            data.close,
            period=self.get_param("bb_period"),
            devfactor=self.get_param("bb_stddev"),
            plot=False
        )
        self.indicators["bb"] = bb
        
        # Initialize Volume MA
        self.indicators["vol_ma"] = bt.indicators.SMA(
            data.volume,
            period=self.get_param("volume_ma_period"),
            plot=False
        )

    def should_enter(self) -> bool:
        """Check if we should enter a position"""
        if not self.indicators:
            return False
        rsi = self.indicators["rsi"][0]
        bb = self.indicators["bb"]
        vol_ma = self.indicators["vol_ma"][0]
        current_price = self.strategy.data.close[0]
        current_volume = self.strategy.data.volume[0]
        
        rsi_condition = rsi < self.get_param("rsi_oversold")
        bb_condition = not self.get_param("use_bb_touch") or current_price <= bb.lines[2][0]
        volume_condition = current_volume > vol_ma * self.get_param("min_volume")
        
        return rsi_condition and bb_condition and volume_condition
