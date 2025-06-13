"""
RSI + Ichimoku Entry Mixin
-------------------------

This module implements an entry strategy based on RSI and Ichimoku Cloud.
The strategy enters a position when:
1. RSI is in the oversold zone (below rsi_oversold)
2. Price is above the Ichimoku Cloud (if require_above_cloud is True)
3. Tenkan-sen crosses above Kijun-sen (if require_crossover is True)

Parameters:
-----------
rsi_period : int
    Period for RSI calculation (default: 14)
rsi_oversold : float
    RSI level considered oversold (default: 30)
tenkan_period : int
    Period for Tenkan-sen calculation (default: 9)
kijun_period : int
    Period for Kijun-sen calculation (default: 26)
senkou_span_b_period : int
    Period for Senkou Span B calculation (default: 52)
displacement : int
    Displacement for Ichimoku Cloud (default: 26)
require_above_cloud : bool
    Whether to require price above cloud (default: True)
require_crossover : bool
    Whether to require Tenkan-sen/Kijun-sen crossover (default: True)
"""

from typing import Any, Dict

import backtrader as bt
import numpy as np
from src.entry.entry_mixin import BaseEntryMixin


class RSIIchimokuEntryMixin(BaseEntryMixin):
    """Entry mixin combining RSI and Ichimoku Cloud indicators"""

    params = {
        "rsi_period": 14,
        "rsi_oversold": 30,
        "tenkan_period": 9,
        "kijun_period": 26,
        "senkou_span_b_period": 52,
        "displacement": 26,
        "require_above_cloud": True,
        "require_crossover": True,
    }

    def get_required_params(self) -> list:
        """There are no required parameters - all have default values"""
        return []

    def get_default_params(self) -> dict:
        """Default parameters"""
        return {
            "rsi_period": 14,
            "rsi_oversold": 30,
            "tenkan_period": 9,
            "kijun_period": 26,
            "senkou_span_b_period": 52,
            "displacement": 26,
            "require_above_cloud": True,
            "require_crossover": True,
        }

    def _init_indicators(self):
        """Initialize RSI and Ichimoku Cloud indicators"""
        if self.strategy is None:
            raise ValueError("Strategy must be set before initializing indicators")

        # Initialize RSI based on use_talib flag
        if self.get_param("use_talib"):
            try:
                import talib
                # Convert data to numpy arrays
                close_data = np.array(self.strategy.data.close.get(size=len(self.strategy.data)))
                
                # Create RSI using TA-Lib
                rsi_values = talib.RSI(
                    close_data,
                    timeperiod=self.get_param("rsi_period")
                )
                self.indicators["rsi"] = bt.indicators.RSI(
                    self.strategy.data.close,
                    period=self.get_param("rsi_period"),
                    plot=False
                )
                # Update RSI values one by one
                for i, value in enumerate(rsi_values):
                    if i < len(self.indicators["rsi"].lines[0]):
                        self.indicators["rsi"].lines[0][i] = value
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

        # Initialize Ichimoku Cloud indicators
        self.indicators["ichimoku"] = bt.indicators.Ichimoku(
            self.strategy.data,
            tenkan_period=self.get_param("tenkan_period"),
            kijun_period=self.get_param("kijun_period"),
            senkou_span_b_period=self.get_param("senkou_span_b_period"),
            displacement=self.get_param("displacement")
        )

    def should_enter(self):
        """Check if we should enter a position"""
        if not self.indicators:
            return False

        # Check RSI condition
        rsi_oversold = self.indicators["rsi"][0] < self.get_param("rsi_oversold")
        
        # Check Ichimoku conditions
        ichimoku = self.indicators["ichimoku"]
        current_price = self.strategy.data.close[0]
        
        # Check if price is above cloud
        above_cloud = True
        if self.get_param("require_above_cloud"):
            above_cloud = (
                current_price > ichimoku.lines.senkou_span_a[0] and
                current_price > ichimoku.lines.senkou_span_b[0]
            )
        
        # Check for Tenkan-sen/Kijun-sen crossover
        crossover = True
        if self.get_param("require_crossover"):
            crossover = (
                ichimoku.lines.tenkan_sen[-1] < ichimoku.lines.kijun_sen[-1] and
                ichimoku.lines.tenkan_sen[0] > ichimoku.lines.kijun_sen[0]
            )
        
        return rsi_oversold and above_cloud and crossover
