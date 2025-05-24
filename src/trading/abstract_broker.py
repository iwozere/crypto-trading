from abc import ABC, abstractmethod

class AbstractBroker(ABC):
    @abstractmethod
    def place_order(self, symbol, side, quantity, order_type='market', price=None, **kwargs):
        pass

    @abstractmethod
    def cancel_order(self, order_id, symbol=None):
        pass

    @abstractmethod
    def get_balance(self, asset=None):
        pass

    @abstractmethod
    def get_open_orders(self, symbol=None):
        pass

    @abstractmethod
    def get_order_status(self, order_id, symbol=None):
        pass

    @abstractmethod
    def fetch_ohlcv(self, symbol, interval, limit=100):
        pass 