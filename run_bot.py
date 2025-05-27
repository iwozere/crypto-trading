import sys
import json
from src.trading import create_trading_bot

# Import your strategies here
from src.strats.rsi_bb_volume_strategy import RSIBollVolumeATRStrategy
# Add more strategy imports as needed

# Central registry for strategies
strategy_registry = {
    'rsi_bb_volume': RSIBollVolumeATRStrategy,
    # Add more mappings: 'strategy_type': StrategyClass
}

def main():
    if len(sys.argv) != 2:
        print("Usage: python run_bot.py path/to/config.json")
        sys.exit(1)
    config_path = sys.argv[1]
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
    except Exception as e:
        print(f"Failed to load config: {e}")
        sys.exit(1)

    strategy_type = config.get('strategy_type', 'rsi_bb_volume')
    StrategyClass = strategy_registry.get(strategy_type)
    if not StrategyClass:
        print(f"Unsupported strategy_type: {strategy_type}")
        print(f"Supported types: {list(strategy_registry.keys())}")
        sys.exit(1)

    # Pass the entire config as params
    strategy = StrategyClass(config)

    bot = create_trading_bot(config, strategy)
    bot.run()

if __name__ == "__main__":
    main() 