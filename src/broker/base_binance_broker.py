from binance.client import Client
from binance.exceptions import BinanceAPIException
from binance.enums import *
from src.notification.logger import _logger
from src.notification.emailer import send_email_alert
from src.notification.telegram_notifier import send_telegram_alert
from src.broker.base_broker import BaseBroker
import pandas as pd
from typing import Any, Optional

class BaseBinanceBroker(BaseBroker):
    """
    Base class for Binance brokers (live and paper). Implements Binance-specific logic.
    """
    def __init__(self, api_key: str, api_secret: str, cash: float = 1000.0, testnet: bool = False) -> None:
        super().__init__(cash)
        self.client = Client(api_key, api_secret)
        self.client.API_URL = None
        self.broker_name = "Binance" if not testnet else "Binance Testnet"
        _logger.info(f"{self.broker_name} initialized with testnet.")

    def buy(self, symbol: str, qty: float, price: Optional[float] = None) -> Any:
        """Place a buy order on Binance."""
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

    def sell(self, symbol: str, qty: float, price: Optional[float] = None) -> Any:
        """Place a sell order on Binance."""
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

    def get_open_orders(self, symbol=None):
        """
        Get open orders for a symbol or all symbols.
        """
        try:
            return self.client.get_open_orders(symbol=symbol) if symbol else self.client.get_open_orders()
        except BinanceAPIException as e:
            return {'error': str(e)}

    def get_order_status(self, order_id, symbol=None):
        """
        Get order status by order ID and symbol.
        """
        try:
            return self.client.get_order(symbol=symbol, orderId=order_id)
        except BinanceAPIException as e:
            return {'error': str(e)}

    def fetch_ohlcv(self, symbol, interval, limit=100):
        """
        Fetch OHLCV data as a pandas DataFrame.
        """
        try:
            klines = self.client.get_klines(symbol=symbol, interval=interval, limit=limit)
            df = pd.DataFrame(klines, columns=[
                'open_time', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'number_of_trades',
                'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'])
            df['open_time'] = pd.to_datetime(df['open_time'], unit='ms')
            df.set_index('open_time', inplace=True)
            df = df[['open', 'high', 'low', 'close', 'volume']].astype(float)
            return df
        except BinanceAPIException as e:
            return {'error': str(e)} 

    def place_order(self, symbol, side, quantity, order_type='MARKET', price=None, **kwargs):
        """
        Place an order on Binance. Supports MARKET and LIMIT orders.
        Returns the order response dict.
        """
        try:
            if order_type.upper() == 'MARKET':
                return self.client.create_order(
                    symbol=symbol,
                    side=side.upper(),
                    type='MARKET',
                    quantity=quantity
                )
            elif order_type.upper() == 'LIMIT':
                return self.client.create_order(
                    symbol=symbol,
                    side=side.upper(),
                    type='LIMIT',
                    timeInForce='GTC',
                    quantity=quantity,
                    price=str(price)
                )
            else:
                raise ValueError(f"Unsupported order type: {order_type}")
        except BinanceAPIException as e:
            return {'error': str(e)}

    def cancel_order(self, order_id, symbol=None):
        """
        Cancel an order on Binance.
        """
        try:
            return self.client.cancel_order(symbol=symbol, orderId=order_id)
        except BinanceAPIException as e:
            return {'error': str(e)}

    def get_balance(self, asset=None):
        """
        Get account balance for a specific asset or all assets.
        """
        try:
            balances = self.client.get_account()['balances']
            if asset:
                for b in balances:
                    if b['asset'] == asset:
                        return b
                return None
            return balances
        except BinanceAPIException as e:
            return {'error': str(e)}

        