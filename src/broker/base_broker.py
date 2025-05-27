import backtrader as bt
from src.notification.logger import _logger
from typing import Any

class BaseBroker(bt.BrokerBase):
    """
    Abstract base class for all brokers. Defines the required interface and common attributes.
    """
    def __init__(self, cash: float = 1000.0) -> None:
        super().__init__()
        self.broker_name: str = "Base Broker"
        self._cash: float = cash
        self._value: float = cash
        self.orders: list = []
        self.positions: dict = {}
        self.notifs: list = []
        

    def start(self) -> None:
        """Start the broker."""
        _logger.info("Broker started.")

    def getcash(self) -> float:
        """Return current cash balance."""
        return self._cash

    def getvalue(self) -> float:
        """Return current portfolio value."""
        return self._value

    def getposition(self, data: Any) -> Any:
        """Return position for the given data/symbol."""
        symbol = data._name
        return self.positions.get(symbol, 0)

    def buy(self, symbol: str, qty: float, price: float = None) -> Any:
        """Place a buy order. Must be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement buy()")

    def sell(self, symbol: str, qty: float, price: float = None) -> Any:
        """Place a sell order. Must be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement sell()")

    def _notify_order(self, order: Any) -> None:
        """Notify about an order (stub for notification logic)."""
        self.notifs.append(order)

    def get_notifications(self):
        """Yield notifications one by one."""
        while self.notifs:
            yield self.notifs.pop(0)

class MockBroker(BaseBroker):
    """
    Mock broker for testing. Simulates order execution without real API calls.
    """
    def __init__(self, cash: float = 1000.0) -> None:
        super().__init__(cash)
        self.broker_name = "Mock Broker"

    def buy(self, symbol: str, qty: float, price: float = None) -> dict:
        """Simulate a buy order."""
        order = {'type': 'buy', 'symbol': symbol, 'qty': qty, 'price': price, 'status': 'filled'}
        self.orders.append(order)
        self._cash -= (price or 1.0) * qty
        self.positions[symbol] = self.positions.get(symbol, 0) + qty
        self._notify_order(order)
        return order

    def sell(self, symbol: str, qty: float, price: float = None) -> dict:
        """Simulate a sell order."""
        order = {'type': 'sell', 'symbol': symbol, 'qty': qty, 'price': price, 'status': 'filled'}
        self.orders.append(order)
        self._cash += (price or 1.0) * qty
        self.positions[symbol] = self.positions.get(symbol, 0) - qty
        self._notify_order(order)
        return order
