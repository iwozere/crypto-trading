import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))


import backtrader as bt
import pandas as pd
import numpy as np
from src.notification.telegram_notifier import create_notifier

class RSIBollVolumeATRStrategy(bt.Strategy):
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
    )

    def __init__(self):
        # Initialize indicators
        self.rsi = bt.ind.RSI(period=self.p.rsi_period)
        self.boll = bt.ind.BollingerBands(
            period=self.p.boll_period,
            devfactor=self.p.boll_devfactor
        )
        self.atr = bt.ind.ATR(period=self.p.atr_period)
        self.vol_ma = bt.ind.SMA(self.data.volume, period=self.p.vol_ma_period)

        # Initialize trade tracking
        self.order = None
        self.entry_price = None
        self.highest_price = None
        self.tp_price = None
        self.sl_price = None
        self.trades = []
        self.current_trade = None
        self.notifier = create_notifier()
        self.position_closed = True
        self.last_order_type = None

    def start(self):
        """Called once at the start of the strategy"""
        self.position_closed = True
        self.last_order_type = None

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
        # Skip if we have an open order
        if self.order:
            return

        # Get current values
        rsi_value = self.rsi[0]
        bb_low = self.boll.lines.bot[0]
        bb_mid = self.boll.lines.mid[0]
        bb_high = self.boll.lines.top[0]
        atr_value = self.atr[0]
        vol_ma_value = self.vol_ma[0]
        volume = self.data.volume[0]
        close = self.data.close[0]

        # Entry logic - only enter if we have no position, previous position was closed, and last order was a sell
        if not self.position and self.position_closed and (self.last_order_type is None or self.last_order_type == 'sell'):
            if (rsi_value < self.p.rsi_oversold and
                close < bb_low and
                volume > vol_ma_value):

                self.entry_price = close
                self.tp_price = self.entry_price + self.p.tp_atr_mult * atr_value
                self.sl_price = self.entry_price - self.p.sl_atr_mult * atr_value
                self.highest_price = self.entry_price

                # Record trade entry
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

                # Calculate size using Backtrader's methods
                cash = self.broker.getcash()
                value = self.broker.getvalue()
                size = (value * 0.1) / close  # Use 10% of portfolio value
                
                # Ensure we have enough cash for the order
                if cash >= (size * close * (1 + self.broker.comminfo[None].getcommission(size=size, price=close))):
                    self.order = self.buy(size=size)
                    self.position_closed = False
        elif self.position:  # We have an open position
            # Update highest price
            self.highest_price = max(self.highest_price, close)
            # Update trailing stop
            trailing_sl = self.highest_price - self.p.sl_atr_mult * atr_value

            # Exit logic
            if close >= self.tp_price:
                # Close position
                self.order = self.close()
                if self.current_trade:
                    self.current_trade.update({
                        'exit_time': self.data.datetime.datetime(0),
                        'exit_price': close,
                        'exit_type': 'tp',
                        'pnl': (close - self.entry_price) / self.entry_price * 100
                    })
                    self.trades.append(self.current_trade)
                    self.current_trade = None
            elif close <= trailing_sl:
                # Close position
                self.order = self.close()
                if self.current_trade:
                    self.current_trade.update({
                        'exit_time': self.data.datetime.datetime(0),
                        'exit_price': close,
                        'exit_type': 'sl',
                        'pnl': (close - self.entry_price) / self.entry_price * 100
                    })
                    self.trades.append(self.current_trade)
                    self.current_trade = None

    def get_trades(self):
        """Return trade information as a DataFrame"""
        if not self.trades:
            return pd.DataFrame()
        
        return pd.DataFrame(self.trades)

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

    def on_trade_exit(self, trade):
        """Called when a trade is exited"""
        if self.notifier:
            trade_data = {
                'symbol': self.symbol,
                'side': 'BUY' if trade.side == 'long' else 'SELL',
                'entry_price': trade.entry_price,
                'exit_price': trade.exit_price,
                'pnl': trade.pnl,
                'exit_type': trade.exit_type,
                'timestamp': trade.exit_time.isoformat()
            }
            self.notifier.send_trade_update(trade_data)

    def on_error(self, error):
        """Called when an error occurs"""
        if self.notifier:
            self.notifier.send_error_notification(str(error))
