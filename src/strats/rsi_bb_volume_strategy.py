import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import backtrader as bt
import pandas as pd
import numpy as np
from src.notification.telegram_notifier import create_notifier
from src.strats.base_strategy import BaseStrategy

class RSIBollVolumeATRStrategy(BaseStrategy):
    """
    A mean reversion strategy that combines RSI, Bollinger Bands, and Volume indicators with ATR-based position management.
    
    Strategy Logic:
    1. Entry Conditions:
       - RSI below oversold level (default: 30)
       - Price below lower Bollinger Band
       - Volume above its moving average
       - No existing position
       - Previous position was closed
    
    2. Position Management:
       - Take Profit: Entry price + (ATR * tp_atr_mult)
       - Stop Loss: Trailing stop based on highest price - (ATR * sl_atr_mult)
       - Position Size: 10% of portfolio value
    
    3. Exit Conditions:
       - Take Profit hit
       - Trailing Stop Loss hit
    
    Parameters:
        rsi_period (int): Period for RSI calculation (default: 14)
        boll_period (int): Period for Bollinger Bands (default: 20)
        boll_devfactor (float): Standard deviation multiplier for Bollinger Bands (default: 2.0)
        atr_period (int): Period for ATR calculation (default: 14)
        vol_ma_period (int): Period for Volume Moving Average (default: 20)
        tp_atr_mult (float): ATR multiplier for Take Profit (default: 2.0)
        sl_atr_mult (float): ATR multiplier for Stop Loss (default: 1.5)
        rsi_oversold (float): RSI oversold threshold (default: 30)
        rsi_overbought (float): RSI overbought threshold (default: 70)
        printlog (bool): Whether to print trade logs (default: False)
    
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
        ('rsi_period', 14),
        ('boll_period', 20),
        ('boll_devfactor', 2.0),
        ('atr_period', 14),
        ('vol_ma_period', 20),
        ('tp_atr_mult', 2.0),
        ('sl_atr_mult', 1.5),
        ('rsi_oversold', 30),
        ('rsi_overbought', 70),
        ('printlog', False),
    )

    def __init__(self):
        super().__init__()
        self.rsi = bt.ind.RSI(period=self.p.rsi_period)
        self.boll = bt.ind.BollingerBands(
            period=self.p.boll_period,
            devfactor=self.p.boll_devfactor
        )
        self.atr = bt.ind.ATR(period=self.p.atr_period)
        self.vol_ma = bt.ind.SMA(self.data.volume, period=self.p.vol_ma_period)
        self.order = None
        self.entry_price = None
        self.highest_price = None
        self.tp_price = None
        self.sl_price = None
        self.current_trade = None
        self.position_closed = True
        self.last_order_type = None
        self.notifier = create_notifier()

    def notify_order(self, order):
        if order.status == order.Completed:
            if order.isbuy():
                self.entry_price = order.executed.price
                self.highest_price = order.executed.price
                self.last_order_type = 'buy'
            else:
                self.position_closed = True
                self.last_order_type = 'sell'
        elif order.status in [order.Canceled, order.Margin]:
            if order.isbuy():
                self.position_closed = True
                self.last_order_type = None
        self.order = None

    def next(self):
        if self.order:
            return
        rsi_value = self.rsi[0]
        bb_low = self.boll.lines.bot[0]
        bb_mid = self.boll.lines.mid[0]
        bb_high = self.boll.lines.top[0]
        atr_value = self.atr[0]
        vol_ma_value = self.vol_ma[0]
        volume = self.data.volume[0]
        close = self.data.close[0]
        if not self.position and self.position_closed and (self.last_order_type is None or self.last_order_type == 'sell'):
            if (rsi_value < self.p.rsi_oversold and
                close < bb_low and
                volume > vol_ma_value):
                self.entry_price = close
                self.tp_price = self.entry_price + self.p.tp_atr_mult * atr_value
                self.sl_price = self.entry_price - self.p.sl_atr_mult * atr_value
                self.highest_price = self.entry_price
                self.current_trade = {
                    'entry_time': self.data.datetime.datetime(0),
                    'entry_price': self.entry_price,
                    'tp_price': self.tp_price,
                    'sl_price': self.sl_price,
                    'atr': atr_value,
                    'rsi': rsi_value,
                    'volume': volume,
                    'volume_ma': vol_ma_value,
                    'bb_low': bb_low,
                    'bb_mid': bb_mid,
                    'bb_high': bb_high
                }
                cash = self.broker.getcash()
                value = self.broker.getvalue()
                size = (value * 0.1) / close
                if cash >= (size * close * (1 + self.broker.comminfo[None].getcommission(size=size, price=close))):
                    self.order = self.buy(size=size)
                    self.position_closed = False
        elif self.position:
            self.highest_price = max(self.highest_price, close)
            trailing_sl = self.highest_price - self.p.sl_atr_mult * atr_value
            if close >= self.tp_price:
                self.order = self.close()
                if self.current_trade:
                    self.current_trade.update({
                        'exit_time': self.data.datetime.datetime(0),
                        'exit_price': close,
                        'exit_type': 'tp',
                        'pnl': (close - self.entry_price) / self.entry_price * 100
                    })
                    self.record_trade(self.current_trade)
                    self.current_trade = None
            elif close <= trailing_sl:
                self.order = self.close()
                if self.current_trade:
                    self.current_trade.update({
                        'exit_time': self.data.datetime.datetime(0),
                        'exit_price': close,
                        'exit_type': 'sl',
                        'pnl': (close - self.entry_price) / self.entry_price * 100
                    })
                    self.record_trade(self.current_trade)
                    self.current_trade = None

    def on_trade_entry(self, trade):
        """Called when a new trade is entered"""
        if self.notifier:
            trade_data = {
                'symbol': self.symbol,
                'side': 'BUY' if trade.side == 'long' else 'SELL',
                'entry_price': trade.entry_price,
                'tp_price': trade.tp_price,
                'sl_price': trade.sl_price,
                'quantity': trade.quantity,
                'timestamp': trade.entry_time.isoformat(),
                'reason': f"RSI: {trade.rsi:.2f}, BB Position: {trade.bb_position}",
                'rsi': trade.rsi,
                'bb_position': trade.bb_position
            }
            self.notifier.send_trade_notification(trade_data)


