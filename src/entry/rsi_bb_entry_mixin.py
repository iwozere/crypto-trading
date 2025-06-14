"""
RSI and Bollinger Bands Entry Mixin

This module implements an entry strategy based on the combination of:
1. RSI (Relative Strength Index)
2. Bollinger Bands

The strategy enters a position when:
1. RSI is oversold
2. Price touches or crosses below the lower Bollinger Band

Parameters:
    rsi_period (int): Period for RSI calculation (default: 14)
    rsi_oversold (float): Oversold threshold for RSI (default: 30)
    bb_period (int): Period for Bollinger Bands calculation (default: 20)
    bb_stddev (float): Standard deviation multiplier for Bollinger Bands (default: 2.0)
    use_bb_touch (bool): Whether to require price touching the lower band (default: True)
    use_talib (bool): Whether to use TA-Lib for calculations (default: True)

This strategy combines mean reversion (RSI + BB) to identify potential reversal points.
"""

from typing import Any, Dict, Optional

import backtrader as bt
import numpy as np
from src.entry.base_entry_mixin import BaseEntryMixin
from src.indicator.talib_rsi import TALibRSI
from src.indicator.talib_bb import TALibBB
from src.notification.logger import setup_logger

logger = setup_logger()

class RSIBBEntryMixin(BaseEntryMixin):
    """Entry mixin based on RSI and Bollinger Bands"""

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
            "use_talib": True,
        }

    def _init_indicators(self):
        """Initialize RSI and Bollinger Bands indicators"""
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
                
        except Exception as e:
            logger.error(f"Error initializing indicators: {str(e)}")
            raise

    def should_enter(self) -> bool:
        """
        Entry logic: RSI oversold and price touching lower BB
        """
        if not all(hasattr(self.strategy, name) for name in [self.rsi_name, self.bb_name]):
            return False

        current_price = self.strategy.data.close[0]
        
        rsi = getattr(self.strategy, self.rsi_name)
        bb = getattr(self.strategy, self.bb_name)

        # Check RSI
        rsi_condition = rsi[0] <= self.get_param("rsi_oversold")

        # Check touching the Bollinger Bands (if enabled)
        bb_condition = not self.get_param("use_bb_touch") or current_price <= bb.bb_lower[0] * 1.01  # Small tolerance

        return rsi_condition and bb_condition
