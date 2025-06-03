# Crypto Trading Platform User Guide

This guide will help you get started with backtesting, optimizing, and running live trading using this platform.

---

## 1. Environment Setup

### a. Clone the Repository
```bash
# Clone the repo (replace with your repo URL)
git clone <your-repo-url>
cd crypto-trading
```

### b. Create and Activate a Virtual Environment
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### c. Install Dependencies
```bash
pip install -r requirements.txt
```

If you plan to use live trading with specific brokers, also install:
```bash
pip install cbpro ib_insync python-binance
```

---

## 2. Running Backtests

Backtests are run using strategy scripts in `src/strategy/`.

### Example: Run a Backtest
```bash
python src/strategy/bb_volume_supertrend_strategy.py
```

- You can modify the script or parameters as needed.
- Results and logs will be saved in the `logs/` and `results/` folders.

---

## 3. Running Optimizations

Optimizers are in `src/optimizer/`. They search for the best parameters for a given strategy.

### Example: Run an Optimizer
```bash
python src/optimizer/bb_volume_supertrend_optimizer.py
```

- You can edit the optimizer script to change the search space or data files.
- Results will be saved in the `results/` folder.

---

## 4. Live Trading

Live trading is managed by trading bots in `src/trading/`.

### a. Configure Your API Keys
- Place your API keys in a secure config file (e.g., `config/donotshare/`).
- Never commit your keys to version control.

### b. Choose and Configure a Broker
- **Binance:** Uses `BinanceBroker` (requires `python-binance`)
- **Coinbase:** Uses `CoinbaseBroker` (requires `cbpro`)
- **IBKR:** Uses `IBKRBroker` (requires `ib_insync`)

### c. Example: Start a Live Trading Bot
```python
from src.trading.base_trading_bot import BaseTradingBot
from src.trading.binance_broker import BinanceBroker
from src.strategy.bb_volume_supertrend_strategy import BBSuperTrendVolumeBreakoutStrategy

# Load your API keys securely
api_key = 'your_binance_api_key'
api_secret = 'your_binance_api_secret'
broker = BinanceBroker(api_key, api_secret)

config = {
    'trading_pair': 'BTCUSDT',
    'initial_balance': 1000,
    'max_drawdown_pct': 20.0,
    'max_exposure': 1.0,
    'position_sizing_pct': 0.1
}

strategy = BBSuperTrendVolumeBreakoutStrategy()
bot = BaseTradingBot(config, strategy, broker=broker, paper_trading=False)
bot.run()
```
- Replace with the broker and strategy of your choice.
- Set `paper_trading=True` for dry runs.

### d. Monitoring and Logs
- All trades and orders are logged in `logs/json/`.
- State is persisted for recovery after restarts.
- Notifications are sent via Telegram/email if configured.

---

## 5. Troubleshooting
- **Missing package errors:** Install the required package with `pip install ...`.
- **API errors:** Check your API keys and network connection.
- **Strategy errors:** Review logs in `logs/` for details.

---

## 6. Extending the Platform
- Add new strategies using the template in `src/strategy/strategy_template.py`.
- Add new optimizers using the template in `src/optimizer/optimizer_template.py`.
- Add new broker adapters by subclassing `AbstractBroker` in `src/trading/`.

---

For more details, see the code comments and docstrings throughout the project. 