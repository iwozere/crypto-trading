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

This strategy is particularly effective for:
1. Taking profits when momentum is high
2. Exiting when price reaches extreme levels
3. Combining mean reversion (RSI) with volatility (BB) for exit signals
"""

from typing import Any, Dict

import backtrader as bt
from src.exit.exit_mixin import BaseExitMixin


class RSIBBExitMixin(BaseExitMixin):
    """Exit mixin based on RSI and Bollinger Bands"""

    def get_required_params(self) -> list:
        """There are no required parameters - all have default values"""
        return []

    def get_default_params(self) -> Dict[str, Any]:
        """Default parameters"""
        return {
            "rsi_period": 14,
            "rsi_overbought": 70,
            "bb_period": 20,
            "bb_stddev": 2.0,
            "use_bb_touch": True,  # Require touching the Bollinger Bands
        }

    def _init_indicators(self):
        """Initialization of RSI and Bollinger Bands indicators"""
        if self.strategy is None:
            raise ValueError("Strategy must be set before initializing indicators")

        # Create RSI indicator
        if self.strategy.p.use_talib:
            import talib
            self.indicators["rsi"] = bt.indicators.TALibIndicator(
                self.strategy.data.close,
                talib.RSI,
                timeperiod=self.get_param("rsi_period")
            )

            # Create Bollinger Bands indicators using TA-Lib
            bb_upper, bb_middle, bb_lower = talib.BBANDS(
                self.strategy.data.close,
                timeperiod=self.get_param("bb_period"),
                nbdevup=self.get_param("bb_stddev"),
                nbdevdn=self.get_param("bb_stddev"),
                matype=0
            )
            self.indicators["bb_upper"] = bt.indicators.TALibIndicator(self.strategy.data.close, lambda x: bb_upper)
            self.indicators["bb_middle"] = bt.indicators.TALibIndicator(self.strategy.data.close, lambda x: bb_middle)
            self.indicators["bb_lower"] = bt.indicators.TALibIndicator(self.strategy.data.close, lambda x: bb_lower)
        else:
            # Create RSI indicator using Backtrader
            self.indicators["rsi"] = bt.indicators.RSI(
                self.strategy.data.close, 
                period=self.get_param("rsi_period")
            )

            # Create Bollinger Bands indicators using Backtrader
            bb = bt.indicators.BollingerBands(
                self.strategy.data.close, 
                period=self.get_param("bb_period"),
                devfactor=self.get_param("bb_stddev")
            )
            self.indicators["bb_upper"] = bb.lines.top
            self.indicators["bb_middle"] = bb.lines.mid
            self.indicators["bb_lower"] = bb.lines.bot

    def should_exit(self) -> bool:
        """
        Exit logic: RSI in overbought zone and (optionally) touching the upper BB band
        """
        if not self.indicators:
            return False

        rsi = self.indicators["rsi"][0]
        current_price = self.strategy.data.close[0]

        # Check RSI
        rsi_overbought = rsi > self.get_param("rsi_overbought")

        # Check touching the Bollinger Bands (if enabled)
        bb_condition = True
        if self.get_param("use_bb_touch"):
            bb_upper = self.indicators["bb_upper"][0]
            bb_condition = current_price >= bb_upper * 0.99  # Small tolerance

        return rsi_overbought and bb_condition 