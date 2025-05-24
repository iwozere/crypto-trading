from src.trading.abstract_broker import AbstractBroker
import pandas as pd
import cbpro

class CoinbaseBroker(AbstractBroker):
    def __init__(self, api_key, api_secret, passphrase):
        """
        Initialize CoinbaseBroker with API credentials.
        """
        if cbpro is None:
            raise ImportError('cbpro package is required for CoinbaseBroker')
        self.client = cbpro.AuthenticatedClient(api_key, api_secret, passphrase)

    def place_order(self, symbol, side, quantity, order_type='market', price=None, **kwargs):
        """
        Place an order on Coinbase Pro. Supports market and limit orders.
        Returns the order response dict.
        """
        try:
            if order_type.lower() == 'market':
                return self.client.place_market_order(product_id=symbol, side=side.lower(), size=quantity)
            elif order_type.lower() == 'limit':
                return self.client.place_limit_order(product_id=symbol, side=side.lower(), price=str(price), size=quantity, post_only=True)
            else:
                raise ValueError(f"Unsupported order type: {order_type}")
        except Exception as e:
            return {'error': str(e)}

    def cancel_order(self, order_id, symbol=None):
        """
        Cancel an order on Coinbase Pro.
        """
        try:
            return self.client.cancel_order(order_id)
        except Exception as e:
            return {'error': str(e)}

    def get_balance(self, asset=None):
        """
        Get account balance for a specific asset or all assets.
        """
        try:
            accounts = self.client.get_accounts()
            if asset:
                for acc in accounts:
                    if acc['currency'] == asset:
                        return acc
                return None
            return accounts
        except Exception as e:
            return {'error': str(e)}

    def get_open_orders(self, symbol=None):
        """
        Get open orders for a symbol or all symbols.
        """
        try:
            return self.client.get_orders(product_id=symbol, status='open') if symbol else self.client.get_orders(status='open')
        except Exception as e:
            return {'error': str(e)}

    def get_order_status(self, order_id, symbol=None):
        """
        Get order status by order ID.
        """
        try:
            return self.client.get_order(order_id)
        except Exception as e:
            return {'error': str(e)}

    def fetch_ohlcv(self, symbol, interval, limit=100):
        """
        Fetch OHLCV data as a pandas DataFrame.
        """
        try:
            # Coinbase Pro granularity: 60, 300, 900, 3600, 21600, 86400 (seconds)
            granularity = int(interval.rstrip('sminhd'))
            data = self.client.get_product_historic_rates(symbol, granularity=granularity)
            df = pd.DataFrame(data, columns=['time', 'low', 'high', 'open', 'close', 'volume'])
            df['time'] = pd.to_datetime(df['time'], unit='s')
            df.set_index('time', inplace=True)
            return df[['open', 'high', 'low', 'close', 'volume']].astype(float)
        except Exception as e:
            return {'error': str(e)} 