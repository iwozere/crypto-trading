from src.trading.rsi_bb_volume_bot import RsiBbVolumeBot
from typing import Any, Dict

def get_bot(config: Dict[str, Any], strategy_class: Any, parameters: Dict[str, Any], broker: Any) -> Any:
    """
    Factory function to instantiate the correct bot based on config['bot_type'].
    Currently supports: 'rsi_bb_volume'.
    """
    bot_type = config.get('bot_type', 'rsi_bb_volume').lower()
    if bot_type == 'rsi_bb_volume':
        # Pass class and parameters, do not instantiate here
        return RsiBbVolumeBot(config, strategy_class, parameters, broker)
    else:
        raise ValueError(f"Unsupported bot type: {bot_type}") 