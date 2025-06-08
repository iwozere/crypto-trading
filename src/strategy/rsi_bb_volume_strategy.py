import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import datetime
from typing import Any, Dict, Optional

import backtrader as bt
import numpy as np
import pandas as pd
from src.notification.telegram_notifier import create_notifier
from src.strategy.base_strategy import BaseStrategy, get_exit_class

"""
RSI + Bollinger Bands + Volume Strategy Module
---------------------------------------------
Implements a mean reversion strategy using RSI, Bollinger Bands, and Volume indicators.
Uses pluggable exit logic for position management.
"""


class RsiBollVolumeStrategy(BaseStrategy):
    """
    A mean reversion strategy that combines RSI, Bollinger Bands, and Volume indicators with pluggable exit logic.

    Strategy Logic:
    1. Entry Conditions:
       - RSI below oversold level (default: 30)
       - Price below lower Bollinger Band
       - Volume above its moving average
       - No existing position
       - Previous position was closed

    2. Position Management:
       - Uses configured exit logic for position management
       - Position Size: 10% of portfolio value

    3. Exit Logic:
       - Pluggable exit logic system with multiple options:
         - ATR-based exits (atr_exit): Uses ATR for dynamic take profit and stop loss
         - Fixed take profit/stop loss (fixed_tp_sl_exit): Uses fixed price levels
         - Moving average crossover (ma_crossover_exit): Exits on MA crossovers
         - Time-based exits (time_based_exit): Exits after a fixed number of bars
         - Trailing stop exits (trailing_stop_exit): Uses trailing stop loss

    Parameters:
        rsi_period (int): Period for RSI calculation (default: 14)
        boll_period (int): Period for Bollinger Bands (default: 20)
        boll_devfactor (float): Standard deviation multiplier for Bollinger Bands (default: 2.0)
        vol_ma_period (int): Period for Volume Moving Average (default: 20)
        rsi_oversold (float): RSI oversold threshold (default: 30)
        rsi_overbought (float): RSI overbought threshold (default: 70)
        exit_logic_name (str): Name of the exit logic to use (default: 'atr_exit')
        exit_params (dict): Parameters for the selected exit logic
        printlog (bool): Whether to print trade logs (default: False)
        risk_per_trade (float): Risk per trade as a percentage of portfolio value (default: 0.02)

    Trade Tracking:
        - Records entry/exit prices, times, and PnL
        - Tracks trade reasons (RSI, BB position)
        - Sends notifications via Telegram (if configured)

    Returns:
        DataFrame with trade history including:
        - Entry/exit times and prices
        - Take profit and stop loss levels
        - PnL percentage
        - Exit type (TP/SL)
        - Technical indicators at entry
    """

    params = (
        ("rsi_period", 14),
        ("rsi_oversold", 30),
        ("boll_period", 20),
        ("boll_devfactor", 2),
        ("vol_ma_period", 20),
        ("atr_period", 14),
        ("use_talib", False),
        ("notify", False),
        ("risk_per_trade", 0.02),  # 2% risk per trade
    )

    def __init__(self, params: dict):
        super().__init__(params)
        self.notify = self.params.get("notify", False)
        use_talib = self.params.get("use_talib", False)
        self.risk_per_trade = self.params.get("risk_per_trade", 0.02)  # Default to 2% if not specified
        self.notifier = self.params.get("notifier", None)  # Get notifier from params

        # Initialize indicators based on use_talib flag
        if use_talib:
            # TA-Lib indicators
            self.rsi = bt.talib.RSI(
                self.data.close, timeperiod=self.params["rsi_period"]
            )
            self.boll = bt.talib.BBANDS(
                self.data.close,
                timeperiod=self.params["boll_period"],
                nbdevup=self.params["boll_devfactor"],
                nbdevdn=self.params["boll_devfactor"],
            )
            self.vol_ma = bt.talib.SMA(
                self.data.volume, timeperiod=self.params["vol_ma_period"]
            )
            self.atr = bt.talib.ATR(
                self.data.high,
                self.data.low,
                self.data.close,
                timeperiod=self.params["atr_period"],
            )
        else:
            # Backtrader built-in indicators
            self.rsi = bt.ind.RSI(period=self.params["rsi_period"])
            self.boll = bt.ind.BollingerBands(
                period=self.params["boll_period"],
                devfactor=self.params["boll_devfactor"],
            )
            self.vol_ma = bt.ind.SMA(
                self.data.volume, period=self.params["vol_ma_period"]
            )
            self.atr = bt.ind.ATR(period=self.params["atr_period"])


    def notify_order(self, order):
        if order.status == order.Completed:
            if order.isbuy():
                self.entry_price = order.executed.price
                self.highest_price = order.executed.price
                self.last_order_type = "buy"

                # Initialize exit logic with entry price
                self.exit_logic.initialize(self.entry_price)
            else:
                self.position_closed = True
                self.last_order_type = "sell"
        elif order.status in [order.Canceled, order.Margin]:
            if order.isbuy():
                self.position_closed = True
                self.last_order_type = None
        self.order = None

    def next(self):
        if self.order:
            return

        # Get indicator values
        rsi_value = self.rsi[0]
        if self.params.get("use_talib", False):
            bb_low = self.boll[2][0]  # TA-Lib BBANDS returns [upper, middle, lower]
            bb_mid = self.boll[1][0]
            bb_high = self.boll[0][0]
        else:
            bb_low = self.boll.lines.bot[0]  # Backtrader BBANDS returns [bot, mid, top]
            bb_mid = self.boll.lines.mid[0]
            bb_high = self.boll.lines.top[0]

        vol_ma_value = self.vol_ma[0]
        volume = self.data.volume[0]
        close = self.data.close[0]
        atr_value = self.atr[0]

        # Entry conditions
        if (
            not self.position
            and self.position_closed
            and (self.last_order_type is None or self.last_order_type == "sell")
        ):
            if (
                rsi_value < self.params["rsi_oversold"]
                and close < bb_low
                and volume > vol_ma_value
            ):
                self.entry_price = close
                self.highest_price = self.entry_price

                # Initialize exit logic with entry price and ATR value
                self.exit_logic.initialize(self.entry_price, atr_value)

                self.current_trade = {
                    "entry_time": self.data.datetime.datetime(0),
                    "entry_price": self.entry_price,
                    "rsi_at_entry": rsi_value,
                    "volume_at_entry": volume,
                    "vol_ma_at_entry": vol_ma_value,
                    "bb_low_at_entry": bb_low,
                    "bb_mid_at_entry": bb_mid,
                    "bb_high_at_entry": bb_high,
                    "atr_at_entry": atr_value,
                }

                # Calculate position size based on risk per trade
                cash = self.broker.getcash()
                risk_amount = cash * self.risk_per_trade
                stop_loss = self.exit_logic.sl_price  # Access stop loss price directly
                risk_per_share = self.entry_price - stop_loss
                if risk_per_share > 0:
                    size = risk_amount / risk_per_share
                    self.order = self.buy(size=size)
                    self.position_closed = False
                    if self.notify and self.notifier:
                        self.notifier.send_notification(
                            f"Buy Signal - Price: {close:.2f}, RSI: {rsi_value:.2f}, Volume: {volume:.2f}"
                        )

        # Exit conditions
        elif self.position and not self.position_closed:
            # Check exit logic
            exit_signal, exit_reason = self.exit_logic.check_exit(
                close, self.highest_price, atr_value
            )
            if exit_signal:
                self.order = self.sell()
                self.position_closed = True
                self.last_exit_reason = exit_reason
                if self.notify and self.notifier:
                    self.notifier.send_notification(
                        f"Exit Signal - Price: {close:.2f}, Reason: {exit_reason}"
                    )

            # Update highest price
            if close > self.highest_price:
                self.highest_price = close

    def _record_trade_exit(
        self, close, exit_type, rsi_value, volume, vol_ma_value, bb_low, bb_mid, bb_high
    ):
        """Helper method to record trade exit details"""
        self.current_trade.update(
            {
                "exit_time": self.data.datetime.datetime(0),
                "exit_price": close,
                "exit_type": exit_type,
                "exit_reason": self.last_exit_reason,
                "pnl": (close - self.entry_price) / self.entry_price * 100,
                "rsi_at_exit": rsi_value,
                "volume_at_exit": volume,
                "vol_ma_at_exit": vol_ma_value,
                "bb_low_at_exit": bb_low,
                "bb_mid_at_exit": bb_mid,
                "bb_high_at_exit": bb_high,
            }
        )
        if "pnl_comm" not in self.current_trade:
            self.current_trade["pnl_comm"] = self.current_trade["pnl"]
        self.record_trade(self.current_trade)
        self.current_trade = None
        self.last_exit_reason = None

    def on_trade_entry(self, trade):
        """Called when a new trade is entered"""
        if self.notifier:
            trade_data = {
                "symbol": self.symbol,
                "side": "BUY" if trade.side == "long" else "SELL",
                "entry_price": trade.entry_price,
                "exit_price": trade.exit_price,
                "exit_type": trade.exit_type,
                "exit_reason": trade.exit_reason,
                "pnl": trade.pnl,
                "quantity": trade.quantity,
                "timestamp": trade.entry_time.isoformat(),
                "reason": f"RSI: {trade.rsi:.2f}, BB Position: {trade.bb_position}",
                "rsi": trade.rsi,
                "bb_position": trade.bb_position,
            }
            self.notifier.send_trade_notification(trade_data)
