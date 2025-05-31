import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import backtrader as bt
import pandas as pd
import numpy as np
from src.strats.base_strategy import BaseStrategy
import datetime
from typing import Any, Dict, Optional

"""
RSI Bollinger Bands ATR Strategy Module
--------------------------------------

This module implements a mean-reversion trading strategy using Bollinger Bands, RSI, and ATR. The strategy is designed for ranging or sideways markets and can be used for both backtesting and live trading. It provides entry and exit logic, position management, and trade recording.

Main Features:
- Entry and exit signals based on Bollinger Bands, RSI, and ATR
- Position and risk management using ATR-based stop loss and take profit
- Designed for use with Backtrader and compatible with other trading frameworks

Classes:
- MeanReversionRSBBATRStrategy: Main strategy class implementing the logic
"""

class MeanReversionRSBBATRStrategy(BaseStrategy):
    """
    A mean-reversion strategy using Bollinger Bands, RSI, and ATR.
    Accepts a single params/config dictionary.
    
    Use Case:
    Ranging/sideways markets (e.g., forex pairs, altcoins)
    Timeframes: 5m to 4H (too slow on daily)
    Strengths: High win rate when market is sideways
    Weaknesses: Easily whipsawed during breakouts

    Indicators:
    - Bollinger Bands (BB): Identifies potential overextension from the mean.
    - Relative Strength Index (RSI): Confirms oversold/overbought conditions.
    - Average True Range (ATR): Sets stop-loss and take-profit levels based on volatility.

    Entry Logic:
    - Long:
        - Price closes below the lower Bollinger Band.
        - RSI is below the oversold level (e.g., 30), ideally showing signs of turning up.
    - Short:
        - Price closes above the upper Bollinger Band.
        - RSI is above the overbought level (e.g., 70), ideally showing signs of turning down.

    Exit Logic:
    - Price reverts to the mean (middle Bollinger Band).
    - RSI crosses a neutral level (e.g., 50).
    - Fixed Take Profit (TP) or Stop Loss (SL) is hit, based on ATR multiples.
    
    Use Case:
        Suited for ranging or sideways markets. Can be effective on various timeframes
        from 5m to 4H. May underperform in strong trending markets due to premature exits
        or fighting the trend.
    """
    def __init__(self, params: dict):
        super().__init__(params)
        self.notify = self.params.get('notify', False)
        self.boll = bt.indicators.BollingerBands(
            period=self.params.get('bb_period', 20),
            devfactor=self.params.get('bb_devfactor', 2.0)
        )
        self.rsi = bt.indicators.RSI(period=self.params.get('rsi_period', 14))
        self.atr = bt.indicators.ATR(period=self.params.get('atr_period', 14))
        self.order = None
        self.entry_price = None
        self.entry_bar_idx = None
        self.active_tp_price = None
        self.active_sl_price = None
        self.last_exit_price = None
        self.last_exit_dt = None
        self.highest_close = None
        self.trailing_stop = None

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return
        if order.status == order.Completed:
            current_bar_idx = len(self)
            atr_at_entry_signal = self.atr[-(current_bar_idx - self.entry_bar_idx)] if self.entry_bar_idx is not None else self.atr[0]
            if atr_at_entry_signal <= 0:
                self.log(f'Warning: ATR at entry is {atr_at_entry_signal:.2f}. Using current ATR: {self.atr[0]:.2f}')
                atr_at_entry_signal = self.atr[0]
                if atr_at_entry_signal <=0:
                     self.log('Error: ATR is still zero or invalid. TP/SL will not be set.')
                     self.active_tp_price = None
                     self.active_sl_price = None
            if order.isbuy():
                self.log(f'BUY EXECUTED, Price: {order.executed.price:.2f}, Cost: {order.executed.value:.2f}, Comm: {order.executed.comm:.2f}')
                self.entry_price = order.executed.price
                if atr_at_entry_signal > 0:
                    self.active_tp_price = self.entry_price + self.params.get('tp_atr_mult', 1.5) * atr_at_entry_signal
                    self.active_sl_price = self.entry_price - self.params.get('sl_atr_mult', 1.0) * atr_at_entry_signal
                    self.log(f'BUY TP: {self.active_tp_price:.2f}, SL: {self.active_sl_price:.2f}, ATR@EntrySignal: {atr_at_entry_signal:.2f}')
                    self.highest_close = self.entry_price
                    self.trailing_stop = self.entry_price - self.params.get('trail_atr_mult', 2.0) * atr_at_entry_signal
                    self.log(f'Trailing Stop set at {self.trailing_stop:.2f} (ATR x {self.params.get("trail_atr_mult", 2.0)})')
                else:
                    self.log('BUY: ATR invalid, TP/SL not set.')
                    self.active_tp_price = None
                    self.active_sl_price = None
                    self.highest_close = None
                    self.trailing_stop = None
            elif order.issell():
                if self.position.size == 0:
                    self.entry_price = None
                    self.active_tp_price = None
                    self.active_sl_price = None
                    self.entry_bar_idx = None
                    self.last_exit_price = order.executed.price
                    self.last_exit_dt = bt.num2date(order.executed.dt) if hasattr(order.executed, 'dt') else None
                    self.highest_close = None
                    self.trailing_stop = None
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log(f'Order Canceled/Margin/Rejected: {order.getstatusname()}')
            if not self.position:
                self.entry_price = None
                self.active_tp_price = None
                self.active_sl_price = None
                self.entry_bar_idx = None
        self.order = None

    def notify_trade(self, trade):
        if not trade.isclosed:
            return
        self.log(f'TRADE CLOSED, PNL GROSS {trade.pnl:.2f}, PNL NET {trade.pnlcomm:.2f}')
        # Get current indicator values
        rsi_val = self.rsi[0] if hasattr(self, 'rsi') else None
        bb_lower = self.boll.lines.bot[0] if hasattr(self, 'boll') else None
        bb_middle = self.boll.lines.mid[0] if hasattr(self, 'boll') else None
        bb_upper = self.boll.lines.top[0] if hasattr(self, 'boll') else None
        atr_val = self.atr[0] if hasattr(self, 'atr') else None
        trade_dict = {
            'symbol': self.data._name if hasattr(self.data, '_name') else 'UNKNOWN',
            'ref': trade.ref,
            'entry_time': bt.num2date(trade.dtopen) if trade.dtopen else None,
            'entry_price': trade.price, 
            'direction': 'long',
            'exit_time': getattr(self, 'last_exit_dt', bt.num2date(trade.dtclose) if trade.dtclose else None),
            'exit_price': getattr(self, 'last_exit_price', None),
            'pnl': trade.pnl, 'pnl_comm': trade.pnlcomm,
            'size': trade.size,
            # Add indicator values
            'rsi_at_exit': rsi_val,
            'bb_lower_at_exit': bb_lower,
            'bb_middle_at_exit': bb_middle,
            'bb_upper_at_exit': bb_upper,
            'atr_at_exit': atr_val
        }
        if 'pnl_comm' not in trade_dict or trade_dict['pnl_comm'] is None:
            trade_dict['pnl_comm'] = trade_dict['pnl']
        self.record_trade(trade_dict)
        self.last_exit_price = None
        self.last_exit_dt = None
        self.entry_price = None
        self.active_tp_price = None
        self.active_sl_price = None
        self.entry_bar_idx = None
        self.highest_close = None
        self.trailing_stop = None

    def next(self):
        if self.order:
            return
        close = self.data.close[0]
        rsi_val = self.rsi[0]
        if (len(self.rsi.lines.rsi) < self.params.get('rsi_period', 14) or
            len(self.boll.lines.bot) < self.params.get('bb_period', 20) or
            len(self.atr.lines.atr) < self.params.get('atr_period', 14)):
            self.log("Indicators not ready yet.")
            return
        bb_lower = self.boll.lines.bot[0]
        bb_middle = self.boll.lines.mid[0]
        if not self.position:
            rsi_is_rising = self.rsi[0] > self.rsi[-1] if len(self.rsi.lines.rsi) > 1 else False
            long_rsi_condition = rsi_is_rising if self.params.get('check_rsi_slope', False) else True
            if close < bb_lower and rsi_val < self.params.get('rsi_oversold', 30) and long_rsi_condition:
                self.log(f'LONG ENTRY SIGNAL: Close {close:.2f} < BB Low {bb_lower:.2f}, RSI {rsi_val:.2f} < {self.params.get("rsi_oversold", 30)}')
                self.entry_bar_idx = len(self)
                size = (self.broker.getvalue() * 0.1) / close
                self.order = self.buy(size=size)
        else:
            exit_signal = False
            exit_reason = ""
            if self.position.size > 0:
                if close >= bb_middle:
                    exit_signal = True
                    exit_reason = "Long Exit: Reverted to Middle BB"
                elif rsi_val > self.params.get('rsi_mid_level', 50):
                    exit_signal = True
                    exit_reason = f"Long Exit: RSI {rsi_val:.2f} crossed above Mid Level {self.params.get('rsi_mid_level', 50)}"
                elif self.active_tp_price and close >= self.active_tp_price:
                    exit_signal = True
                    exit_reason = f"Long Exit: Take Profit hit at {self.active_tp_price:.2f}"
                elif self.active_sl_price and close <= self.active_sl_price:
                    exit_signal = True
                    exit_reason = f"Long Exit: Stop Loss hit at {self.active_sl_price:.2f}"
            if exit_signal:
                self.log(f'EXIT SIGNAL: {exit_reason}. Closing position.')
                self.order = self.close()

