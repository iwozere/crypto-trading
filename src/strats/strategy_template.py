"""
Strategy Template
----------------

This template provides a consistent structure for new trading strategies using Backtrader.
Copy this file and fill in the specific logic for your strategy.
"""

import backtrader as bt
from src.strats.base_strategy import BaseStrategy

class StrategyTemplate(BaseStrategy):
    """
    Brief description of the strategy.

    Indicators:
    - List your indicators here.

    Entry Logic:
    - Describe entry conditions.

    Exit Logic:
    - Describe exit conditions.
    """
    params = (
        # Example parameters (customize as needed)
        ('example_period', 14),
        ('example_threshold', 1.5),
        ('printlog', False),
    )

    def __init__(self):
        super().__init__()
        # Initialize indicators here
        # self.sma = bt.indicators.SimpleMovingAverage(self.data.close, period=self.p.example_period)
        # self.rsi = bt.indicators.RSI(self.data.close, period=14)
        self.order = None
        self.entry_price = None
        self.trade_active = False
        self.trades = []  # List to log trades

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f'BUY EXECUTED, Price: {order.executed.price:.2f}')
                self.entry_price = order.executed.price
            elif order.issell():
                self.log(f'SELL EXECUTED, Price: {order.executed.price:.2f}')
                self.entry_price = order.executed.price
            self.bar_executed = len(self)
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log(f'Order {order.getstatusname()}')
        self.order = None

    def notify_trade(self, trade):
        if not trade.isclosed:
            return
        self.log(f'OPERATION PROFIT, GROSS {trade.pnl:.2f}, NET {trade.pnlcomm:.2f}')
        trade_dict = {
            'symbol': trade.data._name if hasattr(trade.data, '_name') else 'UNKNOWN',
            'ref': trade.ref,
            'entry_time': bt.num2date(trade.dtopen) if trade.dtopen else None,
            'entry_price': trade.price,
            'direction': 'long',  # or 'short', customize as needed
            'exit_time': bt.num2date(trade.dtclose) if trade.dtclose else None,
            'exit_price': trade.history[-1].event.price if trade.history and trade.history[-1].event else None,
            'pnl': trade.pnl, 'pnl_comm': trade.pnlcomm,
            'size': trade.size, 'value': trade.value,
            'commission': trade.commission
        }
        self.record_trade(trade_dict)
        self.trade_active = False
        self.entry_price = None

    def next(self):
        # Example entry/exit logic (replace with your own)
        if self.order:
            return
        close = self.data.close[0]
        # Example: Enter long if close > some threshold
        if not self.position:
            if close > 100:  # Replace with your entry condition
                self.order = self.buy()
                self.trade_active = True
        else:
            # Example: Exit if close < some threshold
            if close < 95:  # Replace with your exit condition
                self.order = self.close() 