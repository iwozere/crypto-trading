"""
RSI and Bollinger Bands Exit Mixin

This module implements an exit strategy based on the combination of Relative Strength Index (RSI)
and Bollinger Bands indicators. The strategy exits a position when:
1. RSI is in the overbought zone (above the configured threshold)
2. Price touches or crosses above the upper Bollinger Band

Parameters:
    rsi_period (int): Period for RSI calculation (default: 14)
    rsi_overbought (float): RSI threshold for overbought condition (default: 70)
    bb_period (int): Period for Bollinger Bands calculation (default: 20)
    bb_stddev (float): Standard deviation multiplier for Bollinger Bands (default: 2.0)
    use_bb_touch (bool): Whether to require price touching the upper band (default: True)
    use_talib (bool): Whether to use TA-Lib for calculations (default: True)

This strategy is particularly effective for:
1. Taking profits when momentum is high
2. Exiting when price reaches extreme levels
3. Combining mean reversion (RSI) with volatility (BB) for exit signals
"""

from typing import Any, Dict, Optional

import backtrader as bt
import numpy as np
from src.exit.base_exit_mixin import BaseExitMixin
import talib

from src.indicator.talib_rsi import TALibRSI
from src.indicator.talib_bb import TALibBB
from src.notification.logger import setup_logger

logger = setup_logger()


class RSIBBExitMixin(BaseExitMixin):
    """Exit mixin based on RSI and Bollinger Bands"""

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        super().__init__(params)
        self.rsi_name = 'exit_rsi'
        self.bb_name = 'exit_bb'

    def get_required_params(self) -> list:
        """There are no required parameters - all have default values"""
        return []

    @classmethod
    def get_default_params(cls) -> Dict[str, Any]:
        """Default parameters"""
        return {
            "rsi_period": 14,
            "rsi_overbought": 70,
            "rsi_oversold": 30,
            "bb_period": 20,
            "bb_devfactor": 2.0,
            "use_talib": True,
        }

    def _init_indicators(self):
        """Initialization of RSI and Bollinger Bands indicators"""
        if not hasattr(self, 'strategy'):
            return
            
        use_talib = self.get_param("use_talib", True)
        if use_talib:
            try:
                # Use TA-Lib indicators
                setattr(self.strategy, self.rsi_name, TALibRSI(
                    self.strategy.data,
                    period=self.get_param("rsi_period")
                ))
                
                setattr(self.strategy, self.bb_name, TALibBB(
                    self.strategy.data,
                    period=self.get_param("bb_period"),
                    devfactor=self.get_param("bb_devfactor")
                ))
            except Exception as e:
                logger.error(f"Error initializing indicators: {str(e)}")
                raise
        else:
            # Use Backtrader's indicators directly
            setattr(self.strategy, self.rsi_name, bt.indicators.RSI(
                self.strategy.data,
                period=self.get_param("rsi_period"),
                plot=False
            ))
            setattr(self.strategy, self.bb_name, bt.indicators.BollingerBands(
                self.strategy.data,
                period=self.get_param("bb_period"),
                devfactor=self.get_param("bb_devfactor"),
                plot=False
            ))

    def should_exit(self) -> bool:
        """
        Exit logic: RSI in overbought zone and (optionally) touching the upper BB band
        """
        if not self.strategy.position:
            return False
            
        rsi = getattr(self.strategy, self.rsi_name).rsi[0]
        bb = getattr(self.strategy, self.bb_name)
        price = self.strategy.data.close[0]
        
        if self.strategy.position.size > 0:
            return (
                rsi > self.get_param("rsi_overbought") or
                price > bb.lines[0][0]
            )
        else:
            return (
                rsi < self.get_param("rsi_oversold") or
                price < bb.lines[2][0]
            ) 