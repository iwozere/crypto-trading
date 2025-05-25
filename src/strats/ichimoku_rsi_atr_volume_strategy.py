import backtrader as bt
from src.notification.telegram_notifier import create_notifier
from src.strats.base_strategy import BaseStrategy
import datetime
from typing import Any, Dict, Optional

"""
Ichimoku RSI ATR Volume Strategy Module
--------------------------------------

This module implements a trading strategy that combines Ichimoku Cloud, RSI, ATR-based trailing stops, and volume confirmation. The strategy is designed for use with Backtrader and can be used for both backtesting and live trading. It provides entry and exit logic, position management, and trade recording.

Main Features:
- Entry and exit signals based on Ichimoku, RSI, ATR, and volume
- Trailing stop management using ATR
- Designed for use with Backtrader and compatible with other trading frameworks

Classes:
- IchimokuRSIATRVolumeStrategy: Main strategy class implementing the logic
"""

class IchimokuRSIATRVolumeStrategy(BaseStrategy):
    """
    Backtrader-native strategy using Ichimoku, RSI, ATR (for trailing stop), and a volume confirmation.
    - Inherits from BaseStrategy (Backtrader-native, standardized trade logging, notification, and event-driven architecture)
    - Uses Backtrader's param system (self.p)
    - Uses self.trades and self.record_trade for trade logging
    - All logic in __init__, next, notify_order, notify_trade
    """
    params = (
        ('tenkan_period', 9),
        ('kijun_period', 26),
        ('senkou_span_b_period', 52),
        ('rsi_period', 14),
        ('rsi_entry', 50),
        ('atr_period', 14),
        ('atr_mult', 2.0),
        ('vol_ma_period', 20),
        ('printlog', False),
    )

    def __init__(self):
        super().__init__()
        self.ichimoku = bt.ind.Ichimoku(
            self.data,
            tenkan=self.p.tenkan_period,
            kijun=self.p.kijun_period,
            senkou=self.p.senkou_span_b_period
        )
        self.tenkan = self.ichimoku.tenkan_sen
        self.kijun = self.ichimoku.kijun_sen
        self.senkou_a = self.ichimoku.senkou_span_a
        self.senkou_b = self.ichimoku.senkou_span_b
        self.chikou = self.ichimoku.chikou_span
        self.rsi = bt.ind.RSI(period=self.p.rsi_period)
        self.atr = bt.ind.ATR(period=self.p.atr_period)
        self.vol_ma = bt.ind.SMA(self.data.volume, period=self.p.vol_ma_period)
        self.order = None
        self.entry_price = None
        self.trailing_stop = None
        self.position_type = None
        self.current_trade = None
        self.notifier = create_notifier()

    def next(self):
        if self.order:
            return
        close = self.data.close[0]
        volume = self.data.volume[0]
        vol_ma = self.vol_ma[0]
        rsi = self.rsi[0]
        tenkan = self.tenkan[0]
        kijun = self.kijun[0]
        senkou_a = self.senkou_a[0]
        senkou_b = self.senkou_b[0]
        atr = self.atr[0]
        cloud_top = max(senkou_a, senkou_b)
        cloud_bot = min(senkou_a, senkou_b)
        if not self.position:
            #print(f"close={close}, cloud_top={cloud_top}, tenkan={tenkan}, kijun={kijun}, rsi={rsi}, volume={volume}, vol_ma={vol_ma}")
            if (
                close > cloud_top and
                tenkan > kijun and self.tenkan[-1] <= self.kijun[-1] and
                rsi > self.p.rsi_entry and
                volume > vol_ma
            ):
                self.order = self.buy()
                self.entry_price = close
                self.trailing_stop = close - self.p.atr_mult * atr
                self.position_type = 'long'
                self.current_trade = {
                    'symbol': self.data._name if hasattr(self.data, '_name') else 'UNKNOWN',
                    'entry_time': self.data.datetime.datetime(0),
                    'entry_price': close,
                    'type': 'long',
                    'rsi': rsi,
                    'volume': volume,
                    'vol_ma': vol_ma,
                    'tenkan': tenkan,
                    'kijun': kijun,
                    'cloud_top': cloud_top,
                    'cloud_bot': cloud_bot
                }
                self.log(f'LONG ENTRY: {close:.2f} (RSI {rsi:.2f}, Vol {volume:.0f} > MA {vol_ma:.0f})')
           
