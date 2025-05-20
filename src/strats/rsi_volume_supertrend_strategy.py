import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import backtrader as bt
import pandas as pd
import numpy as np
from src.indicator.super_trend import SuperTrend
from src.strats.base_strategy import BaseStrategy

class RsiVolumeSuperTrendStrategy(BaseStrategy):
    """
    Backtrader-native trend-following strategy using SuperTrend for trend direction,
    RSI for pullback entries, and Volume for confirmation. ATR is used for calculating
    Take Profit and Stop Loss levels. Supports both Long and Short trades.

    - Inherits from BaseStrategy (Backtrader-native, standardized trade logging, notification, and event-driven architecture)
    - Uses Backtrader's param system (self.p)
    - Uses self.trades and self.record_trade for trade logging
    - All logic in __init__, next, notify_order, notify_trade
    """
    params = (
        ('rsi_period', 14),
        ('rsi_entry_long_level', 40.0),
        ('rsi_entry_short_level', 60.0),
        ('rsi_exit_long_level', 70.0),
        ('rsi_exit_short_level', 30.0),
        ('st_period', 10),
        ('st_multiplier', 3.0),
        ('vol_ma_period', 10),
        ('atr_period', 14),
        ('tp_atr_mult', 2.0),
        ('sl_atr_mult', 1.5),
        ('time_based_exit_period', 5),
        ('printlog', False),
    )

    def __init__(self):
        super().__init__()
        self.rsi = bt.indicators.RSI(period=self.p.rsi_period)
        self.st = SuperTrend(period=self.p.st_period, multiplier=self.p.st_multiplier)
        self.vol_ma = bt.indicators.SMA(self.data.volume, period=self.p.vol_ma_period)
        self.atr = bt.indicators.ATR(period=self.p.atr_period)
        self.order = None
        self.entry_price = None
        self.bar_executed = 0
        self.tp_price = None
        self.sl_price = None
        self.current_trade = None

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
                        self.tp_price = self.entry_price + self.p.tp_atr_mult * atr_val
                        self.sl_price = self.entry_price - self.p.sl_atr_mult * atr_val
                        self.current_trade['tp_price'] = self.tp_price
                        self.current_trade['sl_price'] = self.sl_price
            elif order.issell():
                if self.position.size == 0 and trade_type == 'long':
                    if self.current_trade:
                        self.current_trade['exit_price'] = order.executed.price
                        self.current_trade['exit_time'] = self.data.datetime.datetime(0)
                        self.record_trade(self.current_trade)
                        self.current_trade = None
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
                if rsi_val > self.p.rsi_exit_long_level: exit_reason = 'rsi_long_exit'
                elif st_direction == -1: exit_reason = 'st_flip_long_exit'
                elif (len(self) - self.bar_executed) >= self.p.time_based_exit_period and self.entry_price and close <= self.entry_price: exit_reason = 'time_long_exit'
                elif self.sl_price and close <= self.sl_price: exit_reason = 'sl_long'
                elif self.tp_price and close >= self.tp_price: exit_reason = 'tp_long'
                if exit_reason:
                    if self.current_trade:
                        self.current_trade['pnl'] = current_pnl_pct
                        self.current_trade['exit_type'] = exit_reason
                    self.order = self.close()
                    return
        else:
            if st_direction == 1 and \
               prev_rsi_val < self.p.rsi_entry_long_level and rsi_val > prev_rsi_val and \
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
