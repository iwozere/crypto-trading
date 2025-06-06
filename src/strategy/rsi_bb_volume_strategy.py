import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import backtrader as bt
import pandas as pd
import numpy as np
from src.notification.telegram_notifier import create_notifier
from src.strategy.base_strategy import BaseStrategy
from src.exit.exit_registry import get_exit_class
import datetime
from typing import Any, Dict, Optional

"""
RSI Bollinger Bands Volume Strategy Module
-----------------------------------------

This module implements a mean reversion trading strategy that combines RSI, Bollinger Bands, and Volume indicators with ATR-based position management. The strategy is designed for use with Backtrader and can be used for both backtesting and live trading. It provides entry and exit logic, position management, and trade recording.

Main Features:
- Entry and exit signals based on RSI, Bollinger Bands, Volume, and ATR
- Position and risk management using ATR-based take profit and trailing stop loss
- Designed for use with Backtrader and compatible with other trading frameworks

Classes:
- RSIBollVolumeATRStrategy: Main strategy class implementing the logic
"""

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
       - Uses configured exit logic for take profit and stop loss
       - Position Size: 10% of portfolio value
    
    3. Exit Conditions:
       - Based on configured exit logic (ATR, Fixed SL/TP, MA Crossover, Time Based, or Trailing Stop)
    
    Parameters:
        rsi_period (int): Period for RSI calculation (default: 14)
        boll_period (int): Period for Bollinger Bands (default: 20)
        boll_devfactor (float): Standard deviation multiplier for Bollinger Bands (default: 2.0)
        atr_period (int): Period for ATR calculation (default: 14)
        vol_ma_period (int): Period for Volume Moving Average (default: 20)
        rsi_oversold (float): RSI oversold threshold (default: 30)
        rsi_overbought (float): RSI overbought threshold (default: 70)
        exit_logic_name (str): Name of the exit logic to use
        exit_params (dict): Parameters for the selected exit logic
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
    def __init__(self, params: dict):
        super().__init__(params)
        self.notify = self.params.get('notify', False)
        use_talib = self.params.get('use_talib', False)
        
        # Initialize indicators based on use_talib flag
        if use_talib:
            # TA-Lib indicators
            self.rsi = bt.talib.RSI(self.data.close, timeperiod=self.params['rsi_period'])
            self.boll = bt.talib.BBANDS(
                self.data.close,
                timeperiod=self.params['boll_period'],
                nbdevup=self.params['boll_devfactor'],
                nbdevdn=self.params['boll_devfactor']
            )
            self.atr = bt.talib.ATR(
                self.data.high,
                self.data.low,
                self.data.close,
                timeperiod=self.params['atr_period']
            )
            self.vol_ma = bt.talib.SMA(self.data.volume, timeperiod=self.params['vol_ma_period'])
        else:
            # Backtrader built-in indicators
            self.rsi = bt.ind.RSI(period=self.params['rsi_period'])
            self.boll = bt.ind.BollingerBands(
                period=self.params['boll_period'],
                devfactor=self.params['boll_devfactor']
            )
            self.atr = bt.ind.ATR(period=self.params['atr_period'])
            self.vol_ma = bt.ind.SMA(self.data.volume, period=self.params['vol_ma_period'])
        
        # Initialize exit logic
        exit_logic_name = self.params.get('exit_logic_name', 'atr_exit')
        exit_params = self.params.get('exit_params', {})
        exit_class = get_exit_class(exit_logic_name)
        self.exit_logic = exit_class(exit_params)
        
        self.order = None
        self.entry_price = None
        self.highest_price = None
        self.current_trade = None
        self.position_closed = True
        self.last_order_type = None
        self.notifier = create_notifier()
        self.last_exit_reason = None

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
            
        # Get indicator values
        rsi_value = self.rsi[0]
        if self.params.get('use_talib', False):
            bb_low = self.boll[2][0]  # TA-Lib BBANDS returns [upper, middle, lower]
            bb_mid = self.boll[1][0]
            bb_high = self.boll[0][0]
        else:
            bb_low = self.boll.lines.bot[0]  # Backtrader BBANDS returns [bot, mid, top]
            bb_mid = self.boll.lines.mid[0]
            bb_high = self.boll.lines.top[0]
            
        atr_value = self.atr[0]
        vol_ma_value = self.vol_ma[0]
        volume = self.data.volume[0]
        close = self.data.close[0]
        
        # Entry conditions
        if not self.position and self.position_closed and (self.last_order_type is None or self.last_order_type == 'sell'):
            if (rsi_value < self.params['rsi_oversold'] and
                close < bb_low and
                volume > vol_ma_value):
                
                self.entry_price = close
                self.highest_price = self.entry_price
                
                # Initialize exit logic with entry price and ATR
                self.exit_logic.initialize(self.entry_price, atr_value)
                
                self.current_trade = {
                    'entry_time': self.data.datetime.datetime(0),
                    'entry_price': self.entry_price,
                    'atr_at_entry': atr_value,
                    'rsi_at_entry': rsi_value,
                    'volume_at_entry': volume,
                    'vol_ma_at_entry': vol_ma_value,
                    'bb_low_at_entry': bb_low,
                    'bb_mid_at_entry': bb_mid,
                    'bb_high_at_entry': bb_high
                }
                cash = self.broker.getcash()
                value = self.broker.getvalue()
                size = (value * 0.1) / close  # Using 10% of portfolio
                if cash >= (size * close * (1 + self.broker.comminfo[None].getcommission(size=size, price=close))):
                    self.order = self.buy(size=size)
                    self.position_closed = False
                    self.log(f'BUY CREATE {size:.2f} @ {close:.2f}')
        
        # Exit conditions
        elif self.position:
            self.highest_price = max(self.highest_price, close)
            
            # Check exit conditions using the configured exit logic
            exit_signal, exit_reason = self.exit_logic.check_exit(close, self.highest_price, atr_value)
            
            if exit_signal:
                self.last_exit_reason = exit_reason
                self.order = self.close()
                self.log(f'SELL CREATE {exit_reason} @ {close:.2f}')
                if self.current_trade:
                    self._record_trade_exit(close, exit_reason, atr_value, rsi_value, volume, vol_ma_value, bb_low, bb_mid, bb_high)

    def _record_trade_exit(self, close, exit_type, atr_value, rsi_value, volume, vol_ma_value, bb_low, bb_mid, bb_high):
        """Helper method to record trade exit details"""
        self.current_trade.update({
            'exit_time': self.data.datetime.datetime(0),
            'exit_price': close,
            'exit_type': exit_type,
            'exit_reason': self.last_exit_reason,
            'pnl': (close - self.entry_price) / self.entry_price * 100,
            'atr_at_exit': atr_value,
            'rsi_at_exit': rsi_value,
            'volume_at_exit': volume,
            'vol_ma_at_exit': vol_ma_value,
            'bb_low_at_exit': bb_low,
            'bb_mid_at_exit': bb_mid,
            'bb_high_at_exit': bb_high
        })
        if 'pnl_comm' not in self.current_trade:
            self.current_trade['pnl_comm'] = self.current_trade['pnl']
        self.record_trade(self.current_trade)
        self.current_trade = None
        self.last_exit_reason = None

    def on_trade_entry(self, trade):
        """Called when a new trade is entered"""
        if self.notifier:
            trade_data = {
                'symbol': self.symbol,
                'side': 'BUY' if trade.side == 'long' else 'SELL',
                'entry_price': trade.entry_price,
                'exit_price': trade.exit_price,
                'exit_type': trade.exit_type,
                'exit_reason': trade.exit_reason,
                'pnl': trade.pnl,
                'quantity': trade.quantity,
                'timestamp': trade.entry_time.isoformat(),
                'reason': f"RSI: {trade.rsi:.2f}, BB Position: {trade.bb_position}",
                'rsi': trade.rsi,
                'bb_position': trade.bb_position
            }
            self.notifier.send_trade_notification(trade_data)


