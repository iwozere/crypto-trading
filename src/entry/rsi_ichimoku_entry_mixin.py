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
import numpy as np
from src.entry.base_entry_mixin import BaseEntryMixin
from src.indicator.talib_rsi import TALibRSI
from src.indicator.ichimoku import Ichimoku
from src.notification.logger import setup_logger

logger = setup_logger(__name__)

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
        }

    def _init_indicators(self):
        """Initialize indicators"""
        logger.debug("RSIIchimokuEntryMixin._init_indicators called")
        if not hasattr(self, 'strategy'):
            logger.error("No strategy available in _init_indicators")
            return

        try:
            data = self.strategy.data
            use_talib = self.strategy.use_talib
            logger.debug(f"Initializing indicators with use_talib={use_talib}")

            # Calculate required data length based on indicator periods
            required_length = max(
                self.get_param("rsi_period"),
                self.get_param("tenkan_period"),
                self.get_param("kijun_period"),
                self.get_param("senkou_span_b_period")
            )
            logger.debug(f"Required data length: {required_length}, Current data length: {len(data)}")

            # Ensure we have enough data
            if len(data) <= required_length:
                logger.debug(f"Not enough data yet. Need {required_length} bars, have {len(data)}")
                return

            if use_talib:
                # Use TA-Lib for RSI
                logger.debug("Creating TA-Lib RSI indicator")
                rsi = TALibRSI(
                    data,
                    period=self.get_param("rsi_period")
                )
                logger.debug("Registering TA-Lib RSI indicator")
                self.register_indicator(self.rsi_name, rsi)

                # Use TA-Lib for Ichimoku
                logger.debug("Creating TA-Lib Ichimoku indicator")
                ichimoku = TALibIchimoku(
                    data,
                    tenkan_period=self.get_param("tenkan_period"),
                    kijun_period=self.get_param("kijun_period"),
                    senkou_span_b_period=self.get_param("senkou_span_b_period")
                )
                logger.debug("Registering TA-Lib Ichimoku indicator")
                self.register_indicator(self.ichimoku_name, ichimoku)
            else:
                # Use Backtrader's native RSI
                logger.debug("Creating Backtrader RSI indicator")
                rsi = bt.indicators.RSI(
                    data,
                    period=self.get_param("rsi_period")
                )
                logger.debug("Registering Backtrader RSI indicator")
                self.register_indicator(self.rsi_name, rsi)

                # Use Backtrader's native Ichimoku
                logger.debug("Creating Backtrader Ichimoku indicator")
                ichimoku = bt.indicators.Ichimoku(
                    data,
                    tenkan_period=self.get_param("tenkan_period"),
                    kijun_period=self.get_param("kijun_period"),
                    senkou_span_b_period=self.get_param("senkou_span_b_period")
                )
                logger.debug("Registering Backtrader Ichimoku indicator")
                self.register_indicator(self.ichimoku_name, ichimoku)
        except Exception as e:
            logger.error(f"Error initializing indicators: {e}")
            raise

    def should_enter(self) -> bool:
        """
        Entry logic: RSI oversold and Ichimoku Cloud conditions
        """
        if not all(hasattr(self.strategy, name) for name in [self.rsi_name, self.ichimoku_name]):
            return False

        current_price = self.strategy.data.close[0]
        
        rsi = getattr(self.strategy, self.rsi_name)
        ichimoku = getattr(self.strategy, self.ichimoku_name)

        # Check RSI
        rsi_condition = rsi[0] <= self.get_param("rsi_oversold")

        # Check Ichimoku Cloud conditions
        # Price below cloud
        below_cloud = current_price < ichimoku.senkou_span_a[0] and current_price < ichimoku.senkou_span_b[0]
        
        # Tenkan-sen crosses above Kijun-sen
        tenkan_cross = ichimoku.tenkan_sen[0] > ichimoku.kijun_sen[0] and ichimoku.tenkan_sen[-1] <= ichimoku.kijun_sen[-1]

        return_value = rsi_condition and below_cloud and tenkan_cross
        if return_value:
            logger.debug(f"ENTRY: Price: {current_price}, RSI: {rsi[0]}, "
                       f"Tenkan: {ichimoku.tenkan_sen[0]}, Kijun: {ichimoku.kijun_sen[0]}, "
                       f"Senkou A: {ichimoku.senkou_span_a[0]}, Senkou B: {ichimoku.senkou_span_b[0]}")
        return return_value
