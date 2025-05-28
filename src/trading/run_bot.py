import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import json
from src.trading import create_trading_bot

# Example: You must implement or import your real strategy class here
# from src.strats.rsi_bb_volume_strategy import RSIBollVolumeATRStrategy


def main(config_name : str):
    if len(sys.argv) != 2 and not config_name:
        print("Usage: python run_bot.py rsi_bb_volume1.json")
        sys.exit(1)
    if not config_name:
        config_name = sys.argv[1]
    config_path = f'config/trading/{config_name}'
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
    except Exception as e:
        print(f"Failed to load config: {e}")
        sys.exit(1)

    # Example: You must map config['strategy_type'] to your actual strategy class
    strategy_type = config.get('strategy_type', 'rsi_bb_volume')
    if strategy_type == 'rsi_bb_volume':
        parameters = config.get('strategy_params', {})
        from src.strats.rsi_bb_volume_strategy import RSIBollVolumeATRStrategy
        strategy = RSIBollVolumeATRStrategy(
            rsi_period=config.get('rsi_period', 14),
            boll_period=config.get('boll_period', 20),
            boll_devfactor=config.get('boll_devfactor', 2.0),
            atr_period=config.get('atr_period', 14),
            vol_ma_period=config.get('vol_ma_period', 20),
            tp_atr_mult=config.get('tp_atr_mult', 2.0),
            sl_atr_mult=config.get('sl_atr_mult', 1.0),
            rsi_oversold=config.get('rsi_oversold', 30),
            rsi_overbought=config.get('rsi_overbought', 70)
        )
    else:
        print(f"Unsupported strategy_type: {strategy_type}")
        sys.exit(1)

    bot = create_trading_bot(config, strategy)
    bot.run()

if __name__ == "__main__":
    main('rsi_bb_volume1.json') 