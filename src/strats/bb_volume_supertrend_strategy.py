import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import backtrader as bt
import pandas as pd
import numpy as np
from src.indicator.super_trend import SuperTrend
from src.strats.base_strategy import BaseStrategy
# from src.notification.telegram import create_notifier # Temporarily commented out
import datetime
from typing import Any, Dict, Optional

"""
BB Volume SuperTrend Strategy Module
-----------------------------------

This module implements a breakout trading strategy using Bollinger Bands, SuperTrend, and Volume indicators. The strategy is designed for volatile breakout markets and can be used for both backtesting and live trading. It provides entry and exit logic, position management, and trade recording.

Main Features:
- Entry and exit signals based on Bollinger Bands, SuperTrend, and Volume
- Position and risk management using ATR-based take profit and stop loss
- Designed for use with Backtrader and compatible with other trading frameworks

Classes:
- BBSuperTrendVolumeBreakoutStrategy: Main strategy class implementing the logic
"""

class BBSuperTrendVolumeBreakoutStrategy(BaseStrategy):
    """
    Breakout strategy using Bollinger Bands, SuperTrend, and Volume indicators.
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
    - Position is closed if:
        - Price closes back inside Bollinger Bands.
        - SuperTrend flips against the position.
        - Fixed Take Profit (TP) or Stop Loss (SL) is hit (based on ATR).
    """
    def __init__(self, params: dict):
        super().__init__(params)
        self.notify = self.params.get('notify', False)
        self.boll = bt.indicators.BollingerBands(
            period=self.params.get('bb_period', 20),
            devfactor=self.params.get('bb_devfactor', 2.0)
        )
        self.supertrend = SuperTrend(
            self.datas[0],
            period=self.params.get('st_period', 10),
            multiplier=self.params.get('st_multiplier', 3.0)
        )
        self.atr = bt.indicators.ATR(period=self.params.get('atr_period', 14))
        self.vol_ma = bt.indicators.SMA(self.data.volume, period=self.params.get('vol_ma_period', 20))
        self.order = None
        self.entry_price = None
        self.trade_active = False
        self.entry_bar = None
        self.active_tp_price = None
        self.active_sl_price = None
        self.trades = []
        self.last_exit_price = None
        self.last_exit_reason = None
        # self.notifier = create_notifier() # Temporarily commented out

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return # Do nothing for these statuses

        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f'BUY EXECUTED, Price: {order.executed.price:.2f}, Cost: {order.executed.value:.2f}, Comm: {order.executed.comm:.2f}')
                self.entry_price = order.executed.price
                # Calculate TP/SL based on ATR at entry bar
                atr_val = self.atr[-(self.datas[0].datetime.idx - self.entry_bar)] # ATR at time of entry signal
                if atr_val > 0: # Ensure ATR is valid
                    self.active_tp_price = self.entry_price + self.params.get('tp_atr_mult', 1.45) * atr_val
                    self.active_sl_price = self.entry_price - self.params.get('sl_atr_mult', 0.74) * atr_val
                    self.log(f'BUY TP: {self.active_tp_price:.2f}, SL: {self.active_sl_price:.2f}, ATR: {atr_val:.2f}')
                else:
                    self.log('ATR was zero or invalid at entry for TP/SL calc for BUY.')
                    self.active_tp_price = None # Disable TP/SL if ATR is not valid
                    self.active_sl_price = None

            elif order.issell():
                self.log(f'SELL EXECUTED, Price: {order.executed.price:.2f}, Cost: {order.executed.value:.2f}, Comm: {order.executed.comm:.2f}')
                if self.trade_active: # This is a closing sell
                     self.trade_active = False # Reset flag after closing trade
                     self.last_exit_price = order.executed.price # Store exit price for trade logging
                else: # This is an opening short sell
                    self.entry_price = order.executed.price
                    atr_val = self.atr[-(self.datas[0].datetime.idx - self.entry_bar)]
                    if atr_val > 0:
                        self.active_tp_price = self.entry_price - self.params.get('tp_atr_mult', 1.45) * atr_val # TP is lower for shorts
                        self.active_sl_price = self.entry_price + self.params.get('sl_atr_mult', 0.74) * atr_val # SL is higher for shorts
                        self.log(f'SHORT TP: {self.active_tp_price:.2f}, SL: {self.active_sl_price:.2f}, ATR: {atr_val:.2f}')
                    else:
                        self.log('ATR was zero or invalid at entry for TP/SL calc for SHORT.')
                        self.active_tp_price = None
                        self.active_sl_price = None

            self.bar_executed = len(self) # Bar when order was executed

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log(f'Order Canceled/Margin/Rejected: Status {order.getstatusname()}')
            if self.trade_active and self.order == order: # If an attempt to close failed
                pass # Keep trade_active as is, may need to retry
            elif not self.trade_active and self.order == order: # If an attempt to open failed
                self.entry_price = None # Reset entry price
                self.active_tp_price = None
                self.active_sl_price = None


        self.order = None # Reset pending order

    def notify_trade(self, trade):
        if not trade.isclosed:
            return

        self.log(f'OPERATION PROFIT, GROSS {trade.pnl:.2f}, NET {trade.pnlcomm:.2f}')
        self.log(f'Trade history: {getattr(trade, "history", None)}')
        self.log(f'Trade size: {getattr(trade, "size", None)}')
        
        direction = 'long' if trade.size > 0 else 'short'
        entry_price = trade.price
        exit_price = self.last_exit_price
        # Get current indicator values
        bb_lower = self.boll.lines.bot[0] if hasattr(self, 'boll') else None
        bb_middle = self.boll.lines.mid[0] if hasattr(self, 'boll') else None
        bb_upper = self.boll.lines.top[0] if hasattr(self, 'boll') else None
        atr_val = self.atr[0] if hasattr(self, 'atr') else None
        st_val = self.supertrend.lines.supertrend[0] if hasattr(self, 'supertrend') else None
        st_dir = self.supertrend.lines.direction[0] if hasattr(self, 'supertrend') else None
        vol_ma_val = self.vol_ma[0] if hasattr(self, 'vol_ma') else None
        volume = self.data.volume[0] if hasattr(self.data, 'volume') else None
        trade_dict = {
            'symbol': trade.data._name if hasattr(trade.data, '_name') else 'UNKNOWN',
            'ref': trade.ref,
            'entry_time': bt.num2date(trade.dtopen) if trade.dtopen else None,
            'entry_price': entry_price,
            'direction': direction,
            'exit_time': bt.num2date(trade.dtclose) if trade.dtclose else None,
            'exit_price': exit_price,
            'exit_reason': self.last_exit_reason,
            'pnl': trade.pnl, 'pnl_comm': trade.pnlcomm,
            'size': trade.size, 'value': trade.value,
            'commission': trade.commission,
            # Indicator values at exit
            'bb_lower_at_exit': bb_lower,
            'bb_middle_at_exit': bb_middle,
            'bb_upper_at_exit': bb_upper,
            'atr_at_exit': atr_val,
            'supertrend_val_at_exit': st_val,
            'supertrend_dir_at_exit': st_dir,
            'volume_at_exit': volume,
            'vol_ma_at_exit': vol_ma_val
        }
        if 'pnl_comm' not in trade_dict or trade_dict['pnl_comm'] is None:
            trade_dict['pnl_comm'] = trade_dict['pnl']
        self.record_trade(trade_dict)
        self.last_exit_reason = None
        self.trade_active = False
        self.entry_price = None
        self.active_tp_price = None
        self.active_sl_price = None
        self.last_exit_price = None


    def next(self):
        if self.order: # If an order is pending, do not send another
            return

        close = self.data.close[0]
        volume = self.data.volume[0]
        
        # Ensure all indicators have enough data
        if len(self.supertrend.lines.supertrend) < 1 or self.supertrend.lines.direction[0] == 0:
             self.log(f"Supertrend not ready or direction is 0. ST Direction: {self.supertrend.lines.direction[0] if len(self.supertrend.lines.supertrend) > 0 else 'N/A'}")
             return
        if len(self.vol_ma.lines.sma) < 1:
            self.log("Volume MA not ready.")
            return
        if len(self.boll.lines.top) < 1: # Check if BB is ready
            self.log("Bollinger Bands not ready.")
            return

        st_direction = self.supertrend.lines.direction[0]
        vol_ma_val = self.vol_ma[0]
        bb_top = self.boll.lines.top[0]
        bb_bot = self.boll.lines.bot[0]
        bb_mid = self.boll.lines.mid[0]
        atr_val = self.atr[0] # Current ATR for exits if needed, entry TP/SL uses ATR at entry

        # Check if in a position
        if not self.position: # Not in position, check for entry
            self.trade_active = False # Ensure flag is false if not in position
            # Long Entry Condition
            if close > bb_top and st_direction == 1 and volume > (vol_ma_val * self.params.get('vol_strength_mult', 3.0)):
                self.log(f'LONG ENTRY SIGNAL: Close {close:.2f} > BB Top {bb_top:.2f}, ST Green, Vol {volume:.0f} > MA*Mult {vol_ma_val * self.params.get('vol_strength_mult', 3.0):.0f}')
                self.entry_bar = self.datas[0].datetime.idx # Bar index of signal
                self.order = self.buy()
                self.trade_active = True # Mark that we are attempting to enter a trade
                # TP/SL will be set in notify_order upon execution based on ATR at self.entry_bar
            # No short entry logic
        else: # In a position, check for exit
            self.trade_active = True # Should already be true, but ensure
            # Exit Logic
            exit_signal = False
            exit_reason = ""

            if self.position.size > 0: # In a long position
                # 1. Price closes back inside Bollinger Bands (below upper band)
                if close < bb_top:
                    exit_signal = True
                    exit_reason = "Long Exit: Close back inside BB Top"
                # 2. SuperTrend flips against position (turns red)
                elif st_direction == -1:
                    exit_signal = True
                    exit_reason = "Long Exit: SuperTrend flipped to Red"
                # 3. Fixed TP/SL
                elif self.active_tp_price and close >= self.active_tp_price:
                    exit_signal = True
                    exit_reason = f"Long Exit: Take Profit hit at {self.active_tp_price:.2f}"
                elif self.active_sl_price and close <= self.active_sl_price:
                    exit_signal = True
                    exit_reason = f"Long Exit: Stop Loss hit at {self.active_sl_price:.2f}"
            # No short position/exit logic
            if exit_signal:
                self.last_exit_reason = exit_reason
                self.log(f'EXIT SIGNAL: {exit_reason}. Closing position.')
                self.order = self.close() # Close position
                # self.trade_active is reset in notify_order or notify_trade


