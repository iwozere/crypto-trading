import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import datetime
from typing import Any, Dict, Optional

import backtrader as bt
import numpy as np
import pandas as pd
from src.indicator.super_trend import SuperTrend
from src.strategy.base_strategy import BaseStrategy, get_exit_class

"""
RSI Volume SuperTrend Strategy Module
-----------------------------------

This module implements a trend-following trading strategy using SuperTrend, RSI, and Volume indicators with pluggable exit logic. The strategy is designed for use with Backtrader and can be used for both backtesting and live trading.

Main Features:
- Entry and exit signals based on SuperTrend, RSI, and Volume
- Pluggable exit logic system for flexible position management
- Designed for use with Backtrader and compatible with other trading frameworks

Classes:
- RsiVolumeSuperTrendStrategy: Main strategy class implementing the logic
"""


class RsiVolumeSuperTrendStrategy(BaseStrategy):
    """
    Trend-following strategy using SuperTrend, RSI, Volume, and pluggable exit logic.
    Accepts a single params/config dictionary.

    Indicators:
    - SuperTrend: Determines trend direction and strength
    - RSI: Identifies pullback entries in the trend direction
    - Volume: Confirms entry and exit signals

    Entry Logic:
    - Long:
        - SuperTrend is bullish (green)
        - RSI pulls back to oversold level
        - Volume confirms the entry
    - Short:
        - SuperTrend is bearish (red)
        - RSI rallies to overbought level
        - Volume confirms the entry

    Exit Logic:
    - Pluggable exit logic system with multiple options:
        - ATR-based exits (atr_exit): Uses ATR for dynamic take profit and stop loss
        - Fixed take profit/stop loss (fixed_tp_sl_exit): Uses fixed price levels
        - Moving average crossover (ma_crossover_exit): Exits on MA crossovers
        - Time-based exits (time_based_exit): Exits after a fixed number of bars
        - Trailing stop exits (trailing_stop_exit): Uses trailing stop loss
    """

    def __init__(self, params=None):
        super().__init__(params)
        self.notify = self.params.get("notify", False)
        use_talib = self.params.get("use_talib", False)

        if use_talib:
            # TA-Lib indicators
            self.rsi = bt.talib.RSI(self.data.close, timeperiod=self.params["rsi_period"])
            self.vol_ma = bt.talib.SMA(self.data.volume, timeperiod=self.params["vol_ma_period"])
        else:
            # Backtrader built-in indicators
            self.rsi = bt.indicators.RSI(self.data, period=self.params["rsi_period"])
            self.vol_ma = bt.indicators.SMA(self.data.volume, period=self.params["vol_ma_period"])

        # Initialize SuperTrend indicator with params dictionary
        supertrend_params = {
            "period": self.params["supertrend_period"],
            "multiplier": self.params["supertrend_multiplier"],
            "use_talib": use_talib
        }
        self.supertrend = SuperTrend(params=supertrend_params)

    def notify_order(self, order):
        if order.status == order.Completed:
            if order.isbuy():
                self.entry_price = order.executed.price
                self.last_order_type = "buy"
                # Initialize exit logic with entry price
                self.exit_logic.initialize(self.entry_price)
            else:
                self.last_order_type = "sell"

    def next(self):
        super().next()
        rsi_val = self.rsi[0]
        st_value = self.supertrend.lines.supertrend[0]
        vol_ma_val = self.vol_ma[0]

        if not self.position:
            # Entry conditions
            if (
                rsi_val < self.params["rsi_oversold"]
                and st_value < self.data.close[0]
                and self.data.volume[0] > vol_ma_val
            ):
                self.buy()
        else:
            # Exit conditions
            if self.exit_logic.check_exit(self.data.close[0])[0]:
                self.sell()
