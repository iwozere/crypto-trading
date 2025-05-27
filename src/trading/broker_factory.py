from src.trading.binance_broker import BinanceBroker
from src.trading.binance_paper_broker import BinancePaperBroker
from src.trading.ibkr_broker import IBKRBroker
from src.trading.base_broker import MockBroker
from typing import Any, Dict

def get_broker(config: Dict[str, Any]):
    """
    Factory function to instantiate the correct broker based on config['type'].
    Supported types: 'binance', 'binance_paper', 'ibkr', 'mock'.
    """
    broker_type = config.get('type', 'mock').lower()
    if broker_type == 'binance':
        return BinanceBroker(config['api_key'], config['api_secret'], config.get('cash', 1000.0))
    elif broker_type == 'binance_paper':
        return BinancePaperBroker(config['api_key'], config['api_secret'], config.get('cash', 1000.0))
    elif broker_type == 'ibkr':
        return IBKRBroker(config.get('host', '127.0.0.1'), config.get('port', 7497), config.get('client_id', 1), config.get('cash', 1000.0))
    elif broker_type == 'mock':
        return MockBroker(config.get('cash', 1000.0))
    else:
        raise ValueError(f"Unsupported broker type: {broker_type}") 