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

from typing import Any, Dict, Optional

import backtrader as bt
import numpy as np
from src.exit.base_exit_mixin import BaseExitMixin


class RSIBBExitMixin(BaseExitMixin):
    """Exit mixin based on RSI and Bollinger Bands"""

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        super().__init__(params)

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
            "use_talib": False,
        }

    def _init_indicators(self):
        """Initialization of RSI and Bollinger Bands indicators"""
        if not hasattr(self, 'strategy'):
            return
        use_talib = self.get_param("use_talib", False)
        if use_talib:
            try:
                import talib
                close_prices = np.array([self.strategy.data.close[i] for i in range(len(self.strategy.data))])
                rsi_values = talib.RSI(close_prices, timeperiod=self.get_param("rsi_period"))
                self.indicators["rsi"] = bt.indicators.RSI(self.strategy.data, period=self.get_param("rsi_period"), plot=False)
                for i, value in enumerate(rsi_values):
                    if i < len(self.indicators["rsi"].lines[0]):
                        self.indicators["rsi"].lines[0][i] = value
                upper, middle, lower = talib.BBANDS(
                    close_prices,
                    timeperiod=self.get_param("bb_period"),
                    nbdevup=self.get_param("bb_devfactor"),
                    nbdevdn=self.get_param("bb_devfactor"),
                    matype=0
                )
                self.indicators["bb"] = bt.indicators.BollingerBands(
                    self.strategy.data,
                    period=self.get_param("bb_period"),
                    devfactor=self.get_param("bb_devfactor"),
                    plot=False
                )
                for i, (u, m, l) in enumerate(zip(upper, middle, lower)):
                    if i < len(self.indicators["bb"].lines[0]):
                        self.indicators["bb"].lines[0][i] = u
                        self.indicators["bb"].lines[1][i] = m
                        self.indicators["bb"].lines[2][i] = l
            except ImportError:
                self.strategy.logger.warning("TA-Lib not available, using Backtrader's indicators")
                self.indicators["rsi"] = bt.indicators.RSI(self.strategy.data, period=self.get_param("rsi_period"), plot=False)
                self.indicators["bb"] = bt.indicators.BollingerBands(
                    self.strategy.data,
                    period=self.get_param("bb_period"),
                    devfactor=self.get_param("bb_devfactor"),
                    plot=False
                )
        else:
            self.indicators["rsi"] = bt.indicators.RSI(self.strategy.data, period=self.get_param("rsi_period"), plot=False)
            self.indicators["bb"] = bt.indicators.BollingerBands(
                self.strategy.data,
                period=self.get_param("bb_period"),
                devfactor=self.get_param("bb_devfactor"),
                plot=False
            )

    def should_exit(self) -> bool:
        """
        Exit logic: RSI in overbought zone and (optionally) touching the upper BB band
        """
        if not self.strategy.position:
            return False
        rsi = self.indicators["rsi"][0]
        bb = self.indicators["bb"]
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