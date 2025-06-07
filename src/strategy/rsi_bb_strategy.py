import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import backtrader as bt
import pandas as pd
import numpy as np
from src.strategy.base_strategy import BaseStrategy, get_exit_class
from typing import Any, Dict, Optional

"""
RSI Bollinger Bands Strategy Module
----------------------------------

This module implements a mean-reversion trading strategy using Bollinger Bands, RSI, and pluggable exit logic. The strategy is designed for ranging or sideways markets and can be used for both backtesting and live trading. It provides entry and exit logic, position management, and trade recording.

Main Features:
- Entry and exit signals based on Bollinger Bands and RSI
- Pluggable exit logic system for flexible position management
- Designed for use with Backtrader and compatible with other trading frameworks

Classes:
- MeanReversionRsiBbStrategy: Main strategy class implementing the logic
"""

class MeanReversionRsiBbStrategy(BaseStrategy):
    """
    A mean-reversion strategy using Bollinger Bands, RSI, and pluggable exit logic.
    Accepts a single params/config dictionary.
    
    Use Case:
    Ranging/sideways markets (e.g., forex pairs, altcoins)
    Timeframes: 5m to 4H (too slow on daily)
    Strengths: High win rate when market is sideways
    Weaknesses: Easily whipsawed during breakouts

    Indicators:
    - Bollinger Bands (BB): Identifies potential overextension from the mean.
    - Relative Strength Index (RSI): Confirms oversold/overbought conditions.

    Entry Logic:
    - Long:
        - Price closes below the lower Bollinger Band.
        - RSI is below the oversold level (e.g., 30), ideally showing signs of turning up.
    - Short:
        - Price closes above the upper Bollinger Band.
        - RSI is above the overbought level (e.g., 70), ideally showing signs of turning down.

    Exit Logic:
    - Pluggable exit logic system with multiple options:
        - ATR-based exits (atr_exit): Uses ATR for dynamic take profit and stop loss
        - Fixed take profit/stop loss (fixed_tp_sl_exit): Uses fixed price levels
        - Moving average crossover (ma_crossover_exit): Exits on MA crossovers
        - Time-based exits (time_based_exit): Exits after a fixed number of bars
        - Trailing stop exits (trailing_stop_exit): Uses trailing stop loss
    
    Parameters:
        bb_period (int): Period for Bollinger Bands (default: 20)
        bb_devfactor (float): Standard deviation multiplier for Bollinger Bands (default: 2.0)
        rsi_period (int): Period for RSI calculation (default: 14)
        rsi_oversold (float): RSI oversold threshold (default: 30)
        rsi_overbought (float): RSI overbought threshold (default: 70)
        rsi_mid_level (float): RSI mid-level for exits (default: 50)
        exit_logic_name (str): Name of the exit logic to use (default: 'atr_exit')
        exit_params (dict): Parameters for the selected exit logic
        printlog (bool): Whether to print trade logs (default: False)
    """
    def __init__(self, params: dict):
        super().__init__(params)
        self.notify = self.params.get('notify', False)
        use_talib = self.params.get('use_talib', False)
        if use_talib:
            self.boll = bt.talib.BBANDS(timeperiod=self.params.get('bb_period', 20), nbdevup=self.params.get('bb_devfactor', 2.0), nbdevdn=self.params.get('bb_devfactor', 2.0))
            self.rsi = bt.talib.RSI(timeperiod=self.params.get('rsi_period', 14))
            self.atr = bt.talib.ATR(timeperiod=self.params.get('atr_period', 14))
        else:
            self.boll = bt.indicators.BollingerBands(
                period=self.params.get('bb_period', 20),
                devfactor=self.params.get('bb_devfactor', 2.0)
            )
            self.rsi = bt.indicators.RSI(period=self.params.get('rsi_period', 14))
            self.atr = bt.indicators.ATR(period=self.params.get('atr_period', 14))
            
        # Initialize exit logic
        exit_logic_name = self.params.get('exit_logic_name', 'atr_exit')
        exit_params = self.params.get('exit_params', {})
        exit_class = get_exit_class(exit_logic_name)
        self.exit_logic = exit_class(exit_params)
            
        self.order = None
        self.entry_price = None
        self.entry_bar_idx = None
        self.highest_price = None
        self.current_trade = None
        self.last_exit_reason = None

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return
        if order.status == order.Completed:
            if order.isbuy():
                self.log(f'BUY EXECUTED, Price: {order.executed.price:.2f}, Cost: {order.executed.value:.2f}, Comm: {order.executed.comm:.2f}')
                self.entry_price = order.executed.price
                self.highest_price = self.entry_price
                
                # Initialize exit logic with entry price and ATR
                atr_value = self.atr[0]
                self.exit_logic.initialize(self.entry_price, atr_value)
                
                if self.current_trade:
                    self.current_trade['entry_price'] = self.entry_price
            elif order.issell():
                if self.position.size == 0:
                    self.entry_price = None
                    self.highest_price = None
                    if self.current_trade:
                        self.current_trade['exit_price'] = order.executed.price
                        self.current_trade['exit_time'] = self.data.datetime.datetime(0)
                        self.current_trade['exit_reason'] = self.last_exit_reason
                        self.record_trade(self.current_trade)
                        self.current_trade = None
                    self.last_exit_reason = None
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log(f'Order Canceled/Margin/Rejected: {order.getstatusname()}')
            if not self.position:
                self.entry_price = None
                self.highest_price = None
        self.order = None

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
        atr_value = self.atr[0]
        
        if not self.position:
            rsi_is_rising = self.rsi[0] > self.rsi[-1] if len(self.rsi.lines.rsi) > 1 else False
            long_rsi_condition = rsi_is_rising if self.params.get('check_rsi_slope', False) else True
            if close < bb_lower and rsi_val < self.params.get('rsi_oversold', 30) and long_rsi_condition:
                self.log(f'LONG ENTRY SIGNAL: Close {close:.2f} < BB Low {bb_lower:.2f}, RSI {rsi_val:.2f} < {self.params.get("rsi_oversold", 30)}')
                self.entry_bar_idx = len(self)
                
                # Record trade details
                self.current_trade = {
                    'entry_time': self.data.datetime.datetime(0),
                    'entry_price': 'pending_long',
                    'atr_at_entry': atr_value,
                    'rsi_at_entry': rsi_val,
                    'bb_lower_at_entry': bb_lower,
                    'bb_middle_at_entry': bb_middle,
                    'type': 'long'
                }
                
                size = (self.broker.getvalue() * 0.1) / close
                self.order = self.buy(size=size)
        else:
            if self.position.size > 0:
                self.highest_price = max(self.highest_price, close)
                
                # Check exit conditions using the configured exit logic
                exit_signal, exit_reason = self.exit_logic.check_exit(close, self.highest_price, atr_value)
                
                if exit_signal:
                    self.last_exit_reason = exit_reason
                    self.order = self.close()
                    self.log(f'EXIT SIGNAL: {exit_reason}. Closing position.')
                    if self.current_trade:
                        self.current_trade.update({
                            'exit_time': self.data.datetime.datetime(0),
                            'exit_price': close,
                            'exit_reason': exit_reason,
                            'atr_at_exit': atr_value,
                            'rsi_at_exit': rsi_val,
                            'bb_lower_at_exit': bb_lower,
                            'bb_middle_at_exit': bb_middle
                        })

# Example Usage (for testing)
if __name__ == '__main__':
    cerebro = bt.Cerebro()
    cerebro.addstrategy(
        MeanReversionRsiBbStrategy,
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