# Example Usage (for testing)
if __name__ == '__main__':
    cerebro = bt.Cerebro()
    cerebro.addstrategy(
        MeanReversionRSBBATRStrategy,
        {
            "printlog": True,
            "check_rsi_slope": True,
            # add other params here as needed
        }
    )

    # Create dummy data
    data_len = 200
    data_dict = {
        'datetime': pd.to_datetime([pd.Timestamp('2023-01-01') + pd.Timedelta(hours=i) for i in range(data_len)]),
        'open': np.random.rand(data_len) * 10 + 100,
        'high': np.random.rand(data_len) * 5 + 105, # open + range
        'low': np.random.rand(data_len) * -5 + 100, # open - range
        'close': np.random.rand(data_len) * 10 + 100,
        'volume': np.random.randint(100, 1000, size=data_len)
    }
    # Ensure High >= Open/Close and Low <= Open/Close
    data_dict['high'] = np.maximum.reduce([data_dict['high'], data_dict['open'], data_dict['close']])
    data_dict['low'] = np.minimum.reduce([data_dict['low'], data_dict['open'], data_dict['close']])

    df = pd.DataFrame(data_dict)
    df.set_index('datetime', inplace=True)

    data_feed = bt.feeds.PandasData(dataname=df)
    cerebro.adddata(data_feed)
    cerebro.broker.setcash(10000.0)
    cerebro.broker.setcommission(commission=0.001)
    
    print('Starting Portfolio Value: %.2f' % cerebro.broker.getvalue())
    cerebro.run()
    print('Final Portfolio Value: %.2f' % cerebro.broker.getvalue())

    # Access trades from the strategy instance if needed for analysis after run
    # if cerebro.runstrats and cerebro.runstrats[0]:
    #     strategy_instance = cerebro.runstrats[0][0]
    #     final_trades_df = pd.DataFrame(strategy_instance.trades)
    #     if not final_trades_df.empty:
    #         print("\nFinal Trades Log:\n", final_trades_df.to_string())
    #     else:
    #         print("\nNo trades were logged.")
