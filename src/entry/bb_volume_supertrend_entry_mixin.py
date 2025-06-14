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
from src.indicator.super_trend import SuperTrend
from src.notification.logger import setup_logger

logger = setup_logger()


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
        if not hasattr(self, 'strategy'):
            return

        try:
            data = self.strategy.data
            use_talib = self.strategy.use_talib

            # Initialize Bollinger Bands
            if use_talib:
                setattr(self.strategy, self.bb_name, TALibBB(
                    data,
                    period=self.get_param("bb_period"),
                    devfactor=self.get_param("bb_stddev")
                ))
            else:
                setattr(self.strategy, self.bb_name, bt.indicators.BollingerBands(
                    data,
                    period=self.get_param("bb_period"),
                    devfactor=self.get_param("bb_stddev")
                ))

            # Initialize Volume MA
            setattr(self.strategy, self.volume_ma_name, bt.indicators.SMA(
                data.volume,
                period=self.get_param("volume_ma_period")
            ))

            # Initialize Supertrend
            setattr(self.strategy, self.supertrend_name, SuperTrend(
                data,
                period=self.get_param("supertrend_period"),
                multiplier=self.get_param("supertrend_multiplier")
            ))
        except Exception as e:
            logger.error(f"Error initializing indicators: {e}")
            raise

    def should_enter(self) -> bool:
        """Check if we should enter a position"""
        if not hasattr(self.strategy, self.bb_name) or \
           not hasattr(self.strategy, self.volume_ma_name) or \
           not hasattr(self.strategy, self.supertrend_name):
            return False

        try:
            # Get indicators
            bb = getattr(self.strategy, self.bb_name)
            volume_ma = getattr(self.strategy, self.volume_ma_name)
            supertrend = getattr(self.strategy, self.supertrend_name)

            # Check Bollinger Bands condition
            if self.get_param("use_bb_touch"):
                bb_condition = self.strategy.data.close[0] <= bb.bb_lower[0]
            else:
                bb_condition = self.strategy.data.close[0] < bb.bb_lower[0]

            # Check Volume condition
            volume_condition = self.strategy.data.volume[0] > volume_ma[0]

            # Check Supertrend condition (bullish trend)
            supertrend_condition = supertrend.trend[0] == 1

            return bb_condition and volume_condition and supertrend_condition
        except Exception as e:
            logger.error(f"Error in should_enter: {e}")
            return False
