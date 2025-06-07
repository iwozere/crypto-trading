"""
Liquidity Momentum Strategy Module
--------------------------------

This module implements a momentum-based trading strategy using volume profile, price action, and liquidity analysis with pluggable exit logic. The strategy is designed for use with Backtrader and can be used for both backtesting and live trading.

Main Features:
- Entry signals based on volume profile and price action
- Liquidity analysis for trade management
- Pluggable exit logic system for flexible position management
- Designed for use with Backtrader and compatible with other trading frameworks

Classes:
- LiquidityMomentumStrategy: Main strategy class implementing the logic
"""

import backtrader as bt
import numpy as np
import pandas as pd
from src.strategy.base_strategy import BaseStrategy, get_exit_class

class LiquidityMomentumStrategy(BaseStrategy):
    """
    Momentum-based strategy using volume profile, price action, liquidity analysis, and pluggable exit logic.
    Accepts a single params/config dictionary.

    Indicators:
    - Volume Profile: Identifies key price levels and liquidity zones
    - Price Action: Determines entry and exit points
    - Liquidity Analysis: Manages trade risk and position sizing

    Entry Logic:
    - Long:
        - Price breaks above key resistance with volume confirmation
        - Liquidity analysis shows favorable risk/reward
    - Short:
        - Price breaks below key support with volume confirmation
        - Liquidity analysis shows favorable risk/reward

    Exit Logic:
    - Pluggable exit logic system with multiple options:
        - ATR-based exits (atr_exit): Uses ATR for dynamic take profit and stop loss
        - Fixed take profit/stop loss (fixed_tp_sl_exit): Uses fixed price levels
        - Moving average crossover (ma_crossover_exit): Exits on MA crossovers
        - Time-based exits (time_based_exit): Exits after a fixed number of bars
        - Trailing stop exits (trailing_stop_exit): Uses trailing stop loss
    """
    def __init__(self, params: dict):
        super().__init__(params)
        self.notify = self.params.get('notify', False)
        use_talib = self.params.get('use_talib', False)
        
        # Initialize indicators based on use_talib flag
        if use_talib:
            # TA-Lib indicators
            self.atr = bt.talib.ATR(
                self.data.high,
                self.data.low,
                self.data.close,
                timeperiod=self.params['atr_period']
            )
            self.vol_ma = bt.talib.SMA(self.data.volume, timeperiod=self.params['vol_ma_period'])
        else:
            # Backtrader built-in indicators
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
        volume = self.data.volume[0]
        atr_val = self.atr[0]
        vol_ma_val = self.vol_ma[0]
        
        if not self.position:
            # Entry Logic
            if (volume > vol_ma_val * self.params['volume_threshold'] and
                self.check_liquidity_conditions()):
                
                self.log(f'LONG ENTRY SIGNAL: Volume {volume:.2f} > MA {vol_ma_val:.2f}, Liquidity conditions met')
                
                # Record trade details
                self.current_trade = {
                    'entry_time': self.data.datetime.datetime(0),
                    'entry_price': 'pending_long',
                    'atr_at_entry': atr_val,
                    'volume_at_entry': volume,
                    'vol_ma_at_entry': vol_ma_val,
                    'type': 'long'
                }
                
                size = (self.broker.getvalue() * 0.1) / close
                self.order = self.buy(size=size)
        else:
            if self.position.size > 0:
                self.highest_price = max(self.highest_price, close)
                
                # Check exit conditions using the configured exit logic
                exit_signal, exit_reason = self.exit_logic.check_exit(close, self.highest_price, atr_val)
                
                if exit_signal:
                    self.last_exit_reason = exit_reason
                    self.order = self.close()
                    self.log(f'EXIT SIGNAL: {exit_reason}. Closing position.')
                    if self.current_trade:
                        self.current_trade.update({
                            'exit_time': self.data.datetime.datetime(0),
                            'exit_price': close,
                            'exit_reason': exit_reason,
                            'atr_at_exit': atr_val,
                            'volume_at_exit': volume,
                            'vol_ma_at_exit': vol_ma_val
                        })

    def check_liquidity_conditions(self):
        """
        Check if liquidity conditions are favorable for entry.
        Returns True if conditions are met, False otherwise.
        """
        # Implement your liquidity analysis logic here
        return True  # Placeholder implementation 