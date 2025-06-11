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

    def __init__(self, params: Dict[str, Any]):
        super().__init__(params)
        self.rsi_period = params.get("rsi_period", 14)
        self.rsi_oversold = params.get("rsi_oversold", 30)
        self.tenkan_period = params.get("tenkan_period", 9)
        self.kijun_period = params.get("kijun_period", 26)
        self.senkou_span_b_period = params.get("senkou_span_b_period", 52)
        self.displacement = params.get("displacement", 26)
        self.use_talib = params.get("use_talib", False)

    def _init_indicators(self):
        """Initialize indicators"""
        if self.use_talib:
            import talib

            # Create RSI indicator using TA-Lib
            self.rsi = bt.indicators.TALibIndicator(
                self.strategy.data.close, talib.RSI, period=self.rsi_period
            )

            # Create Ichimoku Cloud using TA-Lib
            # Note: TA-Lib doesn't have a direct Ichimoku implementation,
            # so we'll use Backtrader's implementation for the cloud
            self.ichimoku = bt.indicators.Ichimoku(
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

            # Create Ichimoku Cloud using Backtrader
            self.ichimoku = bt.indicators.Ichimoku(
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
