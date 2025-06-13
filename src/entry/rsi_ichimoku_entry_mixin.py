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
from src.entry.base_entry_mixin import BaseEntryMixin


class RSIIchimokuEntryMixin(BaseEntryMixin):
    """Entry mixin based on RSI and Ichimoku Cloud"""

    def __init__(self, params=None):
        """Initialize the mixin with parameters"""
        super().__init__()
        self.params = params or self.get_default_params()

    def get_required_params(self) -> list:
        """There are no required parameters - all have default values"""
        return []

    @classmethod
    def get_default_params(cls) -> Dict[str, Any]:
        """Default parameters"""
        return {
            "rsi_period": 14,
            "rsi_oversold": 30,
            "ichimoku_tenkan": 9,
            "ichimoku_kijun": 26,
            "ichimoku_senkou_span_b": 52,
            "ichimoku_displacement": 26,
        }

    def _init_indicators(self):
        """Initialize RSI and Ichimoku Cloud indicators"""
        if not hasattr(self, 'strategy'):
            return
            
        # Initialize RSI if not already initialized
        if not hasattr(self.strategy, 'rsi'):
            # Check if TA-Lib should be used based on strategy settings
            use_talib = getattr(self.strategy, 'use_talib', False)
            
            if use_talib:
                try:
                    import talib
                    # Calculate RSI using TA-Lib
                    close_prices = np.array([self.strategy.data.close[i] for i in range(len(self.strategy.data))])
                    rsi_values = talib.RSI(close_prices, timeperiod=self.params["rsi_period"])
                    
                    # Initialize Backtrader RSI
                    self.strategy.rsi = bt.indicators.RSI(
                        self.strategy.data,
                        period=self.params["rsi_period"]
                    )
                    
                    # Update RSI values one by one
                    for i in range(len(self.strategy.data)):
                        if i < len(rsi_values):
                            self.strategy.rsi.array[i] = rsi_values[i]
                except ImportError:
                    self.strategy.logger.warning("TA-Lib not available, using Backtrader's RSI")
                    self.strategy.rsi = bt.indicators.RSI(
                        self.strategy.data,
                        period=self.params["rsi_period"]
                    )
            else:
                self.strategy.rsi = bt.indicators.RSI(
                    self.strategy.data,
                    period=self.params["rsi_period"]
                )
        
        # Initialize Ichimoku Cloud
        use_talib = getattr(self.strategy, 'use_talib', False)
        if use_talib:
            try:
                import talib
                # Calculate Ichimoku Cloud using TA-Lib
                high_prices = np.array([self.strategy.data.high[i] for i in range(len(self.strategy.data))])
                low_prices = np.array([self.strategy.data.low[i] for i in range(len(self.strategy.data))])
                
                # Calculate Tenkan-sen (Conversion Line)
                tenkan_high = talib.MAX(high_prices, timeperiod=self.params["ichimoku_tenkan"])
                tenkan_low = talib.MIN(low_prices, timeperiod=self.params["ichimoku_tenkan"])
                tenkan_sen = (tenkan_high + tenkan_low) / 2
                
                # Calculate Kijun-sen (Base Line)
                kijun_high = talib.MAX(high_prices, timeperiod=self.params["ichimoku_kijun"])
                kijun_low = talib.MIN(low_prices, timeperiod=self.params["ichimoku_kijun"])
                kijun_sen = (kijun_high + kijun_low) / 2
                
                # Calculate Senkou Span A (Leading Span A)
                senkou_span_a = (tenkan_sen + kijun_sen) / 2
                
                # Calculate Senkou Span B (Leading Span B)
                senkou_span_b_high = talib.MAX(high_prices, timeperiod=self.params["ichimoku_senkou_span_b"])
                senkou_span_b_low = talib.MIN(low_prices, timeperiod=self.params["ichimoku_senkou_span_b"])
                senkou_span_b = (senkou_span_b_high + senkou_span_b_low) / 2
                
                # Initialize Backtrader Ichimoku Cloud
                self.strategy.ichimoku = bt.indicators.Ichimoku(
                    self.strategy.data,
                    tenkan=self.params["ichimoku_tenkan"],
                    kijun=self.params["ichimoku_kijun"],
                    senkou=self.params["ichimoku_senkou_span_b"],
                    displacement=self.params["ichimoku_displacement"]
                )
                
                # Update Ichimoku values one by one
                for i in range(len(self.strategy.data)):
                    if i < len(tenkan_sen):
                        self.strategy.ichimoku.lines.tenkan_sen[i] = tenkan_sen[i]
                        self.strategy.ichimoku.lines.kijun_sen[i] = kijun_sen[i]
                        self.strategy.ichimoku.lines.senkou_span_a[i] = senkou_span_a[i]
                        self.strategy.ichimoku.lines.senkou_span_b[i] = senkou_span_b[i]
            except ImportError:
                self.strategy.logger.warning("TA-Lib not available, using Backtrader's Ichimoku Cloud")
                self.strategy.ichimoku = bt.indicators.Ichimoku(
                    self.strategy.data,
                    tenkan=self.params["ichimoku_tenkan"],
                    kijun=self.params["ichimoku_kijun"],
                    senkou=self.params["ichimoku_senkou_span_b"],
                    displacement=self.params["ichimoku_displacement"]
                )
        else:
            self.strategy.ichimoku = bt.indicators.Ichimoku(
                self.strategy.data,
                tenkan=self.params["ichimoku_tenkan"],
                kijun=self.params["ichimoku_kijun"],
                senkou=self.params["ichimoku_senkou_span_b"],
                displacement=self.params["ichimoku_displacement"]
            )

    def should_enter(self) -> bool:
        """Check if we should enter a position"""
        if not hasattr(self.strategy, 'rsi') or not hasattr(self.strategy, 'ichimoku'):
            return False

        # Check RSI condition
        rsi_oversold = self.strategy.rsi[0] < self.params["rsi_oversold"]
        
        # Check Ichimoku Cloud conditions
        ichimoku = self.strategy.ichimoku
        current_price = self.strategy.data.close[0]
        
        # Check if price is below the cloud
        below_cloud = current_price < min(ichimoku.lines.senkou_span_a[0], ichimoku.lines.senkou_span_b[0])
        
        # Check if Tenkan-sen crosses above Kijun-sen (bullish signal)
        tenkan_cross = (ichimoku.lines.tenkan_sen[-1] < ichimoku.lines.kijun_sen[-1] and
                       ichimoku.lines.tenkan_sen[0] > ichimoku.lines.kijun_sen[0])
        
        return rsi_oversold and below_cloud and tenkan_cross

        # Check if price is above cloud
        above_cloud = True
        if self.p.require_above_cloud:
            above_cloud = (
                current_price > ichimoku.lines.senkou_span_a[0] and
                current_price > ichimoku.lines.senkou_span_b[0]
            )
        
        # Check for Tenkan-sen/Kijun-sen crossover
        crossover = True
        if self.p.require_crossover:
            crossover = (
                ichimoku.lines.tenkan_sen[-1] < ichimoku.lines.kijun_sen[-1] and
                ichimoku.lines.tenkan_sen[0] > ichimoku.lines.kijun_sen[0]
            )
        
        return rsi_oversold and above_cloud and crossover
