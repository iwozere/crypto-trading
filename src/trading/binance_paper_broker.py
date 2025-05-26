import datetime
from typing import Any, Dict, Optional
from binance.client import Client
from binance.enums import *
import backtrader as bt
from src.notification.logger import _logger
from src.notification.emailer import send_email_alert
from src.notification.telegram_notifier import send_telegram_alert
import threading
from src.data.binance_live_feed import BinanceLiveData
from src.strats.bb_volume_supertrend_strategy import BBSuperTrendVolumeBreakoutStrategy
from config.donotshare import BINANCE_PAPER_API_KEY, BINANCE_PAPER_API_SECRET


class BinancePaperBroker(bt.BrokerBase):
    def __init__(self, api_key, api_secret, cash=10000.0):
        super().__init__()
        self.client = Client(api_key, api_secret)
        self.client.API_URL = 'https://testnet.binance.vision/api'  # Testnet URL
        self._cash = cash
        self._value = cash
        self.orders = []
        self.positions = {}
        self.notifs = []
        _logger.info("BinancePaperBroker initialized with testnet.")

    def start(self):
        _logger.info("Broker started.")

    def getcash(self):
        return self._cash

    def getvalue(self):
        return self._value

    def getposition(self, data):
        symbol = data._name
        return self.positions.get(symbol, 0)

    def buy(self, symbol, qty, price=None):
        try:
            order = self.client.create_order(
                symbol=symbol,
                side=SIDE_BUY,
                type=ORDER_TYPE_MARKET if price is None else ORDER_TYPE_LIMIT,
                quantity=qty,
                price=price
            )
            self.orders.append(order)
            self._notify_order(order)
            _logger.info(f"Buy order placed: {order}")
            send_telegram_alert(f"Buy order placed: {order}")
            return order
        except Exception as e:
            _logger.error(f"Buy order failed: {e}")
            send_email_alert("Buy order failed", str(e))
            return None

    def sell(self, symbol, qty, price=None):
        try:
            order = self.client.create_order(
                symbol=symbol,
                side=SIDE_SELL,
                type=ORDER_TYPE_MARKET if price is None else ORDER_TYPE_LIMIT,
                quantity=qty,
                price=price
            )
            self.orders.append(order)
            self._notify_order(order)
            _logger.info(f"Sell order placed: {order}")
            send_telegram_alert(f"Sell order placed: {order}")
            return order
        except Exception as e:
            _logger.error(f"Sell order failed: {e}")
            send_email_alert("Sell order failed", str(e))
            return None

    def _notify_order(self, order):
        # This is a stub. You should map Binance order status to Backtrader order notifications.
        self.notifs.append(order)

    def get_notifications(self):
        while self.notifs:
            yield self.notifs.pop(0)

    # Optionally, implement other methods as needed for your strategies


cerebro = bt.Cerebro()
data = BinanceLiveData(symbol='BTCUSDT', timeframe='1m')
cerebro.adddata(data)
cerebro.addstrategy(BBSuperTrendVolumeBreakoutStrategy)
cerebro.setbroker(BinancePaperBroker(BINANCE_PAPER_API_KEY, BINANCE_PAPER_API_SECRET, cash=1000.0))
cerebro.run()
