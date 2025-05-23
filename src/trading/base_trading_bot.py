"""
Base Trading Bot Module
----------------------

This module defines the BaseTradingBot class, which provides a framework for implementing trading bots with signal processing, trade execution, position management, and notification capabilities. It is designed to be subclassed by specific strategy bots and supports integration with notification systems (Telegram, email).

Main Features:
- Signal processing and trade execution logic
- Position and balance management
- Trade history tracking
- Notification via Telegram and email
- Designed for extension by concrete strategy bots

Classes:
- BaseTradingBot: Abstract base class for trading bots
"""
import time
from datetime import datetime
from src.notification.logger import _logger
from src.notification.telegram_notifier import create_notifier as create_telegram_notifier
from src.notification.emailer import EmailNotifier
from config.donotshare.donotshare import SENDGRID_API_KEY as sgkey
import asyncio

class BaseTradingBot:
    def __init__(self, config, strategy):
        self.config = config
        self.trading_pair = config.get('trading_pair', 'BTCUSDT')
        self.initial_balance = config.get('initial_balance', 1000.0)
        self.is_running = False
        self.active_positions = {}
        self.trade_history = []
        self.strategy = strategy
        self.current_balance = self.initial_balance
        self.total_pnl = 0.0
        # Notification setup
        self.telegram_notifier = create_telegram_notifier()
        try:
            self.email_notifier = EmailNotifier(sgkey)
        except Exception as e:
            self.email_notifier = None
            self.log_message(f"Email notifier not initialized: {e}", level="error")

    def run(self):
        self.is_running = True
        self.log_message(f"Starting bot for {self.trading_pair}")
        while self.is_running:
            try:
                signals = self.get_signals()
                self.process_signals(signals)
                self.update_positions()
                time.sleep(1)
            except Exception as e:
                self.log_message(f"Error in bot loop: {str(e)}", level="error")
                time.sleep(5)

    def get_signals(self):
        return self.strategy.get_signals(self.trading_pair)

    def process_signals(self, signals):
        for signal in signals:
            if signal['type'] == 'buy' and self.trading_pair not in self.active_positions:
                self.execute_trade('buy', signal['price'], signal['size'])
            elif signal['type'] == 'sell' and self.trading_pair in self.active_positions:
                self.execute_trade('sell', signal['price'], signal['size'])

    def execute_trade(self, trade_type, price, size):
        timestamp = datetime.now()
        if trade_type == 'buy':
            self.active_positions[self.trading_pair] = {
                'entry_price': price,
                'size': size,
                'entry_time': timestamp
            }
            self.notify_trade_event('BUY', price, size, timestamp)
        else:  # sell
            if self.trading_pair in self.active_positions:
                position = self.active_positions[self.trading_pair]
                pnl = ((price - position['entry_price']) / position['entry_price']) * 100
                self.trade_history.append({
                    'bot_id': id(self),
                    'pair': self.trading_pair,
                    'type': 'long',
                    'entry_price': position['entry_price'],
                    'exit_price': price,
                    'size': position['size'],
                    'pl': pnl,
                    'time': timestamp.isoformat()
                })
                self.current_balance *= (1 + pnl/100)
                self.total_pnl += pnl
                del self.active_positions[self.trading_pair]
                self.notify_trade_event('SELL', price, size, timestamp, entry_price=position['entry_price'], pnl=pnl)

    def notify_trade_event(self, side, price, size, timestamp, entry_price=None, pnl=None):
        # Telegram notification
        if self.telegram_notifier:
            trade_data = {
                'symbol': self.trading_pair,
                'side': side,
                'entry_price': entry_price if entry_price is not None else price,
                'exit_price': price if side == 'SELL' else None,
                'tp_price': getattr(self.strategy, 'tp_atr_mult', None),
                'sl_price': getattr(self.strategy, 'sl_atr_mult', None),
                'quantity': size,
                'timestamp': timestamp.isoformat(),
                'pnl': pnl
            }
            try:
                if side == 'BUY':
                    asyncio.run(self.telegram_notifier.send_trade_notification(trade_data))
                else:
                    asyncio.run(self.telegram_notifier.send_trade_update(trade_data))
            except Exception as e:
                self.log_message(f"Failed to send Telegram notification: {e}", level="error")
        # Email notification
        if self.email_notifier:
            try:
                subject = f"Trade notification: {side} {self.trading_pair} at {price}"
                body = f"{side} {self.trading_pair}\nPrice: {price}\nSize: {size}\nTime: {timestamp}"
                if pnl is not None:
                    body += f"\nPnL: {pnl:.2f}%"
                self.email_notifier.send_notification_email(side, self.trading_pair, price, size, body=body)
            except Exception as e:
                self.log_message(f"Failed to send email notification: {e}", level="error")

    def update_positions(self):
        for pair, position in list(self.active_positions.items()):
            current_price = self.strategy.get_current_price(pair)
            entry_price = position['entry_price']
            pnl = ((current_price - entry_price) / entry_price) * 100
            # Check stop loss
            if pnl <= -self.strategy.sl_atr_mult * 100:
                self.execute_trade('sell', current_price, position['size'])
            # Check take profit
            elif pnl >= self.strategy.tp_atr_mult * 100:
                self.execute_trade('sell', current_price, position['size'])

    def stop(self):
        self.is_running = False
        self.log_message(f"Stopping bot for {self.trading_pair}")
        for pair in list(self.active_positions.keys()):
            current_price = self.strategy.get_current_price(pair)
            self.execute_trade('sell', current_price, self.active_positions[pair]['size'])

    def log_message(self, message, level="info"):
        if level == "error":
            _logger.error(message)
        else:
            _logger.info(message) 