"""
RSI and Ichimoku Cloud Entry Mixin

This module implements an entry strategy based on the combination of Relative Strength Index (RSI)
and Ichimoku Cloud indicators. The strategy enters a position when:
1. RSI is in the oversold zone (below the configured threshold)
2. Price is below the Ichimoku Cloud (bearish cloud)
3. Price crosses above the Tenkan-sen (Conversion Line)

Parameters:
    rsi_period (int): Period for RSI calculation (default: 14)
    rsi_oversold (float): RSI threshold for oversold condition (default: 30)
    ichimoku_tenkan (int): Period for Tenkan-sen calculation (default: 9)
    ichimoku_kijun (int): Period for Kijun-sen calculation (default: 26)
    ichimoku_senkou_span_b (int): Period for Senkou Span B calculation (default: 52)
    ichimoku_displacement (int): Displacement for Ichimoku Cloud (default: 26)

This strategy combines mean reversion (RSI) with trend following (Ichimoku) to identify potential
reversal points in the market. It's particularly effective in trending markets where you want to
catch the beginning of a new trend after a pullback.
"""

from typing import Any, Dict

import backtrader as bt

from .base_entry_mixin import BaseEntryMixin


class RSIIchimokuEntryMixin(BaseEntryMixin):
    """
    Entry mixin based on RSI and Ichimoku Cloud indicators.

    Parameters:
    -----------
    rsi_period : int
        Period for RSI calculation (default: 14)
    rsi_oversold : float
        RSI oversold threshold (default: 30)
    tenkan_period : int
        Period for Tenkan-sen (Conversion Line) (default: 9)
    kijun_period : int
        Period for Kijun-sen (Base Line) (default: 26)
    senkou_span_b_period : int
        Period for Senkou Span B (Leading Span B) (default: 52)
    displacement : int
        Displacement for Senkou Span A and B (default: 26)
    use_talib : bool
        Whether to use TA-Lib for indicator calculations (default: False)
    """

    # Define default values as class constants
    DEFAULT_RSI_PERIOD = 14
    DEFAULT_RSI_OVERSOLD = 30
    DEFAULT_TENKAN_PERIOD = 9
    DEFAULT_KIJUN_PERIOD = 26
    DEFAULT_SENKOU_SPAN_B_PERIOD = 52
    DEFAULT_DISPLACEMENT = 26
    DEFAULT_USE_TALIB = False

    def __init__(self, params: Dict[str, Any]):
        super().__init__(params)
        self.rsi_period = params.get("rsi_period", self.DEFAULT_RSI_PERIOD)
        self.rsi_oversold = params.get("rsi_oversold", self.DEFAULT_RSI_OVERSOLD)
        self.tenkan_period = params.get("tenkan_period", self.DEFAULT_TENKAN_PERIOD)
        self.kijun_period = params.get("kijun_period", self.DEFAULT_KIJUN_PERIOD)
        self.senkou_span_b_period = params.get("senkou_span_b_period", self.DEFAULT_SENKOU_SPAN_B_PERIOD)
        self.displacement = params.get("displacement", self.DEFAULT_DISPLACEMENT)
        self.use_talib = params.get("use_talib", self.DEFAULT_USE_TALIB)

    def get_required_params(self) -> list:
        """There are no required parameters - all have default values"""
        return []

    def get_default_params(self) -> Dict[str, Any]:
        """Default parameters"""
        return {
            "rsi_period": self.DEFAULT_RSI_PERIOD,
            "rsi_oversold": self.DEFAULT_RSI_OVERSOLD,
            "tenkan_period": self.DEFAULT_TENKAN_PERIOD,
            "kijun_period": self.DEFAULT_KIJUN_PERIOD,
            "senkou_span_b_period": self.DEFAULT_SENKOU_SPAN_B_PERIOD,
            "displacement": self.DEFAULT_DISPLACEMENT,
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

            # Create Ichimoku Cloud indicator
            self.ichimoku = bt.indicators.IchimokuCloud(
                self.strategy.data,
                tenkan_period=self.tenkan_period,
                kijun_period=self.kijun_period,
                senkou_span_b_period=self.senkou_span_b_period,
                displacement=self.displacement,
            )
        else:
            # Create RSI indicator using Backtrader
            self.rsi = bt.indicators.RSI(
                self.strategy.data.close, period=self.rsi_period
            )

            # Create Ichimoku Cloud indicator
            self.ichimoku = bt.indicators.IchimokuCloud(
                self.strategy.data,
                tenkan_period=self.tenkan_period,
                kijun_period=self.kijun_period,
                senkou_span_b_period=self.senkou_span_b_period,
                displacement=self.displacement,
            )

    def should_enter(self) -> bool:
        """
        Check if we should enter a long position based on RSI and Ichimoku Cloud.

        Returns:
        --------
        bool
            True if we should enter, False otherwise
        """
        # Check if RSI is oversold
        rsi_oversold = self.rsi[0] < self.rsi_oversold

        # Check if price is above the cloud
        price_above_cloud = (
            self.strategy.data.close[0] > self.ichimoku.senkou_span_a[0]
            and self.strategy.data.close[0] > self.ichimoku.senkou_span_b[0]
        )

        # Check if Tenkan-sen crosses above Kijun-sen
        tenkan_cross = (
            self.ichimoku.tenkan_sen[0] > self.ichimoku.kijun_sen[0]
            and self.ichimoku.tenkan_sen[-1] <= self.ichimoku.kijun_sen[-1]
        )

        return rsi_oversold and price_above_cloud and tenkan_cross
