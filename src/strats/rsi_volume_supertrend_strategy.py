import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import backtrader as bt
import pandas as pd
import numpy as np
from src.notification.telegram_notifier import create_notifier

class SuperTrend(bt.Indicator):
    params = (('period', 10), ('multiplier', 3.0))
    lines = ('supertrend', 'direction')
    plotinfo = dict(subplot=False)

    def __init__(self):
        self.atr = bt.indicators.ATR(self.datas[0], period=self.p.period)
        self.current_final_upperband = 0.0
        self.current_final_lowerband = 0.0
        self.current_direction = 0

    def next(self):
        high = self.datas[0].high[0]
        low = self.datas[0].low[0]
        close = self.datas[0].close[0]
        atr_val = self.atr[0]

        if np.isnan(atr_val):
            self.lines.supertrend[0] = float('nan')
            self.lines.direction[0] = 0
            return

        hl2 = (high + low) / 2.0
        basic_upperband = hl2 + self.p.multiplier * atr_val
        basic_lowerband = hl2 - self.p.multiplier * atr_val

        if self.current_direction == 0:
            self.current_direction = 1 if close > hl2 else -1
            self.current_final_upperband = basic_upperband
            self.current_final_lowerband = basic_lowerband
        else:
            prev_close = self.datas[0].close[-1]

            if basic_upperband < self.current_final_upperband or prev_close > self.current_final_upperband:
                self.current_final_upperband = basic_upperband

            if basic_lowerband > self.current_final_lowerband or prev_close < self.current_final_lowerband:
                self.current_final_lowerband = basic_lowerband

            if self.current_direction == 1 and close < self.current_final_lowerband:
                self.current_direction = -1
            elif self.current_direction == -1 and close > self.current_final_upperband:
                self.current_direction = 1

        self.lines.direction[0] = self.current_direction
        if self.current_direction == 1:
            self.lines.supertrend[0] = self.current_final_lowerband
        elif self.current_direction == -1:
            self.lines.supertrend[0] = self.current_final_upperband
        else:
            self.lines.supertrend[0] = float('nan')

class RsiVolumeSuperTrendStrategy(bt.Strategy):
    """
    A trend-following strategy using SuperTrend for trend direction,
    RSI for pullback entries, and Volume for confirmation.
    ATR is used for calculating Take Profit and Stop Loss levels.
    Supports both Long and Short trades.
    
    Use Case:
    Trending markets (crypto, strong stocks, indices)
    Timeframes: 1H, 4H, Daily
    Strengths: Clear trend direction, avoids counter-trend traps
    Weaknesses: Poor in choppy/ranging markets    

    Strategy Logic:
    -----------------
    SuperTrend: Filters trades in the direction of the main trend (using SuperTrend direction line).
    RSI: Identifies oversold conditions in uptrends (for long entries) or
         overbought conditions in downtrends (for short entries) after a pullback.
    Volume: Confirms the legitimacy of the pullback or bounce against the trend.

    Entry Logic (Long):
    1. SuperTrend direction is Up (self.st.lines.direction[0] == 1).
    2. RSI dips below `rsi_entry_long_level` (e.g., 40) then turns upward (current RSI > previous RSI).
    3. Volume increases vs. `vol_ma_period`-bar average (confirms bounce).
    4. No existing position.

    Entry Logic (Short):
    1. SuperTrend direction is Down (self.st.lines.direction[0] == -1).
    2. RSI rises above `rsi_entry_short_level` (e.g., 60) then turns downward (current RSI < previous RSI).
    3. Volume increases vs. `vol_ma_period`-bar average (confirms pullback selling pressure).
    4. No existing position.

    Exit Logic (Long):
    - RSI crosses above `rsi_exit_long_level` (e.g., 70).
    - SuperTrend direction flips to Down.
    - Time-based: After `time_based_exit_period` bars if P&L is not positive.
    - ATR Stop Loss hit.
    - ATR Take Profit hit.

    Exit Logic (Short):
    - RSI crosses below `rsi_exit_short_level` (e.g., 30).
    - SuperTrend direction flips to Up.
    - Time-based: After `time_based_exit_period` bars if P&L is not positive.
    - ATR Stop Loss hit.
    - ATR Take Profit hit.

    Parameters:
        rsi_period (int): Period for RSI calculation (default: 14)
        rsi_entry_long_level (float): RSI level for long entry pullback (default: 40)
        rsi_entry_short_level (float): RSI level for short entry pullback (default: 60)
        rsi_exit_long_level (float): RSI level to exit long positions (default: 70)
        rsi_exit_short_level (float): RSI level to exit short positions (default: 30)
        st_period (int): Period for SuperTrend ATR calculation (default: 10)
        st_multiplier (float): Multiplier for SuperTrend ATR (default: 3.0)
        vol_ma_period (int): Period for Volume Moving Average (default: 10)
        atr_period (int): Period for ATR calculation for TP/SL (default: 14)
        tp_atr_mult (float): ATR multiplier for Take Profit (default: 2.0)
        sl_atr_mult (float): ATR multiplier for Stop Loss (default: 1.5)
        time_based_exit_period (int): Max bars to hold a non-profitable trade (default: 5)
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
    )

    def __init__(self):
        self.rsi = bt.indicators.RSI(period=self.p.rsi_period)
        self.st = SuperTrend(period=self.p.st_period, multiplier=self.p.st_multiplier)
        self.vol_ma = bt.indicators.SMA(self.data.volume, period=self.p.vol_ma_period)
        self.atr = bt.indicators.ATR(period=self.p.atr_period)

        self.order = None
        self.entry_price = None
        self.bar_executed = 0
        self.tp_price = None
        self.sl_price = None
        self.trades = []
        self.current_trade = None
        self.notifier = create_notifier()

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
                        self.trades.append(self.current_trade)
                        self.current_trade = None
                    self.entry_price = None
                    self.bar_executed = 0
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            if self.current_trade and self.current_trade['entry_price'].startswith('pending'):
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