# Example usage (for testing, normally run via a main script)
if __name__ == '__main__':
    cerebro = bt.Cerebro()
    cerebro.addstrategy(BBSuperTrendVolumeBreakoutStrategy, printlog=True)

    # Create a dummy data feed
    data_dict = {
        'datetime': pd.to_datetime(['2023-01-01T00:00:00', '2023-01-01T01:00:00', '2023-01-01T02:00:00', 
                                     '2023-01-01T03:00:00', '2023-01-01T04:00:00', '2023-01-01T05:00:00',
                                     '2023-01-01T06:00:00', '2023-01-01T07:00:00', '2023-01-01T08:00:00',
                                     '2023-01-01T09:00:00', '2023-01-01T10:00:00', '2023-01-01T11:00:00',
                                     '2023-01-01T12:00:00', '2023-01-01T13:00:00', '2023-01-01T14:00:00',
                                     '2023-01-01T15:00:00', '2023-01-01T16:00:00', '2023-01-01T17:00:00',
                                     '2023-01-01T18:00:00', '2023-01-01T19:00:00', '2023-01-01T20:00:00'
                                     ] * 5), # Repeat to get enough data points
        'open': np.random.rand(21*5) * 10 + 100,
        'high': np.random.rand(21*5) * 12 + 102, # ensure high > open
        'low': np.random.rand(21*5) * 8 + 98,   # ensure low < open
        'close': np.random.rand(21*5) * 10 + 100,
        'volume': np.random.rand(21*5) * 1000 + 100
    }
    # Ensure high is max and low is min
    data_dict['high'] = np.maximum(data_dict['high'], data_dict['open'])
    data_dict['high'] = np.maximum(data_dict['high'], data_dict['close'])
    data_dict['low'] = np.minimum(data_dict['low'], data_dict['open'])
    data_dict['low'] = np.minimum(data_dict['low'], data_dict['close'])

    df = pd.DataFrame(data_dict)
    df.set_index('datetime', inplace=True)

    data_feed = bt.feeds.PandasData(dataname=df)
    cerebro.adddata(data_feed)
    cerebro.broker.setcash(10000.0)
    cerebro.broker.setcommission(commission=0.001) # Example commission
    
    print('Starting Portfolio Value: %.2f' % cerebro.broker.getvalue())
    cerebro.run()
    print('Final Portfolio Value: %.2f' % cerebro.broker.getvalue())
    
    # Access trades from the strategy instance if needed
    # strategy_instance = cerebro.runstrats[0][0] 
    # print(pd.DataFrame(strategy_instance.trades))

# Removed old BollVolumeSupertrendStrategy class and its remnants
# Kept the custom SuperTrend indicator
# Implemented BBSuperTrendVolumeBreakoutStrategy with new logic
# Added basic example usage for testing
# Simplified trade logging and notification handling for now
