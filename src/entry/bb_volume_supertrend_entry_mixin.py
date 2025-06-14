"""
Bollinger Bands, Volume, and Supertrend Entry Mixin

This module implements an entry strategy based on the combination of:
1. Bollinger Bands
2. Volume analysis
3. Supertrend indicator

The strategy enters a position when:
1. Price touches or crosses below the lower Bollinger Band
2. Volume is above its moving average
3. Supertrend indicator shows a bullish signal

Parameters:
    bb_period (int): Period for Bollinger Bands calculation (default: 20)
    bb_stddev (float): Standard deviation multiplier for Bollinger Bands (default: 2.0)
    atr_period (int): Period for ATR calculation (default: 10)
    atr_multiplier (float): Multiplier for ATR in Supertrend (default: 3.0)
    volume_ma_period (int): Period for volume moving average (default: 20)
    min_volume_ratio (float): Minimum volume ratio compared to MA (default: 1.5)
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
from src.indicator.talib_atr import TALibATR
from src.indicator.talib_sma import TALibSMA
from src.notification.logger import get_logger

logger = get_logger(__name__)

class BBVolumeSupertrendEntryMixin(BaseEntryMixin):
    """Entry mixin based on Bollinger Bands, Volume, and Supertrend"""

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        super().__init__(params)
        self.bb_name = 'entry_bb'
        self.volume_ma_name = 'entry_volume_ma'
        self.supertrend_name = 'entry_supertrend'
        self.direction_name = 'entry_direction'

    def get_required_params(self) -> list:
        """There are no required parameters - all have default values"""
        return []

    @classmethod
    def get_default_params(cls) -> Dict[str, Any]:
        """Default parameters"""
        return {
            "bb_period": 20,
            "bb_stddev": 2.0,
            "use_bb_touch": True,
            "volume_ma_period": 20,
            "min_volume": 1.0,
            "supertrend_period": 10,
            "supertrend_multiplier": 3.0,
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
                
                # Use TA-Lib for ATR
                setattr(self.strategy, 'entry_atr', TALibATR(
                    data,
                    period=self.get_param("supertrend_period")
                ))
                
                # Use TA-Lib for Volume MA
                setattr(self.strategy, self.volume_ma_name, TALibSMA(
                    data.volume,
                    period=self.get_param("volume_ma_period")
                ))

                # Calculate Supertrend
                multiplier = self.get_param("supertrend_multiplier")
                atr = getattr(self.strategy, 'entry_atr')

                # Calculate basic upper and lower bands
                hl2 = (data.high + data.low) / 2
                basic_upper = hl2 + (multiplier * atr)
                basic_lower = hl2 - (multiplier * atr)

                # Initialize Supertrend arrays
                supertrend = bt.indicators.SMA(data.close, period=1)
                direction = bt.indicators.SMA(data.close, period=1)

                # Calculate Supertrend values
                for i in range(1, len(data)):
                    if data.close[i] > basic_upper[i - 1]:
                        direction[i] = 1
                    elif data.close[i] < basic_lower[i - 1]:
                        direction[i] = -1
                    else:
                        direction[i] = direction[i - 1]

                    if direction[i] == 1:
                        supertrend[i] = basic_lower[i]
                    else:
                        supertrend[i] = basic_upper[i]

                setattr(self.strategy, self.supertrend_name, supertrend)
                setattr(self.strategy, self.direction_name, direction)
                
            else:
                # Use Backtrader's native indicators
                setattr(self.strategy, self.bb_name, bt.indicators.BollingerBands(
                    data,
                    period=self.get_param("bb_period"),
                    devfactor=self.get_param("bb_stddev")
                ))
                
                setattr(self.strategy, self.volume_ma_name, bt.indicators.SMA(
                    data.volume,
                    period=self.get_param("volume_ma_period")
                ))
                
                # Calculate Supertrend using Backtrader's ATR
                atr = bt.indicators.ATR(
                    data,
                    period=self.get_param("supertrend_period")
                )
                
                # Calculate basic upper and lower bands
                hl2 = (data.high + data.low) / 2
                basic_upper = hl2 + (self.get_param("supertrend_multiplier") * atr)
                basic_lower = hl2 - (self.get_param("supertrend_multiplier") * atr)

                # Initialize Supertrend arrays
                supertrend = bt.indicators.SMA(data.close, period=1)
                direction = bt.indicators.SMA(data.close, period=1)

                # Calculate Supertrend values
                for i in range(1, len(data)):
                    if data.close[i] > basic_upper[i - 1]:
                        direction[i] = 1
                    elif data.close[i] < basic_lower[i - 1]:
                        direction[i] = -1
                    else:
                        direction[i] = direction[i - 1]

                    if direction[i] == 1:
                        supertrend[i] = basic_lower[i]
                    else:
                        supertrend[i] = basic_upper[i]

                setattr(self.strategy, self.supertrend_name, supertrend)
                setattr(self.strategy, self.direction_name, direction)
                
        except Exception as e:
            logger.error(f"Error initializing indicators: {str(e)}")
            raise

    def should_enter(self) -> bool:
        """
        Entry logic: Price touching lower BB, volume above MA, and Supertrend bullish
        """
        if not all(hasattr(self.strategy, name) for name in [self.bb_name, self.volume_ma_name, self.supertrend_name, self.direction_name]):
            return False

        current_price = self.strategy.data.close[0]
        current_volume = self.strategy.data.volume[0]
        
        bb = getattr(self.strategy, self.bb_name)
        vol_ma = getattr(self.strategy, self.volume_ma_name)
        direction = getattr(self.strategy, self.direction_name)

        # Check volume
        volume_ok = current_volume >= vol_ma[0] * self.get_param("min_volume")

        # Check touching the Bollinger Bands (if enabled)
        bb_condition = not self.get_param("use_bb_touch") or current_price <= bb.bb_lower[0] * 1.01  # Small tolerance

        # Check Supertrend (bullish when price is above Supertrend)
        supertrend_bullish = direction[0] > 0

        return volume_ok and bb_condition and supertrend_bullish
