from src.broker.broker_factory import get_broker
from src.trading.bot_factory import get_bot
from typing import Any, Dict

def create_trading_bot(config: Dict[str, Any], strategy: Any) -> Any:
    """
    Centralized function to create a trading bot using config and strategy.
    Uses broker and bot factories.
    """
    broker = get_broker(config)
    bot = get_bot(config, strategy, broker)
    return bot 