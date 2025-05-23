from binance.client import Client
from binance.enums import *
import backtrader as bt


class BinancePaperBroker(bt.brokers.BackBroker):
    def __init__(self, api_key, api_secret):
        super().__init__()
        self.client = Client(api_key, api_secret)
        self.client.API_URL = 'https://testnet.binance.vision/api'  # Testnet URL

    def buy(self, symbol, qty, price=None):
        order = self.client.create_order(
            symbol=symbol,
            side=SIDE_BUY,
            type=ORDER_TYPE_MARKET if price is None else ORDER_TYPE_LIMIT,
            quantity=qty,
            price=price
        )
        return order

    def sell(self, symbol, qty, price=None):
        order = self.client.create_order(
            symbol=symbol,
            side=SIDE_SELL,
            type=ORDER_TYPE_MARKET if price is None else ORDER_TYPE_LIMIT,
            quantity=qty,
            price=price
        )
        return order
