import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.trading import create_trading_bot

# Example dummy strategy (replace with your real strategy)
class DummyStrategy:
    def get_signals(self, trading_pair):
        # Return a list of signal dicts, e.g. [{'type': 'buy', 'price': 100, 'size': 1}]
        return []

# Example config for a mock broker and RSI BB Volume bot
config = {
    "type": "mock",            # or 'binance', 'binance_paper', 'ibkr'
    "bot_type": "rsi_bb_volume",
    "trading_pair": "BTCUSDT",
    "initial_balance": 1000.0,
    "cash": 1000.0,
    # Add other broker-specific keys as needed (api_key, api_secret, etc.)
}

strategy = DummyStrategy()

# Create the bot using the centralized factory
bot = create_trading_bot(config, strategy)

# Run the bot (this will loop forever in most real bots)
bot.run()