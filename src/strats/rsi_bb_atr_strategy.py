import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import backtrader as bt
import pandas as pd
import numpy as np
from src.strats.base_strategy import BaseStrategy

class MeanReversionRSBBATRStrategy(BaseStrategy):
    """
    A mean-reversion strategy using Bollinger Bands, RSI, and ATR.
    
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
    params = (
        ('bb_period', 20),
        ('bb_devfactor', 2.0),
        ('rsi_period', 14),
        ('rsi_oversold', 30),
        ('rsi_overbought', 70),
        ('rsi_mid_level', 50), # Neutral RSI level for exits
        ('atr_period', 14),
        ('tp_atr_mult', 1.5), # Take Profit ATR multiplier
        ('sl_atr_mult', 1.0), # Stop Loss ATR multiplier
        ('trail_atr_mult', 2.0), # Trailing Stop ATR multiplier (NEW)
        ('printlog', False),   # For logging strategy actions
        ('check_rsi_slope', False), # Optional: check if RSI is rising/falling for entry
    )

    def __init__(self):
        super().__init__()
        self.boll = bt.indicators.BollingerBands(
            period=self.p.bb_period,
            devfactor=self.p.bb_devfactor
        )
        self.rsi = bt.indicators.RSI(period=self.p.rsi_period)
        self.atr = bt.indicators.ATR(period=self.p.atr_period)
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
                    self.active_tp_price = self.entry_price + self.p.tp_atr_mult * atr_at_entry_signal
                    self.active_sl_price = self.entry_price - self.p.sl_atr_mult * atr_at_entry_signal
                    self.log(f'BUY TP: {self.active_tp_price:.2f}, SL: {self.active_sl_price:.2f}, ATR@EntrySignal: {atr_at_entry_signal:.2f}')
                    self.highest_close = self.entry_price
                    self.trailing_stop = self.entry_price - self.p.trail_atr_mult * atr_at_entry_signal
                    self.log(f'Trailing Stop set at {self.trailing_stop:.2f} (ATR x {self.p.trail_atr_mult})')
                else:
                    self.log('BUY: ATR invalid, TP/SL not set.')
                    self.active_tp_price = None; self.active_sl_price = None;
                    self.highest_close = None; self.trailing_stop = None;
            elif order.issell():
                if self.position.size == 0:
                    self.entry_price = None
                    self.active_tp_price = None
                    self.active_sl_price = None
                    self.entry_bar_idx = None
                    self.last_exit_price = order.executed.price
                    self.last_exit_dt = bt.num2date(order.executed.dt).isoformat() if hasattr(order.executed, 'dt') else None
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
        trade_dict = {
            'ref': trade.ref, 'symbol': self.data._name,
            'entry_dt': bt.num2date(trade.dtopen).isoformat() if trade.dtopen else None,
            'entry_price': trade.price, 
            'direction': 'long',
            'exit_dt': getattr(self, 'last_exit_dt', bt.num2date(trade.dtclose).isoformat() if trade.dtclose else None),
            'exit_price': getattr(self, 'last_exit_price', None),
            'pnl': trade.pnl, 'pnl_comm': trade.pnlcomm,
            'size': trade.size
        }
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
        if (len(self.rsi.lines.rsi) < self.p.rsi_period or
            len(self.boll.lines.bot) < self.p.bb_period or
            len(self.atr.lines.atr) < self.p.atr_period):
            self.log("Indicators not ready yet.")
            return
        bb_lower = self.boll.lines.bot[0]
        bb_middle = self.boll.lines.mid[0]
        if not self.position:
            rsi_is_rising = self.rsi[0] > self.rsi[-1] if len(self.rsi.lines.rsi) > 1 else False
            long_rsi_condition = rsi_is_rising if self.p.check_rsi_slope else True
            if close < bb_lower and rsi_val < self.p.rsi_oversold and long_rsi_condition:
                self.log(f'LONG ENTRY SIGNAL: Close {close:.2f} < BB Low {bb_lower:.2f}, RSI {rsi_val:.2f} < {self.p.rsi_oversold}')
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
                elif rsi_val > self.p.rsi_mid_level:
                    exit_signal = True
                    exit_reason = f"Long Exit: RSI {rsi_val:.2f} crossed above Mid Level {self.p.rsi_mid_level}"
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
    cerebro.addstrategy(MeanReversionRSBBATRStrategy, printlog=True, check_rsi_slope=True)

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
