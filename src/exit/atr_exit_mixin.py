"""
ATR Exit Mixin
-------------

This module implements an exit strategy based on Average True Range (ATR).
The strategy exits a position when the price moves against the position by more than ATR multiplied by a specified multiplier.

Parameters:
-----------
atr_period : int
    Period for ATR calculation (default: 14)
atr_multiplier : float
    Multiplier for ATR to determine exit threshold (default: 2.0)
use_talib : bool
    Whether to use TA-Lib for calculations (default: True)
"""

import backtrader as bt
import numpy as np
from src.exit.base_exit_mixin import BaseExitMixin
from typing import Dict, Any, Optional
from src.notification.logger import setup_logger
from src.indicator.talib_atr import TALibATR

logger = setup_logger(__name__)

class ATRExitMixin(BaseExitMixin):
    """Exit mixin based on ATR"""

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        """Initialize the mixin with parameters"""
        super().__init__(params)
        self.atr_name = 'exit_atr'

    def get_required_params(self) -> list:
        """There are no required parameters - all have default values"""
        return []

    @classmethod
    def get_default_params(cls) -> Dict[str, Any]:
        """Default parameters"""
        return {
            "atr_period": 14,
            "atr_multiplier": 2.0,
        }

    def _init_indicators(self):
        """Initialize indicators"""
        logger.debug("ATRExitMixin._init_indicators called")
        if not hasattr(self, 'strategy'):
            logger.error("No strategy available in _init_indicators")
            return

        try:
            data = self.strategy.data
            use_talib = self.strategy.use_talib
            logger.debug(f"Initializing indicators with use_talib={use_talib}")

            # Calculate required data length based on indicator periods
            required_length = self.get_param("atr_period")
            logger.debug(f"Required data length: {required_length}, Current data length: {len(data)}")

            # Ensure we have enough data
            if len(data) <= required_length:
                logger.debug(f"Not enough data yet. Need {required_length} bars, have {len(data)}")
                return

            if use_talib:
                # Use TA-Lib for ATR
                logger.debug("Creating TA-Lib ATR indicator")
                atr = TALibATR(
                    data,
                    period=self.get_param("atr_period")
                )
                logger.debug("Registering TA-Lib ATR indicator")
                self.register_indicator(self.atr_name, atr)
                logger.debug(f"ATR indicator registered, indicators dict now has keys: {list(self.indicators.keys())}")
            else:
                # Use Backtrader's native ATR
                logger.debug("Creating Backtrader ATR indicator")
                atr = bt.indicators.ATR(
                    data,
                    period=self.get_param("atr_period")
                )
                logger.debug("Registering Backtrader ATR indicator")
                self.register_indicator(self.atr_name, atr)
                logger.debug(f"ATR indicator registered, indicators dict now has keys: {list(self.indicators.keys())}")
        except Exception as e:
            logger.error(f"Error initializing indicators: {e}")
            raise

    def should_exit(self) -> bool:
        """Check if we should exit a position"""
        if not self.are_indicators_ready():
            return False

        try:
            # Get indicator from mixin's indicators dictionary
            atr = self.indicators[self.atr_name]
            atr_val = atr[0] if hasattr(atr, '__getitem__') else atr.lines.atr[0]
            current_price = self.strategy.data.close[0]
            stop_loss = current_price - (atr_val * self.get_param("atr_multiplier"))
            
            return_value = current_price < stop_loss
            if return_value:
                logger.debug(f"EXIT: Price: {current_price}, Stop Loss: {stop_loss}, "
                           f"ATR: {atr_val}, ATR Multiplier: {self.get_param('atr_multiplier')}")
            return return_value
        except Exception as e:
            logger.error(f"Error in should_exit: {e}")
            return False

    def get_exit_reason(self) -> str:
        """Get the reason for exiting the position"""
        if not self.strategy.position:
            return "unknown"
        return "atr_stop_loss"
