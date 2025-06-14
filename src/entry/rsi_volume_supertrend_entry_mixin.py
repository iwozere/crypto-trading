"""
RSI, Volume, and Supertrend Entry Mixin

This module implements an entry strategy based on the combination of:
1. RSI (Relative Strength Index)
2. Volume analysis
3. Supertrend indicator

The strategy enters a position when:
1. RSI is oversold
2. Volume is above its moving average
3. Supertrend indicates a bullish trend

Parameters:
    rsi_period (int): Period for RSI calculation (default: 14)
    rsi_oversold (float): Oversold threshold for RSI (default: 30)
    volume_ma_period (int): Period for volume moving average (default: 20)
    supertrend_period (int): Period for Supertrend calculation (default: 10)
    supertrend_multiplier (float): Multiplier for Supertrend ATR (default: 3.0)

This strategy combines mean reversion (RSI) with volume confirmation and trend following (Supertrend)
to identify potential reversal points with strong momentum.
"""

from typing import Any, Dict, Optional

import backtrader as bt
import numpy as np
from src.entry.base_entry_mixin import BaseEntryMixin
from src.indicator.talib_rsi import TALibRSI
from src.indicator.talib_sma import TALibSMA
from src.notification.logger import setup_logger

logger = setup_logger(__name__)

class RSIVolumeSupertrendEntryMixin(BaseEntryMixin):
    """Entry mixin based on RSI, Volume, and Supertrend"""

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        """Initialize the mixin with parameters"""
        super().__init__(params)
        self.rsi_name = 'entry_rsi'
        self.vol_ma_name = 'entry_volume_ma'
        self.supertrend_name = 'entry_supertrend'
        self.direction_name = 'entry_direction'

    def get_required_params(self) -> list:
        """There are no required parameters - all have default values"""
        return []

    @classmethod
    def get_default_params(cls) -> Dict[str, Any]:
        """Default parameters"""
        return {
            "rsi_period": 14,
            "rsi_oversold": 30,
            "volume_ma_period": 20,
            "min_volume_ratio": 1.5,
            "supertrend_period": 10,
            "supertrend_multiplier": 3.0,
        }

    def _init_indicators(self):
        """Initialize indicators"""
        logger.debug("RSIVolumeSupertrendEntryMixin._init_indicators called")
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
                self.get_param("volume_ma_period"),
                self.get_param("supertrend_period")
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

                # Use TA-Lib for Volume MA
                logger.debug("Creating TA-Lib Volume MA indicator")
                vol_ma = TALibSMA(
                    data.volume,
                    period=self.get_param("volume_ma_period")
                )
                logger.debug("Registering TA-Lib Volume MA indicator")
                self.register_indicator(self.vol_ma_name, vol_ma)
            else:
                # Use Backtrader's native RSI
                logger.debug("Creating Backtrader RSI indicator")
                rsi = bt.indicators.RSI(
                    data,
                    period=self.get_param("rsi_period")
                )
                logger.debug("Registering Backtrader RSI indicator")
                self.register_indicator(self.rsi_name, rsi)

                # Use Backtrader's native SMA for Volume
                logger.debug("Creating Backtrader Volume MA indicator")
                vol_ma = bt.indicators.SMA(
                    data.volume,
                    period=self.get_param("volume_ma_period")
                )
                logger.debug("Registering Backtrader Volume MA indicator")
                self.register_indicator(self.vol_ma_name, vol_ma)

            # Create Supertrend indicator (same for both TA-Lib and Backtrader)
            logger.debug("Creating Supertrend indicator")
            supertrend = bt.indicators.Supertrend(
                data,
                period=self.get_param("supertrend_period"),
                multiplier=self.get_param("supertrend_multiplier")
            )
            logger.debug("Registering Supertrend indicator")
            self.register_indicator(self.supertrend_name, supertrend)
        except Exception as e:
            logger.error(f"Error initializing indicators: {e}")
            raise

    def should_enter(self) -> bool:
        """Check if we should enter a position"""
        if self.rsi_name not in self.indicators or self.vol_ma_name not in self.indicators or self.supertrend_name not in self.indicators:
            return False

        try:
            # Get indicators from mixin's indicators dictionary
            rsi = self.indicators[self.rsi_name]
            vol_ma = self.indicators[self.vol_ma_name]
            supertrend = self.indicators[self.supertrend_name]
            current_price = self.strategy.data.close[0]
            current_volume = self.strategy.data.volume[0]

            # Check RSI
            rsi_condition = rsi[0] <= self.get_param("rsi_oversold")

            # Check Volume
            volume_condition = current_volume > vol_ma[0] * self.get_param("min_volume_ratio")

            # Check Supertrend
            supertrend_condition = supertrend[0] == 1  # 1 means uptrend

            return_value = rsi_condition and volume_condition and supertrend_condition
            if return_value:
                logger.debug(f"ENTRY: Price: {current_price}, RSI: {rsi[0]}, Volume: {current_volume}, Volume MA: {vol_ma[0]}, Supertrend: {supertrend[0]}")
            return return_value
        except Exception as e:
            logger.error(f"Error in should_enter: {e}")
            return False
