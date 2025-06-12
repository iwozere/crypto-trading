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
    tenkan_period (int): Period for Tenkan-sen calculation (default: 9)
    kijun_period (int): Period for Kijun-sen calculation (default: 26)
    senkou_span_b_period (int): Period for Senkou Span B calculation (default: 52)
    displacement (int): Displacement for Ichimoku Cloud (default: 26)
    use_talib (bool): Whether to use TA-Lib for calculations (default: False)

This strategy combines mean reversion (RSI) with trend following (Ichimoku) to identify potential
reversal points in the market. It's particularly effective in trending markets where you want to
catch the beginning of a new trend after a pullback.
"""

from typing import Any, Dict

import backtrader as bt
import numpy as np
from src.entry.entry_mixin import BaseEntryMixin


class RSIIchimokuEntryMixin(BaseEntryMixin):
    """Entry mixin based on RSI and Ichimoku cloud"""

    def get_required_params(self) -> list:
        # We can make some parameters required
        return ["tenkan_period", "kijun_period"]

    def get_default_params(self) -> Dict[str, Any]:
        return {
            "rsi_period": 14,
            "rsi_oversold": 30,
            "tenkan_period": 9,  # Will be required
            "kijun_period": 26,  # Will be required
            "senkou_span_b_period": 52,
            "displacement": 26,
            "require_above_cloud": True,
            "use_talib": False,
        }

    def _init_indicators(self):
        """Initialize RSI and Ichimoku Cloud indicators"""
        if self.strategy is None:
            raise ValueError("Strategy must be set before initializing indicators")

        # Initialize RSI based on use_talib flag
        if self.get_param("use_talib"):
            try:
                import talib
                # This creates an indicator that will be automatically updated
                # when new data arrives in the strategy's next() method
                self.indicators["rsi"] = bt.indicators.TALibIndicator(
                    self.strategy.data.close,  # Uses strategy's data as input
                    talib.RSI,
                    timeperiod=self.get_param("rsi_period")
                )
            except ImportError:
                self.log("TA-Lib not available, falling back to Backtrader RSI")
                self.indicators["rsi"] = bt.indicators.RSI(
                    self.strategy.data.close,
                    period=self.get_param("rsi_period")
                )
        else:
            self.indicators["rsi"] = bt.indicators.RSI(
                self.strategy.data.close,
                period=self.get_param("rsi_period")
            )

        # Create Ichimoku Cloud components
        data = self.strategy.data  # Reference to strategy's data
        
        # All these indicators will be automatically updated
        # when new data arrives in the strategy's next() method
        # Calculate Tenkan-sen (Conversion Line)
        tenkan_period = self.get_param("tenkan_period")
        tenkan_high = bt.indicators.Highest(data.high, period=tenkan_period)
        tenkan_low = bt.indicators.Lowest(data.low, period=tenkan_period)
        self.indicators["tenkan"] = (tenkan_high + tenkan_low) / 2

        # Calculate Kijun-sen (Base Line)
        kijun_period = self.get_param("kijun_period")
        kijun_high = bt.indicators.Highest(data.high, period=kijun_period)
        kijun_low = bt.indicators.Lowest(data.low, period=kijun_period)
        self.indicators["kijun"] = (kijun_high + kijun_low) / 2

        # Calculate Senkou Span A (Leading Span A)
        senkou_span_a = bt.indicators.MovingAverageSimple(
            (self.indicators["tenkan"] + self.indicators["kijun"]) / 2,
            period=1
        )
        self.indicators["senkou_span_a"] = bt.indicators.DisplaceN(
            senkou_span_a,
            n=self.get_param("displacement")
        )

        # Calculate Senkou Span B (Leading Span B)
        senkou_span_b_period = self.get_param("senkou_span_b_period")
        senkou_span_b_high = bt.indicators.Highest(data.high, period=senkou_span_b_period)
        senkou_span_b_low = bt.indicators.Lowest(data.low, period=senkou_span_b_period)
        senkou_span_b = bt.indicators.MovingAverageSimple(
            (senkou_span_b_high + senkou_span_b_low) / 2,
            period=1
        )
        self.indicators["senkou_span_b"] = bt.indicators.DisplaceN(
            senkou_span_b,
            n=self.get_param("displacement")
        )

        # Calculate Chikou Span (Lagging Span)
        chikou_span = bt.indicators.MovingAverageSimple(
            data.close,
            period=1
        )
        self.indicators["chikou_span"] = bt.indicators.DisplaceN(
            chikou_span,
            n=-self.get_param("displacement")  # Negative displacement for lagging
        )

    def should_enter(self) -> bool:
        """Entry logic: RSI oversold and Ichimoku Cloud conditions"""
        if not self.indicators:
            return False

        rsi = self.indicators["rsi"][0]
        current_price = self.strategy.data.close[0]

        # RSI condition
        rsi_ok = rsi < self.get_param("rsi_oversold")

        # Ichimoku conditions
        tenkan = self.indicators["tenkan"][0]
        kijun = self.indicators["kijun"][0]
        senkou_span_a = self.indicators["senkou_span_a"][0]
        senkou_span_b = self.indicators["senkou_span_b"][0]

        # Bullish signal: Tenkan-sen crosses above Kijun-sen
        tenkan_kijun_cross = tenkan > kijun

        # Additional condition - price above the cloud (if required)
        above_cloud = True
        if self.get_param("require_above_cloud"):
            cloud_top = max(senkou_span_a, senkou_span_b)
            above_cloud = current_price > cloud_top

        return rsi_ok and tenkan_kijun_cross and above_cloud
