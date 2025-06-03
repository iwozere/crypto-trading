import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import backtrader as bt
import pandas as pd
import numpy as np
from src.indicator.super_trend import SuperTrend
from src.strategy.base_strategy import BaseStrategy
import datetime
from typing import Any, Dict, Optional

"""
RSI Volume SuperTrend Strategy Module
------------------------------------

This module implements a trend-following trading strategy using SuperTrend for trend direction, RSI for pullback entries, and Volume for confirmation. ATR is used for calculating take profit and stop loss levels. The strategy supports both long and short trades and is designed for use with Backtrader for backtesting and live trading.

Main Features:
- Entry and exit signals based on SuperTrend, RSI, Volume, and ATR
- Position and risk management using ATR-based take profit and stop loss
- Designed for use with Backtrader and compatible with other trading frameworks

Classes:
- RsiVolumeSuperTrendStrategy: Main strategy class implementing the logic
"""

class RsiVolumeSuperTrendStrategy(BaseStrategy):
    """
    Trend-following strategy using SuperTrend, RSI, Volume, and ATR.
    Accepts a single params/config dictionary.
    """
    def __init__(self, params: dict):
        super().__init__(params)
        self.notify = self.params.get('notify', False)
        use_talib = self.params.get('use_talib', False)
        if use_talib:
            self.rsi = bt.talib.RSI(timeperiod=self.params.get('rsi_period', 14))
            self.vol_ma = bt.talib.SMA(timeperiod=self.params.get('vol_ma_period', 10))
            self.atr = bt.talib.ATR(timeperiod=self.params.get('atr_period', 14))
        else:
            self.rsi = bt.indicators.RSI(period=self.params.get('rsi_period', 14))
            self.vol_ma = bt.indicators.SMA(self.data.volume, period=self.params.get('vol_ma_period', 10))
            self.atr = bt.indicators.ATR(period=self.params.get('atr_period', 14))
        self.st = SuperTrend(params={
            'period': self.params.get('st_period', 10),
            'multiplier': self.params.get('st_multiplier', 3.0),
            'use_talib': use_talib
        })
        self.order = None
        self.entry_price = None
        self.bar_executed = 0
        self.tp_price = None
        self.sl_price = None
        self.current_trade = None
        self.last_exit_reason = None

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return
        if order.status == order.Completed:
            trade_type = ''
            if self.current_trade:
                trade_type = self.current_trade.get('type', '')
            if order.isbuy():
                if self.position.size > 0 and trade_type == 'long':
                    self.entry_price = order.executed.price
                    self.bar_executed = len(self)
                    if self.current_trade:
                        self.current_trade['entry_price'] = self.entry_price
                        atr_val = self.atr[0]
                        self.tp_price = self.entry_price + self.params.get('tp_atr_mult', 2.0) * atr_val
                        self.sl_price = self.entry_price - self.params.get('sl_atr_mult', 1.5) * atr_val
                        self.current_trade['tp_price'] = self.tp_price
                        self.current_trade['sl_price'] = self.sl_price
            elif order.issell():
                if self.position.size == 0 and trade_type == 'long':
                    if self.current_trade:
                        self.current_trade['exit_price'] = order.executed.price
                        self.current_trade['exit_time'] = self.data.datetime.datetime(0)
                        self.current_trade['exit_reason'] = self.last_exit_reason
                        self.current_trade.pop('symbol', None)
                        self.record_trade(self.current_trade)
                        self.current_trade = None
                    self.last_exit_reason = None
                    self.entry_price = None
                    self.bar_executed = 0
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            if self.current_trade and self.current_trade.get('entry_price', '').startswith('pending'):
                self.current_trade = None
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
        if self.position:
            exit_reason = None
            current_pnl_pct = 0
            if self.position.size > 0:
                if self.entry_price: current_pnl_pct = (close - self.entry_price) / self.entry_price * 100
                if rsi_val > self.params.get('rsi_exit_long_level', 70.0): exit_reason = 'rsi_long_exit'
                elif st_direction == -1: exit_reason = 'st_flip_long_exit'
                elif (len(self) - self.bar_executed) >= self.params.get('time_based_exit_period', 5) and self.entry_price and close <= self.entry_price: exit_reason = 'time_long_exit'
                elif self.sl_price and close <= self.sl_price: exit_reason = 'sl_long'
                elif self.tp_price and close >= self.tp_price: exit_reason = 'tp_long'
                if exit_reason:
                    self.last_exit_reason = exit_reason
                    if self.current_trade:
                        self.current_trade['pnl'] = current_pnl_pct
                        self.current_trade['exit_type'] = exit_reason
                        self.current_trade['atr_at_exit'] = atr_val
                        self.current_trade['rsi_at_exit'] = rsi_val
                        self.current_trade['volume_at_exit'] = volume
                        self.current_trade['vol_ma_at_exit'] = vol_ma_val
                        self.current_trade['supertrend_val_at_exit'] = st_value
                        self.current_trade['supertrend_dir_at_exit'] = st_direction
                        if 'pnl_comm' not in self.current_trade:
                            self.current_trade['pnl_comm'] = self.current_trade['pnl']
                    self.order = self.close()
                    return
        else:
            if st_direction == 1 and \
               prev_rsi_val < self.params.get('rsi_entry_long_level', 40.0) and rsi_val > prev_rsi_val and \
               volume > vol_ma_val:
                self.current_trade = {
                    'entry_time': self.data.datetime.datetime(0),
                    'entry_price': 'pending_long',
                    'atr_at_entry': atr_val, 'rsi_at_entry': rsi_val,
                    'volume_at_entry': volume, 'vol_ma_at_entry': vol_ma_val,
                    'supertrend_val_at_entry': st_value, 'supertrend_dir_at_entry': st_direction,
                    'type': 'long'
                }
                size = (self.broker.getvalue() * 0.1) / close
                self.order = self.buy(size=size)
                return
