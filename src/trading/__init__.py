from src.broker.broker_factory import get_broker
from src.trading.bot_factory import get_bot
from typing import Any, Dict

def create_trading_bot(config: Dict[str, Any], strategy_class: Any, parameters: Dict[str, Any]) -> Any:
    """
    Centralized function to create a trading bot using config, strategy class, and parameters.
    Uses broker and bot factories.
    """
    broker = get_broker(config)
    bot = get_bot(config, strategy_class, parameters, broker)
    return bot 