"""
Base Strategy Module
-------------------

This module defines the BaseStrategy class, which provides a foundation for implementing trading strategies in Backtrader. It includes trade logging, notification integration, and utility methods for recording and notifying about trades and errors.

Main Features:
- Trade logging and recording
- Integration with notification systems (Telegram)
- Utility hooks for trade entry, exit, and error handling
- Designed for extension by concrete strategy classes

Classes:
- BaseStrategy: Abstract base class for trading strategies
"""
import backtrader as bt
from src.notification.telegram_notifier import create_notifier

class BaseStrategy(bt.Strategy):
    params = (
        ('printlog', False),
        ('notify', True),
    )

    def __init__(self):
        self.trades = []
        self.notifier = create_notifier()

    def log(self, txt, dt=None, doprint=False):
        if self.p.printlog or doprint:
            dt = dt or self.datas[0].datetime.date(0)
            print(f'{dt.isoformat()} {txt}')

    def record_trade(self, trade_dict):
        self.trades.append(trade_dict)
        self.on_trade_exit(trade_dict)

    def on_trade_entry(self, trade_dict):
        if self.p.notify and self.notifier:
            self.notifier.send_trade_notification(trade_dict)

    def on_trade_exit(self, trade_dict):
        if self.p.notify and self.notifier:
            self.notifier.send_trade_update(trade_dict)

    def on_error(self, error):
        if self.p.notify and self.notifier:
            self.notifier.send_error_notification(str(error))
            
