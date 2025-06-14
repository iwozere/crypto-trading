"""
RSI, Volume, and Supertrend Entry Mixin

This module implements an entry strategy based on the combination of:
1. RSI (Relative Strength Index)
2. Volume analysis
3. Supertrend indicator

The strategy enters a position when:
1. RSI is oversold
2. Volume is above its moving average
3. Supertrend indicator shows a bullish signal

Parameters:
    rsi_period (int): Period for RSI calculation (default: 14)
    rsi_oversold (float): Oversold threshold for RSI (default: 30)
    volume_ma_period (int): Period for volume moving average (default: 20)
    min_volume_ratio (float): Minimum volume ratio compared to MA (default: 1.5)
    supertrend_period (int): Period for ATR calculation in Supertrend (default: 10)
    supertrend_multiplier (float): Multiplier for ATR in Supertrend (default: 3.0)
    use_talib (bool): Whether to use TA-Lib for calculations (default: True)

This strategy combines mean reversion (RSI) with volume confirmation and trend following (Supertrend)
to identify potential reversal points with strong momentum.
"""

from typing import Any, Dict, Optional

import backtrader as bt
import numpy as np
from src.entry.base_entry_mixin import BaseEntryMixin
from src.indicator.talib_rsi import TALibRSI
from src.indicator.talib_atr import TALibATR
from src.indicator.talib_sma import TALibSMA
from src.notification.logger import get_logger

logger = get_logger(__name__)

class RSIVolumeSupertrendEntryMixin(BaseEntryMixin):
    """Entry mixin based on RSI, Volume, and Supertrend"""

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        """Initialize the mixin with parameters"""
        super().__init__(params)
        self.rsi_name = 'entry_rsi'
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
            "rsi_period": 14,
            "rsi_oversold": 30,
            "volume_ma_period": 20,
            "min_volume_ratio": 1.5,
            "supertrend_period": 10,
            "supertrend_multiplier": 3.0,
            "use_talib": True,
        }

    def _init_indicators(self):
        """Initialize RSI, Volume, and Supertrend indicators"""
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
                setattr(self.strategy, self.rsi_name, bt.indicators.RSI(
                    data,
                    period=self.get_param("rsi_period")
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
        Entry logic: RSI oversold, volume above MA, and Supertrend bullish
        """
        if not all(hasattr(self.strategy, name) for name in [self.rsi_name, self.volume_ma_name, self.supertrend_name, self.direction_name]):
            return False

        current_volume = self.strategy.data.volume[0]
        
        rsi = getattr(self.strategy, self.rsi_name)
        vol_ma = getattr(self.strategy, self.volume_ma_name)
        direction = getattr(self.strategy, self.direction_name)

        # Check RSI
        rsi_condition = rsi[0] <= self.get_param("rsi_oversold")

        # Check volume
        volume_ok = current_volume >= vol_ma[0] * self.get_param("min_volume_ratio")

        # Check Supertrend (bullish when price is above Supertrend)
        supertrend_bullish = direction[0] > 0

        return rsi_condition and volume_ok and supertrend_bullish
