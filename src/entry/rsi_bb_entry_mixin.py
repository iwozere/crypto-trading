"""
RSI and Bollinger Bands Entry Mixin

This module implements an entry strategy based on the combination of:
1. RSI (Relative Strength Index)
2. Bollinger Bands

The strategy enters a position when:
1. RSI is oversold
2. Price is below the lower Bollinger Band

Parameters:
    rsi_period (int): Period for RSI calculation (default: 14)
    rsi_oversold (float): Oversold threshold for RSI (default: 30)
    bb_period (int): Period for Bollinger Bands calculation (default: 20)
    bb_stddev (float): Standard deviation multiplier for Bollinger Bands (default: 2.0)
    use_bb_touch (bool): Whether to require price touching the lower band (default: True)

This strategy combines mean reversion (RSI + BB) to identify potential reversal points.
"""

from typing import Any, Dict, Optional

import backtrader as bt
from src.entry.base_entry_mixin import BaseEntryMixin
from src.indicator.talib_rsi import TALibRSI
from src.indicator.talib_bb import TALibBB
from src.notification.logger import setup_logger

logger = setup_logger(__name__)


class RSIBBEntryMixin(BaseEntryMixin):
    """Entry mixin that combines RSI and Bollinger Bands for entry signals."""

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        """Initialize the mixin with parameters"""
        super().__init__(params)
        self.rsi_name = 'entry_rsi'
        self.bb_name = 'entry_bb'

    def get_required_params(self) -> list:
        """There are no required parameters - all have default values"""
        return []

    @classmethod
    def get_default_params(cls) -> Dict[str, Any]:
        """Default parameters"""
        return {
            "rsi_period": 14,
            "rsi_oversold": 30,
            "bb_period": 20,
            "bb_stddev": 2.0,
            "use_bb_touch": True,
        }

    def _init_indicators(self):
        """Initialize indicators"""
        logger.debug("RSIBBEntryMixin._init_indicators called")
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
                self.get_param("bb_period")
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
                logger.debug(f"RSI indicator registered, indicators dict now has keys: {list(self.indicators.keys())}")

                # Use TA-Lib for Bollinger Bands
                logger.debug("Creating TA-Lib BB indicator")
                bb = TALibBB(
                    data,
                    period=self.get_param("bb_period"),
                    devfactor=self.get_param("bb_stddev")
                )
                logger.debug("Registering TA-Lib BB indicator")
                self.register_indicator(self.bb_name, bb)
                logger.debug(f"BB indicator registered, indicators dict now has keys: {list(self.indicators.keys())}")
            else:
                # Use Backtrader's native RSI
                logger.debug("Creating Backtrader RSI indicator")
                rsi = bt.indicators.RSI(
                    data,
                    period=self.get_param("rsi_period")
                )
                logger.debug("Registering Backtrader RSI indicator")
                self.register_indicator(self.rsi_name, rsi)
                logger.debug(f"RSI indicator registered, indicators dict now has keys: {list(self.indicators.keys())}")

                # Use Backtrader's native Bollinger Bands
                logger.debug("Creating Backtrader BB indicator")
                bb = bt.indicators.BollingerBands(
                    data,
                    period=self.get_param("bb_period"),
                    devfactor=self.get_param("bb_stddev")
                )
                logger.debug("Registering Backtrader BB indicator")
                self.register_indicator(self.bb_name, bb)
                logger.debug(f"BB indicator registered, indicators dict now has keys: {list(self.indicators.keys())}")
        except Exception as e:
            logger.error(f"Error initializing indicators: {e}")
            raise

    def should_enter(self) -> bool:
        """Check if we should enter a position"""
        if not hasattr(self.strategy, self.rsi_name) or not hasattr(self.strategy, self.bb_name):
            return False

        try:
            # Get indicators
            rsi = getattr(self.strategy, self.rsi_name)
            bb = getattr(self.strategy, self.bb_name)
            current_price = self.strategy.data.close[0]

            # Check RSI
            rsi_condition = rsi[0] <= self.get_param("rsi_oversold")

            # Check Bollinger Bands
            if self.strategy.use_talib:
                # For TA-Lib BB, use bb_lower
                if self.get_param("use_bb_touch"):
                    bb_condition = current_price <= bb.bb_lower[0]
                else:
                    bb_condition = current_price < bb.bb_lower[0]
            else:
                # For Backtrader's native BB, use lines.bot
                if self.get_param("use_bb_touch"):
                    bb_condition = current_price <= bb.lines.bot[0]
                else:
                    bb_condition = current_price < bb.lines.bot[0]

            return_value = rsi_condition and bb_condition
            if return_value:
                logger.debug(f"ENTRY: Price: {current_price}, RSI: {rsi[0]}, BB Lower: {bb.bb_lower[0] if self.strategy.use_talib else bb.lines.bot[0]}")
            return return_value
        except Exception as e:
            logger.error(f"Error in should_enter: {e}")
            return False
