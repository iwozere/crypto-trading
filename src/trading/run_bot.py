import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import json
from src.trading import create_trading_bot
from src.strats.strategy_registry import STRATEGY_REGISTRY
from src.notification.logger import _logger

# Example: You must implement or import your real strategy class here
# from src.strats.rsi_bb_volume_strategy import RSIBollVolumeATRStrategy


def main(config_name : str):
    _logger.info("Starting trading bot runner.")
    if len(sys.argv) != 2 and not config_name:
        _logger.error("Usage: python run_bot.py <config.json>")
        sys.exit(1)
    if not config_name:
        config_name = sys.argv[1]
    config_path = f'config/trading/{config_name}'
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        _logger.info(f"Loaded config from {config_path}")
    except Exception as e:
        _logger.error(f"Failed to load config: {e}")
        sys.exit(1)

    # Example: You must map config['strategy_type'] to your actual strategy class
    strategy_type = config.get('strategy_type')
    if not strategy_type:
        _logger.error("strategy_type is required in config.")
        sys.exit(1)

    parameters = config.get('strategy_params', {})
    strat_info = STRATEGY_REGISTRY.get(strategy_type)
    if not strat_info:
        _logger.error(f"Unsupported strategy_type: {strategy_type}")
        _logger.error(f"Available strategies: {list(STRATEGY_REGISTRY.keys())}")
        sys.exit(1)
        
    strategy_class = strat_info['class']
    _logger.info(f"Selected strategy: {strategy_type} ({strategy_class.__name__})")
    strategy = strategy_class(parameters)

    _logger.info("Creating trading bot...")
    bot = create_trading_bot(config, strategy)
    _logger.info("Bot created. Running bot...")
    try:
        bot.run()
    except Exception as e:
        _logger.error(f"Error while running bot: {e}")
        sys.exit(1)
    _logger.info("Bot stopped.")

if __name__ == "__main__":
    main('rsi_bb_volume1.json') 