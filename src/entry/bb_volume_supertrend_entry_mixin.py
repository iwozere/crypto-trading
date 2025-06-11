"""
Bollinger Bands, Volume and SuperTrend Entry Mixin

This module implements an entry strategy based on the combination of Bollinger Bands,
Volume, and SuperTrend indicators. The strategy enters a position when:
1. Price touches or crosses below the lower Bollinger Band
2. Volume is above its moving average by the specified multiplier
3. Price is above the SuperTrend indicator (indicating bullish trend)

Parameters:
    bb_period (int): Period for Bollinger Bands calculation (default: 20)
    bb_stddev (float): Standard deviation multiplier for Bollinger Bands (default: 2.0)
    volume_ma_period (int): Period for Volume Moving Average (default: 20)
    volume_threshold (float): Volume threshold multiplier (default: 1.5)
    supertrend_period (int): Period for SuperTrend calculation (default: 10)
    supertrend_multiplier (float): Multiplier for SuperTrend ATR (default: 3.0)
    use_talib (bool): Whether to use TA-Lib for indicator calculations (default: False)

This strategy combines mean reversion (Bollinger Bands), volume confirmation, and trend following
(SuperTrend) to identify potential entry points. It's particularly effective in ranging markets
where you want to enter on oversold conditions with strong volume confirmation and trend support.
"""

from typing import Any, Dict

import backtrader as bt

from .base_entry_mixin import BaseEntryMixin


class BBVolumeSuperTrendEntryMixin(BaseEntryMixin):
    """
    Entry mixin based on Bollinger Bands, Volume, and SuperTrend indicators.

    Parameters:
    -----------
    bb_period : int
        Period for Bollinger Bands calculation (default: 20)
    bb_devfactor : float
        Standard deviation factor for Bollinger Bands (default: 2.0)
    volume_ma_period : int
        Period for volume moving average (default: 20)
    volume_threshold : float
        Volume threshold multiplier (default: 1.5)
    supertrend_period : int
        Period for SuperTrend calculation (default: 10)
    supertrend_multiplier : float
        Multiplier for SuperTrend ATR (default: 3.0)
    use_talib : bool
        Whether to use TA-Lib for indicator calculations (default: False)
    """

    # Define default values as class constants
    DEFAULT_BB_PERIOD = 20
    DEFAULT_BB_DEVFACTOR = 2.0
    DEFAULT_VOLUME_MA_PERIOD = 20
    DEFAULT_VOLUME_THRESHOLD = 1.5
    DEFAULT_SUPERTREND_PERIOD = 10
    DEFAULT_SUPERTREND_MULTIPLIER = 3.0
    DEFAULT_USE_TALIB = False

    def __init__(self, params: Dict[str, Any]):
        super().__init__(params)
        self.bb_period = params.get("bb_period", self.DEFAULT_BB_PERIOD)
        self.bb_devfactor = params.get("bb_devfactor", self.DEFAULT_BB_DEVFACTOR)
        self.volume_ma_period = params.get("volume_ma_period", self.DEFAULT_VOLUME_MA_PERIOD)
        self.volume_threshold = params.get("volume_threshold", self.DEFAULT_VOLUME_THRESHOLD)
        self.supertrend_period = params.get("supertrend_period", self.DEFAULT_SUPERTREND_PERIOD)
        self.supertrend_multiplier = params.get("supertrend_multiplier", self.DEFAULT_SUPERTREND_MULTIPLIER)
        self.use_talib = params.get("use_talib", self.DEFAULT_USE_TALIB)

    def get_required_params(self) -> list:
        """There are no required parameters - all have default values"""
        return []

    def get_default_params(self) -> Dict[str, Any]:
        """Default parameters"""
        return {
            "bb_period": self.DEFAULT_BB_PERIOD,
            "bb_devfactor": self.DEFAULT_BB_DEVFACTOR,
            "volume_ma_period": self.DEFAULT_VOLUME_MA_PERIOD,
            "volume_threshold": self.DEFAULT_VOLUME_THRESHOLD,
            "supertrend_period": self.DEFAULT_SUPERTREND_PERIOD,
            "supertrend_multiplier": self.DEFAULT_SUPERTREND_MULTIPLIER,
            "use_talib": self.DEFAULT_USE_TALIB,
        }

    def _init_indicators(self):
        """Initialize indicators"""
        if self.use_talib:
            import talib

            # Create Bollinger Bands indicator using TA-Lib
            self.bb = bt.indicators.TALibIndicator(
                self.strategy.data.close,
                talib.BBANDS,
                period=self.bb_period,
                devfactor=self.bb_devfactor,
            )

            # Create volume MA using TA-Lib
            self.volume_ma = bt.indicators.TALibIndicator(
                self.strategy.data.volume, talib.SMA, period=self.volume_ma_period
            )

            # Create ATR for SuperTrend using TA-Lib
            self.atr = bt.indicators.TALibIndicator(
                self.strategy.data, talib.ATR, period=self.supertrend_period
            )
        else:
            # Create Bollinger Bands indicator using Backtrader
            self.bb = bt.indicators.BollingerBands(
                self.strategy.data.close,
                period=self.bb_period,
                devfactor=self.bb_devfactor,
            )

            # Create volume MA using Backtrader
            self.volume_ma = bt.indicators.SMA(
                self.strategy.data.volume, period=self.volume_ma_period
            )

            # Create ATR for SuperTrend using Backtrader
            self.atr = bt.indicators.ATR(
                self.strategy.data, period=self.supertrend_period
            )

        # Create SuperTrend indicator
        self.supertrend = bt.indicators.SuperTrend(
            self.strategy.data,
            period=self.supertrend_period,
            multiplier=self.supertrend_multiplier,
        )

    def should_enter(self) -> bool:
        """
        Check if we should enter a long position based on Bollinger Bands, Volume, and SuperTrend.

        Returns:
        --------
        bool
            True if we should enter, False otherwise
        """
        # Check if price is below lower Bollinger Band
        price_below_bb = self.strategy.data.close[0] < self.bb.lines.bot[0]

        # Check if volume is above threshold
        volume_signal = self.strategy.data.volume[0] > (
            self.volume_ma[0] * self.volume_threshold
        )

        # Check if price is above SuperTrend
        supertrend_signal = self.strategy.data.close[0] > self.supertrend[0]

        return price_below_bb and volume_signal and supertrend_signal
