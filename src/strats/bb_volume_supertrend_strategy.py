import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))


import backtrader as bt
import pandas as pd
import numpy as np
# from src.notification.telegram import create_notifier # Temporarily commented out

# Custom SuperTrend Indicator
class SuperTrend(bt.Indicator):
    lines = ('supertrend', 'direction',) # supertrend line and direction (-1 for short, 1 for long)
    params = (('period', 10), ('multiplier', 3.0),)

    def __init__(self):
        self.atr = bt.indicators.ATR(self.datas[0], period=self.p.period)
        # Basic Upper Band = (High + Low) / 2 + Multiplier * ATR
        # Basic Lower Band = (High + Low) / 2 - Multiplier * ATR
        self.basic_ub = ((self.datas[0].high + self.datas[0].low) / 2) + self.p.multiplier * self.atr
        self.basic_lb = ((self.datas[0].high + self.datas[0].low) / 2) - self.p.multiplier * self.atr

        # Final Upper Band and Final Lower Band
        self.final_ub = bt.indicators.Max(self.basic_ub) # Placeholder, logic will be in next
        self.final_lb = bt.indicators.Min(self.basic_lb) # Placeholder, logic will be in next
        # Do not assign to self.lines.direction[0] or self.lines.supertrend[0] here

    def next(self):
        # If ATR is not yet valid, do nothing or carry forward
        if len(self.atr.lines.atr) < self.p.period or len(self) < 2:
            self.lines.supertrend[0] = np.nan
            self.lines.direction[0] = 0 # Undefined
            return

        # Calculate current final upper and lower bands
        # Only use negative indices if len(self) > 1
        prev_final_ub = self.final_ub[-1] if len(self) > 1 else self.basic_ub[0]
        prev_final_lb = self.final_lb[-1] if len(self) > 1 else self.basic_lb[0]
        prev_close = self.datas[0].close[-1] if len(self) > 1 else self.datas[0].close[0]

        if self.basic_ub[0] < prev_final_ub or prev_close > prev_final_ub:
            self.final_ub[0] = self.basic_ub[0]
        else:
            self.final_ub[0] = prev_final_ub

        if self.basic_lb[0] > prev_final_lb or prev_close < prev_final_lb:
            self.final_lb[0] = self.basic_lb[0]
        else:
            self.final_lb[0] = prev_final_lb
        
        # Set initial direction if it's undefined (first proper calculation)
        if self.lines.direction[-1] == 0:
            if self.datas[0].close[0] > prev_final_ub:
                self.lines.direction[0] = 1
            elif self.datas[0].close[0] < prev_final_lb:
                self.lines.direction[0] = -1
            else:
                self.lines.direction[0] = 0 # Still undefined
                self.lines.supertrend[0] = np.nan
                return

        # Determine current direction and SuperTrend line
        if self.lines.direction[-1] == 1: # Previous trend was up
            if self.datas[0].close[0] < self.final_lb[0]:
                self.lines.direction[0] = -1
            else:
                self.lines.direction[0] = 1
        elif self.lines.direction[-1] == -1: # Previous trend was down
            if self.datas[0].close[0] > self.final_ub[0]:
                self.lines.direction[0] = 1
            else:
                self.lines.direction[0] = -1

        # Set SuperTrend line value
        if self.lines.direction[0] == 1:
            self.lines.supertrend[0] = self.final_lb[0]
        elif self.lines.direction[0] == -1:
            self.lines.supertrend[0] = self.final_ub[0]
        else: # Direction is 0 (undetermined initial state)
            self.lines.supertrend[0] = np.nan


