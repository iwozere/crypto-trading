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

    def __init__(self, params: dict):
        super().__init__(params)
        self.notify = self.params.get("notify", False)
        use_talib = self.params.get("use_talib", False)

        # Initialize indicators based on use_talib flag
        if use_talib:
            # TA-Lib indicators
            self.rsi = bt.talib.RSI(
                self.data.close, timeperiod=self.params["rsi_period"]
            )
            self.atr = bt.talib.ATR(
                self.data.high,
                self.data.low,
                self.data.close,
                timeperiod=self.params["atr_period"],
            )
            self.vol_ma = bt.talib.SMA(
                self.data.volume, timeperiod=self.params["vol_ma_period"]
            )
        else:
            # Backtrader built-in indicators
            self.rsi = bt.ind.RSI(period=self.params["rsi_period"])
            self.atr = bt.ind.ATR(period=self.params["atr_period"])
            self.vol_ma = bt.ind.SMA(
                self.data.volume, period=self.params["vol_ma_period"]
            )

        # Initialize SuperTrend
        self.st = SuperTrend(
            params={
                "period": self.params["st_period"],
                "multiplier": self.params["st_multiplier"],
                "use_talib": use_talib,
            }
        )


    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return
        if order.status == order.Completed:
            if order.isbuy():
                self.log(
                    f"BUY EXECUTED, Price: {order.executed.price:.2f}, Cost: {order.executed.value:.2f}, Comm: {order.executed.comm:.2f}"
                )
                self.entry_price = order.executed.price
                self.highest_price = self.entry_price

                # Initialize exit logic with entry price
                self.exit_logic.initialize(self.entry_price)

                if self.current_trade:
                    self.current_trade["entry_price"] = self.entry_price
            elif order.issell():
                if self.position.size == 0:
                    self.entry_price = None
                    self.highest_price = None
                    if self.current_trade:
                        self.current_trade["exit_price"] = order.executed.price
                        self.current_trade["exit_time"] = self.data.datetime.datetime(0)
                        self.current_trade["exit_reason"] = self.last_exit_reason
                        self.record_trade(self.current_trade)
                        self.current_trade = None
                    self.last_exit_reason = None
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log(f"Order Canceled/Margin/Rejected: {order.getstatusname()}")
            if not self.position:
                self.entry_price = None
                self.highest_price = None
        self.order = None

    def next(self):
        if self.order:
            return
        close = self.data.close[0]
        volume = self.data.volume[0]
        rsi_val = self.rsi[0]
        prev_rsi_val = self.rsi[-1] if len(self.rsi) > 1 else rsi_val
        st_direction = self.st.lines.direction[0]
        st_value = self.st.lines.supertrend[0]
        vol_ma_val = self.vol_ma[0]
        atr_val = self.atr[0]

        if not self.position:
            # Entry Logic
            if (
                st_direction == 1
                and prev_rsi_val < self.params["rsi_entry_long_level"]
                and rsi_val > prev_rsi_val
                and volume > vol_ma_val
            ):

                self.log(
                    f"LONG ENTRY SIGNAL: ST Direction: {st_direction}, RSI {rsi_val:.2f} > {prev_rsi_val:.2f}, Volume {volume:.2f} > MA {vol_ma_val:.2f}"
                )

                # Record trade details
                self.current_trade = {
                    "entry_time": self.data.datetime.datetime(0),
                    "entry_price": "pending_long",
                    "atr_at_entry": atr_val,
                    "rsi_at_entry": rsi_val,
                    "volume_at_entry": volume,
                    "vol_ma_at_entry": vol_ma_val,
                    "supertrend_val_at_entry": st_value,
                    "supertrend_dir_at_entry": st_direction,
                    "type": "long",
                }

                size = (self.broker.getvalue() * 0.1) / close
                self.order = self.buy(size=size)
        else:
            if self.position.size > 0:
                self.highest_price = max(self.highest_price, close)

                # Check exit conditions using the configured exit logic
                exit_signal, exit_reason = self.exit_logic.check_exit(
                    close, self.highest_price, atr_val
                )

                if exit_signal:
                    self.last_exit_reason = exit_reason
                    self.order = self.close()
                    self.log(f"EXIT SIGNAL: {exit_reason}. Closing position.")
                    if self.current_trade:
                        self.current_trade.update(
                            {
                                "exit_time": self.data.datetime.datetime(0),
                                "exit_price": close,
                                "exit_reason": exit_reason,
                                "atr_at_exit": atr_val,
                                "rsi_at_exit": rsi_val,
                                "volume_at_exit": volume,
                                "vol_ma_at_exit": vol_ma_val,
                                "supertrend_val_at_exit": st_value,
                                "supertrend_dir_at_exit": st_direction,
                            }
                        )
