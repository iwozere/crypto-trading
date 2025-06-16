"""
RSI and Ichimoku Cloud Entry Mixin

This module implements an entry strategy based on the combination of:
1. RSI (Relative Strength Index)
2. Ichimoku Cloud

The strategy enters a position when:
1. RSI is oversold
2. Price is below the Ichimoku Cloud
3. Tenkan-sen (Conversion Line) crosses above Kijun-sen (Base Line)

Parameters:
    rsi_period (int): Period for RSI calculation (default: 14)
    rsi_oversold (float): Oversold threshold for RSI (default: 30)
    tenkan_period (int): Period for Tenkan-sen calculation (default: 9)
    kijun_period (int): Period for Kijun-sen calculation (default: 26)
    senkou_span_b_period (int): Period for Senkou Span B calculation (default: 52)

This strategy combines mean reversion (RSI) with trend following (Ichimoku) to identify potential reversal points.
"""

from typing import Any, Dict, Optional

import backtrader as bt
from src.entry.base_entry_mixin import BaseEntryMixin
from src.notification.logger import setup_logger
from src.indicator.ichimoku import Ichimoku

logger = setup_logger(__name__)

class RSIIchimokuEntryMixin(BaseEntryMixin):
    """Entry mixin based on RSI and Ichimoku Cloud"""

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        super().__init__(params)
        self.rsi_name = 'entry_rsi'
        self.ichimoku_name = 'entry_ichimoku'
        self.rsi = None
        self.ichimoku = None

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
        }

    def _init_indicators(self):
        """Initialize indicators"""
        logger.debug("RSIIchimokuEntryMixin._init_indicators called")
        if not hasattr(self, 'strategy'):
            logger.error("No strategy available in _init_indicators")
            return

        try:
            rsi_period = self.get_param("rsi_period")
            if self.strategy.use_talib:
                self.rsi = bt.talib.RSI(self.strategy.data.close, period=rsi_period)
            else:
                self.rsi = bt.indicators.RSI(self.strategy.data.close, period=rsi_period)

            self.register_indicator(self.rsi_name, self.rsi)

            self.ichimoku = Ichimoku(
                self.strategy.data,
                tenkan_period=self.get_param("tenkan_period"),
                kijun_period=self.get_param("kijun_period"),
                senkou_span_b_period=self.get_param("senkou_span_b_period")
            )
            self.register_indicator(self.ichimoku_name, self.ichimoku)
        except Exception as e:
            logger.error(f"Error initializing indicators: {e}", exc_info=e)
            raise

    def should_enter(self) -> bool:
        """Check if we should enter a position"""
        if self.rsi_name not in self.indicators or self.ichimoku_name not in self.indicators:
            return False

        try:
            # Get indicators from mixin's indicators dictionary
            rsi = self.indicators[self.rsi_name]
            ichimoku = self.indicators[self.ichimoku_name]
            current_price = self.strategy.data.close[0]

            # Check RSI
            rsi_condition = rsi[0] <= self.get_param("rsi_oversold")

            # Check Ichimoku Cloud
            ichimoku_condition = current_price > ichimoku.senkou_span_a[0] and current_price > ichimoku.senkou_span_b[0]

            return_value = rsi_condition and ichimoku_condition
            if return_value:
                logger.debug(f"ENTRY: Price: {current_price}, RSI: {rsi[0]}, Ichimoku Span A: {ichimoku.senkou_span_a[0]}, Ichimoku Span B: {ichimoku.senkou_span_b[0]}")
            return return_value
        except Exception as e:
            logger.error(f"Error in should_enter: {e}", exc_info=e)
            return False
