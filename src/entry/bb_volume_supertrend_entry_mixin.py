"""
Bollinger Bands, Volume, and Supertrend Entry Mixin

This module implements an entry strategy based on the combination of:
1. Bollinger Bands
2. Volume analysis
3. Supertrend indicator

The strategy enters a position when:
1. Price is below the lower Bollinger Band
2. Volume is above its moving average
3. Supertrend indicates a bullish trend

Parameters:
    bb_period (int): Period for Bollinger Bands calculation (default: 20)
    bb_stddev (float): Standard deviation multiplier for Bollinger Bands (default: 2.0)
    volume_ma_period (int): Period for volume moving average (default: 20)
    supertrend_period (int): Period for Supertrend calculation (default: 10)
    supertrend_multiplier (float): Multiplier for Supertrend ATR (default: 3.0)
    use_bb_touch (bool): Whether to require price touching the lower band (default: True)
    use_talib (bool): Whether to use TA-Lib for calculations (default: True)

This strategy combines mean reversion (BB), volume confirmation, and trend following (Supertrend).
"""

from typing import Any, Dict, Optional

import backtrader as bt
from src.entry.base_entry_mixin import BaseEntryMixin
from src.indicator.talib_bb import TALibBB
from src.indicator.talib_sma import TALibSMA
from src.indicator.super_trend import SuperTrend
from src.notification.logger import setup_logger

logger = setup_logger(__name__)


class BBVolumeSupertrendEntryMixin(BaseEntryMixin):
    """Entry mixin that combines Bollinger Bands, Volume, and Supertrend for entry signals."""

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        """Initialize the mixin with parameters"""
        super().__init__(params)
        self.bb_name = 'entry_bb'
        self.volume_ma_name = 'entry_volume_ma'
        self.supertrend_name = 'entry_supertrend'

    def get_required_params(self) -> list:
        """There are no required parameters - all have default values"""
        return []

    @classmethod
    def get_default_params(cls) -> Dict[str, Any]:
        """Default parameters"""
        return {
            "bb_period": 20,
            "bb_stddev": 2.0,
            "volume_ma_period": 20,
            "supertrend_period": 10,
            "supertrend_multiplier": 3.0,
            "use_bb_touch": True,
        }

    def _init_indicators(self):
        """Initialize indicators"""
        logger.debug("BBVolumeSupertrendEntryMixin._init_indicators called")
        if not hasattr(self, 'strategy'):
            logger.error("No strategy available in _init_indicators")
            return

        try:
            data = self.strategy.data
            use_talib = self.strategy.use_talib
            logger.debug(f"Initializing indicators with use_talib={use_talib}")

            # Calculate required data length based on indicator periods
            required_length = max(
                self.get_param("bb_period"),
                self.get_param("volume_ma_period"),
                self.get_param("supertrend_period")
            )
            logger.debug(f"Required data length: {required_length}, Current data length: {len(data)}")

            # Ensure we have enough data
            if len(data) <= required_length:
                logger.debug(f"Not enough data yet. Need {required_length} bars, have {len(data)}")
                return

            if use_talib:
                # Use TA-Lib for Bollinger Bands
                logger.debug("Creating TA-Lib BB indicator")
                bb = TALibBB(
                    data,
                    period=self.get_param("bb_period"),
                    devfactor=self.get_param("bb_stddev")
                )
                logger.debug("Registering TA-Lib BB indicator")
                self.register_indicator(self.bb_name, bb)

                # Use TA-Lib for Volume MA
                logger.debug("Creating TA-Lib Volume MA indicator")
                vol_ma = TALibSMA(
                    data.volume,
                    period=self.get_param("volume_ma_period")
                )
                logger.debug("Registering TA-Lib Volume MA indicator")
                self.register_indicator(self.volume_ma_name, vol_ma)
            else:
                # Use Backtrader's native Bollinger Bands
                logger.debug("Creating Backtrader BB indicator")
                bb = bt.indicators.BollingerBands(
                    data,
                    period=self.get_param("bb_period"),
                    devfactor=self.get_param("bb_stddev")
                )
                logger.debug("Registering Backtrader BB indicator")
                self.register_indicator(self.bb_name, bb)

                # Use Backtrader's native SMA for Volume
                logger.debug("Creating Backtrader Volume MA indicator")
                vol_ma = bt.indicators.SMA(
                    data.volume,
                    period=self.get_param("volume_ma_period")
                )
                logger.debug("Registering Backtrader Volume MA indicator")
                self.register_indicator(self.volume_ma_name, vol_ma)

            # Create Supertrend indicator (same for both TA-Lib and Backtrader)
            logger.debug("Creating Supertrend indicator")
            supertrend = SuperTrend(
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
        if self.bb_name not in self.indicators or self.volume_ma_name not in self.indicators or self.supertrend_name not in self.indicators:
            return False

        try:
            # Get indicators from mixin's indicators dictionary
            bb = self.indicators[self.bb_name]
            vol_ma = self.indicators[self.volume_ma_name]
            supertrend = self.indicators[self.supertrend_name]
            current_price = self.strategy.data.close[0]
            current_volume = self.strategy.data.volume[0]

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

            # Check Volume
            volume_condition = current_volume > vol_ma[0] * self.get_param("min_volume_ratio")

            # Check Supertrend
            supertrend_condition = supertrend[0] == 1  # 1 means uptrend

            return_value = bb_condition and volume_condition and supertrend_condition
            if return_value:
                logger.debug(f"ENTRY: Price: {current_price}, BB Lower: {bb.bb_lower[0] if self.strategy.use_talib else bb.lines.bot[0]}, Volume: {current_volume}, Volume MA: {vol_ma[0]}, Supertrend: {supertrend[0]}")
            return return_value
        except Exception as e:
            logger.error(f"Error in should_enter: {e}")
            return False