#            elif (
#                close < cloud_bot and
#                tenkan < kijun and self.tenkan[-1] >= self.kijun[-1] and
#                rsi < self.p.rsi_entry and
#                volume > vol_ma
#            ):
#                self.order = self.sell()
#                self.entry_price = close
#                self.trailing_stop = close + self.p.atr_mult * atr
#                self.position_type = 'short'
#                self.current_trade = {
#                    'symbol': self.data._name if hasattr(self.data, '_name') else 'UNKNOWN',
#                    'entry_time': self.data.datetime.datetime(0),
#                    'entry_price': close,
#                    'type': 'short',
#                    'rsi': rsi,
#                    'volume': volume,
#                    'vol_ma': vol_ma,
#                    'tenkan': tenkan,
#                    'kijun': kijun,
#                    'cloud_top': cloud_top,
#                    'cloud_bot': cloud_bot
#                }
#                self.log(f'SHORT ENTRY: {close:.2f} (RSI {rsi:.2f}, Vol {volume:.0f} > MA {vol_ma:.0f})')

        else:
            if self.position_type == 'long':
                new_stop = close - self.p.atr_mult * atr
                if new_stop > self.trailing_stop:
                    self.trailing_stop = new_stop
                exit_signal = False
                exit_reason = ''
                if tenkan < kijun and self.tenkan[-1] >= self.kijun[-1]:
                    exit_signal = True
                    exit_reason = 'Tenkan cross down'
                elif close < cloud_bot:
                    exit_signal = True
                    exit_reason = 'Price below cloud'
                elif close < self.trailing_stop:
                    exit_signal = True
                    exit_reason = 'Trailing stop hit'
                if exit_signal:
                    self.order = self.close()
                    if self.current_trade:
                        self.current_trade.update({
                            'symbol': self.data._name if hasattr(self.data, '_name') else 'UNKNOWN',
                            'exit_time': self.data.datetime.datetime(0),
                            'exit_price': close,
                            'exit_reason': exit_reason,
                            'pnl': (close - self.entry_price) / self.entry_price * 100
                        })
                        self.record_trade(self.current_trade)
                        self.current_trade = None
                    self.log(f'LONG EXIT: {close:.2f} ({exit_reason})')
#            elif self.position_type == 'short':
#                new_stop = close + self.p.atr_mult * atr
#                if new_stop < self.trailing_stop:
#                    self.trailing_stop = new_stop
#                exit_signal = False
#                exit_reason = ''
#                if tenkan > kijun and self.tenkan[-1] <= self.kijun[-1]:
#                    exit_signal = True
#                    exit_reason = 'Tenkan cross up'
#                elif close > cloud_top:
#                    exit_signal = True
#                    exit_reason = 'Price above cloud'
#                elif close > self.trailing_stop:
#                    exit_signal = True
#                    exit_reason = 'Trailing stop hit'
#                if exit_signal:
#                    self.order = self.close()
#                    if self.current_trade:
#                        self.current_trade.update({
#                            'symbol': self.data._name if hasattr(self.data, '_name') else 'UNKNOWN',
#                            'exit_time': self.data.datetime.datetime(0),
#                            'exit_price': close,
#                            'exit_reason': exit_reason,
#                            'pnl': (self.entry_price - close) / self.entry_price * 100
#                        })
#                        self.record_trade(self.current_trade)
#                        self.current_trade = None
#                    self.log(f'SHORT EXIT: {close:.2f} ({exit_reason})')

    def notify_order(self, order):
        if order.status in [order.Completed, order.Canceled, order.Margin, order.Rejected]:
            self.order = None
            if not self.position:
                self.entry_price = None
                self.trailing_stop = None
                self.position_type = None

