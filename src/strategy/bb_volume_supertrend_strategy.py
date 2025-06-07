import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# from src.notification.telegram import create_notifier # Temporarily commented out
import datetime
from typing import Any, Dict, Optional

import backtrader as bt
import numpy as np
import pandas as pd
from src.indicator.super_trend import SuperTrend
from src.strategy.base_strategy import BaseStrategy, get_exit_class

"""
BB SuperTrend Volume Breakout Strategy Module
-------------------------------------------

This module implements a breakout trading strategy using Bollinger Bands, SuperTrend, and Volume indicators with pluggable exit logic. The strategy is designed for use with Backtrader and can be used for both backtesting and live trading.

Main Features:
- Entry and exit signals based on Bollinger Bands, SuperTrend, and Volume
- Pluggable exit logic system for flexible position management
- Designed for use with Backtrader and compatible with other trading frameworks

Classes:
- BBSuperTrendVolumeBreakoutStrategy: Main strategy class implementing the logic
"""


class BBSuperTrendVolumeBreakoutStrategy(BaseStrategy):
    """
    Breakout strategy using Bollinger Bands, SuperTrend, and Volume indicators with pluggable exit logic.
    Accepts a single params/config dictionary.

    Indicators:
    - Bollinger Bands: Identifies squeeze/breakout conditions.
    - SuperTrend: Confirms breakout direction.
    - Volume: Confirms breakout strength.

    Use Case:
    Volatile breakout markets (crypto, small-cap stocks)
    Timeframes: 15m, 1H, 4H
    Strengths: Captures big moves early
    Weaknesses: Needs filtering to avoid fakeouts

    Entry Logic:
    - Long:
        - Price closes above upper Bollinger Band.
        - SuperTrend is green (bullish).
        - Volume is above its moving average (e.g., 1.5x 20-bar average).
    - Short:
        - Price closes below lower Bollinger Band.
        - SuperTrend is red (bearish).
        - Volume is above its moving average (e.g., 1.5x 20-bar average).

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
            self.boll = bt.talib.BBANDS(
                self.data.close,
                timeperiod=self.params["boll_period"],
                nbdevup=self.params["boll_devfactor"],
                nbdevdn=self.params["boll_devfactor"],
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
            self.boll = bt.ind.BollingerBands(
                period=self.params["boll_period"],
                devfactor=self.params["boll_devfactor"],
            )
            self.atr = bt.ind.ATR(period=self.params["atr_period"])
            self.vol_ma = bt.ind.SMA(
                self.data.volume, period=self.params["vol_ma_period"]
            )

        # Initialize exit logic
        exit_logic_name = self.params.get("exit_logic_name", "atr_exit")
        exit_params = self.params.get("exit_params", {})
        exit_class = get_exit_class(exit_logic_name)
        self.exit_logic = exit_class(exit_params)

        self.order = None
        self.entry_price = None
        self.highest_price = None
        self.current_trade = None
        self.trade_active = False
        self.last_exit_reason = None

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

                # Initialize exit logic with entry price and ATR
                atr_value = self.atr[0]
                self.exit_logic.initialize(self.entry_price, atr_value)

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
        bb_top = self.boll.lines.top[0]
        bb_bot = self.boll.lines.bot[0]
        bb_mid = self.boll.lines.mid[0]
        st_direction = self.st.lines.direction[0]
        st_value = self.st.lines.supertrend[0]
        vol_ma_val = self.vol_ma[0]
        atr_value = self.atr[0]

        if not self.position:
            # Entry Logic
            if close > bb_top and st_direction == 1 and volume > vol_ma_val:
                self.log(
                    f"LONG ENTRY SIGNAL: Close {close:.2f} > BB Top {bb_top:.2f}, ST Direction: {st_direction}, Volume: {volume:.2f} > MA {vol_ma_val:.2f}"
                )

                # Record trade details
                self.current_trade = {
                    "entry_time": self.data.datetime.datetime(0),
                    "entry_price": "pending_long",
                    "atr_at_entry": atr_value,
                    "volume_at_entry": volume,
                    "vol_ma_at_entry": vol_ma_val,
                    "bb_top_at_entry": bb_top,
                    "bb_mid_at_entry": bb_mid,
                    "bb_bot_at_entry": bb_bot,
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
                    close, self.highest_price, atr_value
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
                                "atr_at_exit": atr_value,
                                "volume_at_exit": volume,
                                "vol_ma_at_exit": vol_ma_val,
                                "bb_top_at_exit": bb_top,
                                "bb_mid_at_exit": bb_mid,
                                "bb_bot_at_exit": bb_bot,
                                "supertrend_val_at_exit": st_value,
                                "supertrend_dir_at_exit": st_direction,
                            }
                        )


# Example usage (for testing, normally run via a main script)
if __name__ == "__main__":
    cerebro = bt.Cerebro()
    cerebro.addstrategy(BBSuperTrendVolumeBreakoutStrategy, printlog=True)

    # Create a dummy data feed
    data_dict = {
        "datetime": pd.to_datetime(
            [
                "2023-01-01T00:00:00",
                "2023-01-01T01:00:00",
                "2023-01-01T02:00:00",
                "2023-01-01T03:00:00",
                "2023-01-01T04:00:00",
                "2023-01-01T05:00:00",
                "2023-01-01T06:00:00",
                "2023-01-01T07:00:00",
                "2023-01-01T08:00:00",
                "2023-01-01T09:00:00",
                "2023-01-01T10:00:00",
                "2023-01-01T11:00:00",
                "2023-01-01T12:00:00",
                "2023-01-01T13:00:00",
                "2023-01-01T14:00:00",
                "2023-01-01T15:00:00",
                "2023-01-01T16:00:00",
                "2023-01-01T17:00:00",
                "2023-01-01T18:00:00",
                "2023-01-01T19:00:00",
                "2023-01-01T20:00:00",
            ]
            * 5
        ),  # Repeat to get enough data points
        "open": np.random.rand(21 * 5) * 10 + 100,
        "high": np.random.rand(21 * 5) * 12 + 102,  # ensure high > open
        "low": np.random.rand(21 * 5) * 8 + 98,  # ensure low < open
        "close": np.random.rand(21 * 5) * 10 + 100,
        "volume": np.random.rand(21 * 5) * 1000 + 100,
    }
    # Ensure high is max and low is min
    data_dict["high"] = np.maximum(data_dict["high"], data_dict["open"])
    data_dict["high"] = np.maximum(data_dict["high"], data_dict["close"])
    data_dict["low"] = np.minimum(data_dict["low"], data_dict["open"])
    data_dict["low"] = np.minimum(data_dict["low"], data_dict["close"])

    df = pd.DataFrame(data_dict)
    df.set_index("datetime", inplace=True)

    data_feed = bt.feeds.PandasData(dataname=df)
    cerebro.adddata(data_feed)
    cerebro.broker.setcash(10000.0)
    cerebro.broker.setcommission(commission=0.001)  # Example commission

    print("Starting Portfolio Value: %.2f" % cerebro.broker.getvalue())
    cerebro.run()
    print("Final Portfolio Value: %.2f" % cerebro.broker.getvalue())

    # Access trades from the strategy instance if needed
    # strategy_instance = cerebro.runstrategy[0][0]
    # print(pd.DataFrame(strategy_instance.trades))

# Removed old BollVolumeSupertrendStrategy class and its remnants
# Kept the custom SuperTrend indicator
# Implemented BBSuperTrendVolumeBreakoutStrategy with new logic
# Added basic example usage for testing
# Simplified trade logging and notification handling for now
