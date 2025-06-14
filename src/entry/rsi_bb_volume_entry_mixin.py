"""
RSI, Bollinger Bands, and Volume Entry Mixin

This module implements an entry strategy based on the combination of:
1. RSI (Relative Strength Index)
2. Bollinger Bands
3. Volume analysis

The strategy enters a position when:
1. RSI is oversold
2. Price touches or crosses below the lower Bollinger Band
3. Volume is above its moving average

Parameters:
    rsi_period (int): Period for RSI calculation (default: 14)
    rsi_oversold (float): Oversold threshold for RSI (default: 30)
    bb_period (int): Period for Bollinger Bands calculation (default: 20)
    bb_stddev (float): Standard deviation multiplier for Bollinger Bands (default: 2.0)
    volume_ma_period (int): Period for volume moving average (default: 20)
    min_volume_ratio (float): Minimum volume ratio compared to MA (default: 1.5)
    use_bb_touch (bool): Whether to require price touching the lower band (default: True)
    use_talib (bool): Whether to use TA-Lib for calculations (default: True)

This strategy combines mean reversion (RSI + BB) with volume confirmation
to identify potential reversal points with strong momentum.
"""

from typing import Any, Dict, Optional

import backtrader as bt
import numpy as np
from src.entry.base_entry_mixin import BaseEntryMixin
from src.indicator.talib_rsi import TALibRSI
from src.indicator.talib_bb import TALibBB
from src.indicator.talib_sma import TALibSMA
from src.notification.logger import get_logger

logger = get_logger(__name__)

class RSIBBVolumeEntryMixin(BaseEntryMixin):
    """Entry mixin based on RSI, Bollinger Bands, and Volume"""

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        super().__init__(params)
        self.rsi_name = 'entry_rsi'
        self.bb_name = 'entry_bb'
        self.volume_ma_name = 'entry_volume_ma'

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
            "volume_ma_period": 20,
            "min_volume_ratio": 1.5,
            "use_bb_touch": True,
            "use_talib": True,
        }

    def _init_indicators(self):
        """Initialize RSI, Bollinger Bands, and Volume indicators"""
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
                
                # Use TA-Lib for Bollinger Bands
                setattr(self.strategy, self.bb_name, TALibBB(
                    data,
                    period=self.get_param("bb_period"),
                    devfactor=self.get_param("bb_stddev")
                ))
                
                # Use TA-Lib for Volume MA
                setattr(self.strategy, self.volume_ma_name, TALibSMA(
                    data.volume,
                    period=self.get_param("volume_ma_period")
                ))
                
            else:
                # Use Backtrader's native indicators
                setattr(self.strategy, self.rsi_name, bt.indicators.RSI(
                    data,
                    period=self.get_param("rsi_period")
                ))
                
                setattr(self.strategy, self.bb_name, bt.indicators.BollingerBands(
                    data,
                    period=self.get_param("bb_period"),
                    devfactor=self.get_param("bb_stddev")
                ))
                
                setattr(self.strategy, self.volume_ma_name, bt.indicators.SMA(
                    data.volume,
                    period=self.get_param("volume_ma_period")
                ))
                
        except Exception as e:
            logger.error(f"Error initializing indicators: {str(e)}")
            raise

    def should_enter(self) -> bool:
        """
        Entry logic: RSI oversold, price touching lower BB, and volume above MA
        """
        if not all(hasattr(self.strategy, name) for name in [self.rsi_name, self.bb_name, self.volume_ma_name]):
            return False

        current_price = self.strategy.data.close[0]
        current_volume = self.strategy.data.volume[0]
        
        rsi = getattr(self.strategy, self.rsi_name)
        bb = getattr(self.strategy, self.bb_name)
        vol_ma = getattr(self.strategy, self.volume_ma_name)

        # Check RSI
        rsi_condition = rsi[0] <= self.get_param("rsi_oversold")

        # Check touching the Bollinger Bands (if enabled)
        bb_condition = not self.get_param("use_bb_touch") or current_price <= bb.bb_lower[0] * 1.01  # Small tolerance

        # Check volume
        volume_ok = current_volume >= vol_ma[0] * self.get_param("min_volume_ratio")

        return rsi_condition and bb_condition and volume_ok
