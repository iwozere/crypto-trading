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

    def __init__(self, params: Dict[str, Any]):
        super().__init__(params)
        self.rsi_period = params.get("rsi_period", 14)
        self.rsi_oversold = params.get("rsi_oversold", 30)
        self.bb_period = params.get("bb_period", 20)
        self.bb_devfactor = params.get("bb_devfactor", 2.0)
        self.use_talib = params.get("use_talib", False)

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
