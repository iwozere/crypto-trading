"""
RSI and Ichimoku Cloud Entry Mixin

This module implements an entry strategy based on the combination of:
1. RSI (Relative Strength Index)
2. Ichimoku Cloud

The strategy enters a position when:
1. RSI is oversold
2. Price is above the Ichimoku Cloud
3. Tenkan-sen (Conversion Line) crosses above Kijun-sen (Base Line)

Parameters:
    rsi_period (int): Period for RSI calculation (default: 14)
    rsi_oversold (float): Oversold threshold for RSI (default: 30)
    tenkan_period (int): Period for Tenkan-sen calculation (default: 9)
    kijun_period (int): Period for Kijun-sen calculation (default: 26)
    senkou_span_b_period (int): Period for Senkou Span B calculation (default: 52)
    displacement (int): Displacement for Senkou Span A and B (default: 26)
    use_talib (bool): Whether to use TA-Lib for calculations (default: True)

This strategy combines mean reversion (RSI) with trend following (Ichimoku Cloud)
to identify potential reversal points in trending markets.
"""

from typing import Any, Dict, Optional

import backtrader as bt
import numpy as np
from src.entry.base_entry_mixin import BaseEntryMixin
from src.indicator.talib_rsi import TALibRSI
from src.notification.logger import get_logger

logger = get_logger(__name__)

class RSIIchimokuEntryMixin(BaseEntryMixin):
    """Entry mixin based on RSI and Ichimoku Cloud"""

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        super().__init__(params)
        self.rsi_name = 'entry_rsi'
        self.ichimoku_name = 'entry_ichimoku'

    def get_required_params(self) -> list:
        """There are no required parameters - all have default values"""
        return []

    @classmethod
    def get_default_params(cls) -> Dict[str, Any]:
        """Default parameters"""
        return {
            "rsi_period": 14,
            "rsi_oversold": 30,
            "tenkan_period": 9,
            "kijun_period": 26,
            "senkou_span_b_period": 52,
            "displacement": 26,
            "use_talib": True,
        }

    def _init_indicators(self):
        """Initialize RSI and Ichimoku Cloud indicators"""
        if not hasattr(self, 'strategy'):
            return
            
        try:
            data = self.strategy.data
            use_talib = self.get_param("use_talib", True)
            
            if use_talib:
                # Use TA-Lib for RSI
                setattr(self.strategy, self.rsi_name, TALibRSI(
                    data,
                    period=self.get_param("rsi_period")
                ))
                
                # Calculate Ichimoku Cloud
                ichimoku = bt.indicators.Ichimoku(
                    data,
                    tenkan_period=self.get_param("tenkan_period"),
                    kijun_period=self.get_param("kijun_period"),
                    senkou_span_b_period=self.get_param("senkou_span_b_period"),
                    displacement=self.get_param("displacement")
                )
                setattr(self.strategy, self.ichimoku_name, ichimoku)
                
            else:
                # Use Backtrader's native indicators
                setattr(self.strategy, self.rsi_name, bt.indicators.RSI(
                    data,
                    period=self.get_param("rsi_period")
                ))
                
                setattr(self.strategy, self.ichimoku_name, bt.indicators.Ichimoku(
                    data,
                    tenkan_period=self.get_param("tenkan_period"),
                    kijun_period=self.get_param("kijun_period"),
                    senkou_span_b_period=self.get_param("senkou_span_b_period"),
                    displacement=self.get_param("displacement")
                ))
                
        except Exception as e:
            logger.error(f"Error initializing indicators: {str(e)}")
            raise

    def should_enter(self) -> bool:
        """
        Entry logic: RSI oversold, price above cloud, and bullish crossover
        """
        if not all(hasattr(self.strategy, name) for name in [self.rsi_name, self.ichimoku_name]):
            return False

        current_price = self.strategy.data.close[0]
        
        rsi = getattr(self.strategy, self.rsi_name)
        ichimoku = getattr(self.strategy, self.ichimoku_name)

        # Check RSI
        rsi_condition = rsi[0] <= self.get_param("rsi_oversold")

        # Check price position relative to cloud
        cloud_condition = current_price > max(ichimoku.senkou_span_a[0], ichimoku.senkou_span_b[0])

        # Check for bullish crossover
        crossover_condition = (ichimoku.tenkan_sen[0] > ichimoku.kijun_sen[0] and 
                             ichimoku.tenkan_sen[-1] <= ichimoku.kijun_sen[-1])

        return rsi_condition and cloud_condition and crossover_condition
