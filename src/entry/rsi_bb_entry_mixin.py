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

from .base_entry_mixin import BaseEntryMixin


class RSIBBEntryMixin(BaseEntryMixin):
    """
    Entry mixin based on RSI and Bollinger Bands.

    Parameters:
    -----------
    rsi_period : int
        Period for RSI calculation (default: 14)
    rsi_oversold : float
        RSI oversold threshold (default: 30)
    bb_period : int
        Period for Bollinger Bands calculation (default: 20)
    bb_devfactor : float
        Standard deviation factor for Bollinger Bands (default: 2.0)
    use_talib : bool
        Whether to use TA-Lib for indicator calculations (default: False)
    """

    # Define default values as class constants
    DEFAULT_RSI_PERIOD = 14
    DEFAULT_RSI_OVERSOLD = 30
    DEFAULT_BB_PERIOD = 20
    DEFAULT_BB_DEVFACTOR = 2.0
    DEFAULT_USE_TALIB = False

    def __init__(self, params: Dict[str, Any]):
        super().__init__(params)
        self.rsi_period = params.get("rsi_period", self.DEFAULT_RSI_PERIOD)
        self.rsi_oversold = params.get("rsi_oversold", self.DEFAULT_RSI_OVERSOLD)
        self.bb_period = params.get("bb_period", self.DEFAULT_BB_PERIOD)
        self.bb_devfactor = params.get("bb_devfactor", self.DEFAULT_BB_DEVFACTOR)
        self.use_talib = params.get("use_talib", self.DEFAULT_USE_TALIB)

    def get_required_params(self) -> list:
        """There are no required parameters - all have default values"""
        return []

    def get_default_params(self) -> Dict[str, Any]:
        """Default parameters"""
        return {
            "rsi_period": self.DEFAULT_RSI_PERIOD,
            "rsi_oversold": self.DEFAULT_RSI_OVERSOLD,
            "bb_period": self.DEFAULT_BB_PERIOD,
            "bb_devfactor": self.DEFAULT_BB_DEVFACTOR,
            "use_talib": self.DEFAULT_USE_TALIB,
        }

    def _init_indicators(self):
        """Initialize indicators"""
        if self.use_talib:
            import talib

            # Create RSI indicator using TA-Lib
            self.rsi = bt.indicators.TALibIndicator(
                self.strategy.data.close, talib.RSI, period=self.rsi_period
            )

            # Create Bollinger Bands indicator using TA-Lib
            self.bb = bt.indicators.TALibIndicator(
                self.strategy.data.close,
                talib.BBANDS,
                period=self.bb_period,
                devfactor=self.bb_devfactor,
            )
        else:
            # Create RSI indicator using Backtrader
            self.rsi = bt.indicators.RSI(
                self.strategy.data.close, period=self.rsi_period
            )

            # Create Bollinger Bands indicator using Backtrader
            self.bb = bt.indicators.BollingerBands(
                self.strategy.data.close,
                period=self.bb_period,
                devfactor=self.bb_devfactor,
            )

    def should_enter(self) -> bool:
        """
        Check if we should enter a long position based on RSI and Bollinger Bands.

        Returns:
        --------
        bool
            True if we should enter, False otherwise
        """
        # Check if RSI is oversold
        rsi_oversold = self.rsi[0] < self.rsi_oversold

        # Check if price is below lower Bollinger Band
        price_below_bb = self.strategy.data.close[0] < self.bb.lines.bot[0]

        return rsi_oversold and price_below_bb
