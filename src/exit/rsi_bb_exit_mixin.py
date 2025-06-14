"""
RSI and Bollinger Bands Exit Mixin

This module implements an exit strategy based on the combination of:
1. RSI (Relative Strength Index)
2. Bollinger Bands

The strategy exits a position when:
1. RSI is overbought
2. Price touches or crosses above the upper Bollinger Band

Parameters:
    rsi_period (int): Period for RSI calculation (default: 14)
    rsi_overbought (float): Overbought threshold for RSI (default: 70)
    bb_period (int): Period for Bollinger Bands calculation (default: 20)
    bb_stddev (float): Standard deviation multiplier for Bollinger Bands (default: 2.0)
    use_bb_touch (bool): Whether to require price touching the upper band (default: True)
    use_talib (bool): Whether to use TA-Lib for calculations (default: True)

This strategy combines mean reversion (RSI + BB) to identify potential reversal points.
"""

from typing import Any, Dict, Optional

import backtrader as bt
from src.exit.base_exit_mixin import BaseExitMixin
from src.indicator.talib_rsi import TALibRSI
from src.indicator.talib_bb import TALibBB
from src.notification.logger import setup_logger

logger = setup_logger(__name__)


class RSIBBExitMixin(BaseExitMixin):
    """Exit mixin that combines RSI and Bollinger Bands for exit signals."""

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        """Initialize the mixin with parameters"""
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
            "bb_period": 20,
            "bb_stddev": 2.0,
            "use_bb_touch": True,
        }

    def _init_indicators(self):
        """Initialize RSI and Bollinger Bands indicators"""
        if not hasattr(self, 'strategy'):
            return

        try:
            data = self.strategy.data
            use_talib = self.strategy.use_talib

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
                # Use Backtrader's native RSI
                setattr(self.strategy, self.rsi_name, bt.indicators.RSI(
                    data,
                    period=self.get_param("rsi_period")
                ))

                # Use Backtrader's native Bollinger Bands
                setattr(self.strategy, self.bb_name, bt.indicators.BollingerBands(
                    data,
                    period=self.get_param("bb_period"),
                    devfactor=self.get_param("bb_stddev")
                ))
        except Exception as e:
            logger.error(f"Error initializing indicators: {e}")
            raise

    def should_exit(self) -> bool:
        """Check if we should exit a position"""
        if not self.strategy.position:
            return False

        try:
            # Get indicators
            rsi = getattr(self.strategy, self.rsi_name)
            bb = getattr(self.strategy, self.bb_name)
            current_price = self.strategy.data.close[0]

            # Check RSI
            rsi_condition = rsi[0] >= self.get_param("rsi_overbought")

            # Check touching the Bollinger Bands (if enabled)
            bb_condition = not self.get_param("use_bb_touch") or current_price >= bb.bb_upper[0] * 0.99  # Small tolerance

            return_value = rsi_condition and bb_condition
            if return_value:
                logger.debug(f"EXIT: Price: {current_price}, RSI: {rsi[0]}, "
                           f"BB Upper: {bb.bb_upper[0]}, "
                           f"RSI Overbought: {self.get_param('rsi_overbought')}")
            return return_value
        except Exception as e:
            logger.error(f"Error in should_exit: {e}")
            return False

    def get_exit_reason(self) -> str:
        """Get the reason for exiting the position"""
        if not self.strategy.position:
            return "unknown"
            
        try:
            # Get indicators
            rsi = getattr(self.strategy, self.rsi_name)
            bb = getattr(self.strategy, self.bb_name)
            
            # Check which condition triggered the exit
            if rsi[0] >= self.get_param("rsi_overbought"):
                if self.get_param("use_bb_touch") and self.strategy.data.close[0] >= bb.bb_upper[0] * 0.99:
                    return "rsi_bb_overbought"
                return "rsi_overbought"
            elif self.get_param("use_bb_touch") and self.strategy.data.close[0] >= bb.bb_upper[0] * 0.99:
                return "bb_upper_touch"
                
            return "unknown"
        except Exception as e:
            logger.error(f"Error in get_exit_reason: {e}")
            return "unknown" 