class BBSuperTrendVolumeBreakoutStrategy(bt.Strategy):
    """
    A breakout strategy using Bollinger Bands, SuperTrend, and Volume.

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
    params = (
        ('bb_period', 20),
        ('bb_devfactor', 2.0),
        ('st_period', 10),
        ('st_multiplier', 3.0),
        ('vol_ma_period', 20),
        ('vol_strength_mult', 1.5), # Multiplier for volume spike confirmation
        ('atr_period', 14),         # ATR period for TP/SL
        ('tp_atr_mult', 2.0),       # ATR multiplier for Take Profit
        ('sl_atr_mult', 1.0),       # ATR multiplier for Stop Loss
        ('printlog', False),        # Enable/disable logging
    )

    def __init__(self):
        self.boll = bt.indicators.BollingerBands(
            period=self.p.bb_period,
            devfactor=self.p.bb_devfactor
        )
        self.supertrend = SuperTrend(
            self.datas[0], # Pass the data feed
            period=self.p.st_period,
            multiplier=self.p.st_multiplier
        )
        self.atr = bt.indicators.ATR(period=self.p.atr_period)
        self.vol_ma = bt.indicators.SMA(self.data.volume, period=self.p.vol_ma_period)

        self.order = None
        self.entry_price = None
        self.trade_active = False
        self.entry_bar = None # To track bar of entry for TP/SL calculation
        self.active_tp_price = None
        self.active_sl_price = None
        self.trades = [] # Simple list to log trades
        # self.notifier = create_notifier() # Temporarily commented out

    def log(self, txt, dt=None, doprint=False):
        """Logging function for this strategy"""
        if self.params.printlog or doprint:
            dt = dt or self.datas[0].datetime.date(0)
            print(f'{dt.isoformat()} {txt}')

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
                    self.active_tp_price = self.entry_price + self.p.tp_atr_mult * atr_val
                    self.active_sl_price = self.entry_price - self.p.sl_atr_mult * atr_val
                    self.log(f'BUY TP: {self.active_tp_price:.2f}, SL: {self.active_sl_price:.2f}, ATR: {atr_val:.2f}')
                else:
                    self.log('ATR was zero or invalid at entry for TP/SL calc for BUY.')
                    self.active_tp_price = None # Disable TP/SL if ATR is not valid
                    self.active_sl_price = None

            elif order.issell():
                self.log(f'SELL EXECUTED, Price: {order.executed.price:.2f}, Cost: {order.executed.value:.2f}, Comm: {order.executed.comm:.2f}')
                if self.trade_active: # This is a closing sell
                     self.trade_active = False # Reset flag after closing trade
                else: # This is an opening short sell
                    self.entry_price = order.executed.price
                    atr_val = self.atr[-(self.datas[0].datetime.idx - self.entry_bar)]
                    if atr_val > 0:
                        self.active_tp_price = self.entry_price - self.p.tp_atr_mult * atr_val # TP is lower for shorts
                        self.active_sl_price = self.entry_price + self.p.sl_atr_mult * atr_val # SL is higher for shorts
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
        self.trades.append({
            'ref': trade.ref, 'symbol': trade.data._name,
            'entry_dt': bt.num2date(trade.dtopen).isoformat() if trade.dtopen else None,
            'entry_price': trade.price, 'direction': 'long' if trade.history[0].event.size > 0 else 'short',
            'exit_dt': bt.num2date(trade.dtclose).isoformat() if trade.dtclose else None,
            'exit_price': trade.history[-1].event.price if trade.history and trade.history[-1].event else None, # last event price
            'pnl': trade.pnl, 'pnl_comm': trade.pnlcomm,
            'size': trade.size, 'value': trade.value,
            'commission': trade.commission
        })
        self.trade_active = False # Ensure flag is reset
        self.entry_price = None
        self.active_tp_price = None
        self.active_sl_price = None


    def next(self):
        if self.order: # If an order is pending, do not send another
            return

        close = self.data.close[0]
        volume = self.data.volume[0]
        
        # Ensure all indicators have enough data
        # SuperTrend init might take `st_period` + internal ATR period.
        # For safety, check if supertrend direction is non-zero (meaning it has been determined)
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
            if close > bb_top and st_direction == 1 and volume > (vol_ma_val * self.p.vol_strength_mult):
                self.log(f'LONG ENTRY SIGNAL: Close {close:.2f} > BB Top {bb_top:.2f}, ST Green, Vol {volume:.0f} > MA*Mult {vol_ma_val * self.p.vol_strength_mult:.0f}')
                self.entry_bar = self.datas[0].datetime.idx # Bar index of signal
                self.order = self.buy()
                self.trade_active = True # Mark that we are attempting to enter a trade
                # TP/SL will be set in notify_order upon execution based on ATR at self.entry_bar
            
            # Short Entry Condition
            elif close < bb_bot and st_direction == -1 and volume > (vol_ma_val * self.p.vol_strength_mult):
                self.log(f'SHORT ENTRY SIGNAL: Close {close:.2f} < BB Bot {bb_bot:.2f}, ST Red, Vol {volume:.0f} > MA*Mult {vol_ma_val * self.p.vol_strength_mult:.0f}')
                self.entry_bar = self.datas[0].datetime.idx # Bar index of signal
                self.order = self.sell()
                self.trade_active = True # Mark that we are attempting to enter a trade
                # TP/SL will be set in notify_order

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

            elif self.position.size < 0: # In a short position
                # 1. Price closes back inside Bollinger Bands (above lower band)
                if close > bb_bot:
                    exit_signal = True
                    exit_reason = "Short Exit: Close back inside BB Bot"
                # 2. SuperTrend flips against position (turns green)
                elif st_direction == 1:
                    exit_signal = True
                    exit_reason = "Short Exit: SuperTrend flipped to Green"
                # 3. Fixed TP/SL
                elif self.active_tp_price and close <= self.active_tp_price: # TP is lower for shorts
                    exit_signal = True
                    exit_reason = f"Short Exit: Take Profit hit at {self.active_tp_price:.2f}"
                elif self.active_sl_price and close >= self.active_sl_price: # SL is higher for shorts
                    exit_signal = True
                    exit_reason = f"Short Exit: Stop Loss hit at {self.active_sl_price:.2f}"
            
            if exit_signal:
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
