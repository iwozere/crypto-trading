"""
Bollinger Bands, Volume, and Supertrend Entry Mixin

This module implements an entry strategy based on the combination of:
1. Bollinger Bands
2. Volume analysis
3. Supertrend indicator

The strategy enters a position when:
1. Price touches or crosses below the lower Bollinger Band
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

This strategy combines mean reversion (BB) with volume confirmation and trend following (Supertrend)
to identify potential reversal points with strong momentum.
"""

from typing import Any, Dict, Optional

import backtrader as bt
import numpy as np
from src.entry.base_entry_mixin import BaseEntryMixin
from src.indicator.talib_bb import TALibBB
from src.indicator.talib_sma import TALibSMA
from src.notification.logger import setup_logger

logger = setup_logger()

class BBVolumeSupertrendEntryMixin(BaseEntryMixin):
    """Entry mixin based on Bollinger Bands, Volume, and Supertrend"""

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        super().__init__(params)
        self.bb_name = 'entry_bb'
        self.vol_ma_name = 'entry_vol_ma'
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
            "use_talib": True,
        }

    def _init_indicators(self):
        """Initialize Bollinger Bands, Volume, and Supertrend indicators"""
        if not hasattr(self, 'strategy'):
            return
            
        try:
            data = self.strategy.data
            use_talib = self.get_param("use_talib", True)
            
            if use_talib:
                # Use TA-Lib for Bollinger Bands
                setattr(self.strategy, self.bb_name, TALibBB(
                    data,
                    period=self.get_param("bb_period"),
                    devfactor=self.get_param("bb_stddev")
                ))
                
                # Use TA-Lib for Volume MA
                setattr(self.strategy, self.vol_ma_name, TALibSMA(
                    data.volume,
                    period=self.get_param("volume_ma_period")
                ))
            else:
                # Use Backtrader's native Bollinger Bands
                setattr(self.strategy, self.bb_name, bt.indicators.BollingerBands(
                    data,
                    period=self.get_param("bb_period"),
                    devfactor=self.get_param("bb_stddev")
                ))
                
                # Use Backtrader's native SMA for volume
                setattr(self.strategy, self.vol_ma_name, bt.indicators.SMA(
                    data.volume,
                    period=self.get_param("volume_ma_period")
                ))
            
            # Supertrend is always initialized using Backtrader's native indicator
            setattr(self.strategy, self.supertrend_name, bt.indicators.Supertrend(
                data,
                period=self.get_param("supertrend_period"),
                multiplier=self.get_param("supertrend_multiplier")
            ))
                
        except Exception as e:
            logger.error(f"Error initializing indicators: {str(e)}")
            raise

    def should_enter(self) -> bool:
        """
        Entry logic: Price touching lower BB, volume above MA, and Supertrend bullish
        """
        if not all(hasattr(self.strategy, name) for name in [self.bb_name, self.vol_ma_name, self.supertrend_name]):
            return False

        current_price = self.strategy.data.close[0]
        current_volume = self.strategy.data.volume[0]
        
        bb = getattr(self.strategy, self.bb_name)
        vol_ma = getattr(self.strategy, self.vol_ma_name)
        supertrend = getattr(self.strategy, self.supertrend_name)

        # Check Bollinger Bands
        bb_condition = not self.get_param("use_bb_touch") or current_price <= bb.bb_lower[0] * 1.01  # Small tolerance

        # Check volume
        volume_condition = current_volume > vol_ma[0]

        # Check Supertrend
        supertrend_condition = supertrend.trend[0] == 1  # 1 indicates bullish trend

        return bb_condition and volume_condition and supertrend_condition
