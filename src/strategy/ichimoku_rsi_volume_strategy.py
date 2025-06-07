import backtrader as bt
from src.strategy.base_strategy import BaseStrategy, get_exit_class
import datetime
from typing import Any, Dict, Optional

"""
Ichimoku RSI Volume Strategy Module
----------------------------------

This module implements a trend-following trading strategy using Ichimoku Cloud, RSI, and Volume indicators with pluggable exit logic. The strategy is designed for use with Backtrader and can be used for both backtesting and live trading.

Main Features:
- Entry and exit signals based on Ichimoku Cloud, RSI, and Volume
- Pluggable exit logic system for flexible position management
- Designed for use with Backtrader and compatible with other trading frameworks

Classes:
- IchimokuRsiVolumeStrategy: Main strategy class implementing the logic
"""

class IchimokuRsiVolumeStrategy(BaseStrategy):
    """
    Trend-following strategy using Ichimoku Cloud, RSI, Volume, and pluggable exit logic.
    Accepts a single params/config dictionary.

    Indicators:
    - Ichimoku Cloud: Determines trend direction and support/resistance levels
    - RSI: Identifies momentum and potential reversals
    - Volume: Confirms entry and exit signals

    Entry Logic:
    - Long:
        - Price above Ichimoku Cloud
        - Tenkan-sen crosses above Kijun-sen
        - RSI above entry level
        - Volume above its moving average
    - Short:
        - Price below Ichimoku Cloud
        - Tenkan-sen crosses below Kijun-sen
        - RSI below entry level
        - Volume above its moving average

    Exit Logic:
    - Pluggable exit logic system with multiple options:
        - ATR-based exits (atr_exit): Uses ATR for dynamic take profit and stop loss
        - Fixed take profit/stop loss (fixed_tp_sl_exit): Uses fixed price levels
        - Moving average crossover (ma_crossover_exit): Exits on MA crossovers
        - Time-based exits (time_based_exit): Exits after a fixed number of bars
        - Trailing stop exits (trailing_stop_exit): Uses trailing stop loss

    Parameters:
        tenkan_period (int): Period for Tenkan-sen calculation (default: 9)
        kijun_period (int): Period for Kijun-sen calculation (default: 26)
        senkou_span_b_period (int): Period for Senkou Span B calculation (default: 52)
        rsi_period (int): Period for RSI calculation (default: 14)
        rsi_entry (float): RSI entry threshold (default: 50)
        vol_ma_period (int): Period for Volume Moving Average (default: 20)
        exit_logic_name (str): Name of the exit logic to use (default: 'atr_exit')
        exit_params (dict): Parameters for the selected exit logic
        printlog (bool): Whether to print trade logs (default: False)
    """
    def __init__(self, params: dict):
        super().__init__(params)
        self.notify = self.params.get('notify', False)
        use_talib = self.params.get('use_talib', False)
        
        # Initialize indicators based on use_talib flag
        if use_talib:
            # TA-Lib indicators
            self.tenkan = bt.talib.SMA(self.data.close, timeperiod=self.params['tenkan_period'])
            self.kijun = bt.talib.SMA(self.data.close, timeperiod=self.params['kijun_period'])
            self.senkou_span_b = bt.talib.SMA(self.data.close, timeperiod=self.params['senkou_span_b_period'])
            self.rsi = bt.talib.RSI(self.data.close, timeperiod=self.params['rsi_period'])
            self.atr = bt.talib.ATR(
                self.data.high,
                self.data.low,
                self.data.close,
                timeperiod=self.params['atr_period']
            )
            self.vol_ma = bt.talib.SMA(self.data.volume, timeperiod=self.params['vol_ma_period'])
        else:
            # Backtrader built-in indicators
            self.tenkan = bt.ind.SMA(self.data.close, period=self.params['tenkan_period'])
            self.kijun = bt.ind.SMA(self.data.close, period=self.params['kijun_period'])
            self.senkou_span_b = bt.ind.SMA(self.data.close, period=self.params['senkou_span_b_period'])
            self.rsi = bt.ind.RSI(period=self.params['rsi_period'])
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
        self.position_type = None
        self.last_exit_reason = None

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return
        if order.status == order.Completed:
            if order.isbuy():
                self.log(f'BUY EXECUTED, Price: {order.executed.price:.2f}, Cost: {order.executed.value:.2f}, Comm: {order.executed.comm:.2f}')
                self.entry_price = order.executed.price
                self.highest_price = self.entry_price
                self.position_type = 'long'
                
                # Initialize exit logic with entry price and ATR
                atr_value = self.atr[0]
                self.exit_logic.initialize(self.entry_price, atr_value)
                
                if self.current_trade:
                    self.current_trade['entry_price'] = self.entry_price
            elif order.issell():
                if self.position.size == 0:
                    self.entry_price = None
                    self.highest_price = None
                    self.position_type = None
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
                self.position_type = None
        self.order = None

    def next(self):
        if self.order:
            return
        close = self.data.close[0]
        volume = self.data.volume[0]
        tenkan = self.tenkan[0]
        kijun = self.kijun[0]
        senkou_span_b = self.senkou_span_b[0]
        rsi = self.rsi[0]
        atr = self.atr[0]
        vol_ma = self.vol_ma[0]
        
        # Calculate Ichimoku Cloud levels
        senkou_span_a = (tenkan + kijun) / 2
        cloud_top = max(senkou_span_a, senkou_span_b)
        cloud_bot = min(senkou_span_a, senkou_span_b)
        
        if not self.position:
            # Entry Logic
            if (close > cloud_top and
                tenkan > kijun and
                rsi > self.params['rsi_entry'] and
                volume > vol_ma):
                
                self.log(f'LONG ENTRY SIGNAL: Close {close:.2f} > Cloud Top {cloud_top:.2f}, RSI {rsi:.2f} > {self.params["rsi_entry"]}, Volume {volume:.2f} > MA {vol_ma:.2f}')
                
                # Record trade details
                self.current_trade = {
                    'entry_time': self.data.datetime.datetime(0),
                    'entry_price': 'pending_long',
                    'atr_at_entry': atr,
                    'rsi_at_entry': rsi,
                    'volume_at_entry': volume,
                    'vol_ma_at_entry': vol_ma,
                    'tenkan_at_entry': tenkan,
                    'kijun_at_entry': kijun,
                    'senkou_a_at_entry': senkou_span_a,
                    'senkou_b_at_entry': senkou_span_b,
                    'cloud_top_at_entry': cloud_top,
                    'cloud_bot_at_entry': cloud_bot,
                    'type': 'long'
                }
                
                size = (self.broker.getvalue() * 0.1) / close
                self.order = self.buy(size=size)
        else:
            if self.position.size > 0:
                self.highest_price = max(self.highest_price, close)
                
                # Check exit conditions using the configured exit logic
                exit_signal, exit_reason = self.exit_logic.check_exit(close, self.highest_price, atr)
                
                if exit_signal:
                    self.last_exit_reason = exit_reason
                    self.order = self.close()
                    self.log(f'EXIT SIGNAL: {exit_reason}. Closing position.')
                    if self.current_trade:
                        self.current_trade.update({
                            'exit_time': self.data.datetime.datetime(0),
                            'exit_price': close,
                            'exit_reason': exit_reason,
                            'atr_at_exit': atr,
                            'rsi_at_exit': rsi,
                            'volume_at_exit': volume,
                            'vol_ma_at_exit': vol_ma,
                            'tenkan_at_exit': tenkan,
                            'kijun_at_exit': kijun,
                            'senkou_a_at_exit': senkou_span_a,
                            'senkou_b_at_exit': senkou_span_b,
                            'cloud_top_at_exit': cloud_top,
                            'cloud_bot_at_exit': cloud_bot
                        }) 