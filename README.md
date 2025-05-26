# Crypto Trading Bot Platform

A modular, extensible platform for research, backtesting, and live trading of algorithmic strategies on crypto and stock markets. Features a web GUI, REST API, strategy optimizers, and robust logging/notification.

---

## Table of Contents
- [Setup](#setup)
- [Project Structure](#project-structure)
- [Strategy and Optimizer Conventions](#strategy-and-optimizer-conventions)
- [Strategies](#strategies)
- [Optimizers](#optimizers)
- [Development](#development)
- [Testing](#testing)
- [Quick Start Example](#quick-start-example)
- [Quick Start Example: Optimizer](#quick-start-example-optimizer)
- [Usage](#usage)
- [Deployment](#deployment)
- [Troubleshooting](#troubleshooting)

---

# Python Project

This is a Python project template with virtual environment setup.

## Setup

1. Create a virtual environment:
```bash
python -m venv venv
```

2. Activate the virtual environment:
- Windows:
```bash
.\venv\Scripts\activate
```
- Unix/MacOS:
```bash
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Project Structure

```
crypto-trading/
├── README.md
├── requirements.txt
├── setup.py
├── data/
│   └── all/
├── results/
│   └── archive/
├── src/
│   ├── analyzer/
│   ├── bot/
│   ├── data/
│   ├── notification/
│   ├── optimizer/
│   │   ├── base_optimizer.py
│   │   ├── rsi_bb_atr_optimizer.py
│   │   ├── rsi_bb_volume_optimizer.py
│   │   ├── bb_volume_supertrend_optimizer.py
│   │   └── rsi_volume_supertrend_optimizer.py
│   ├── strats/
│   │   ├── rsi_bb_atr_strategy.py
│   │   ├── rsi_bb_volume_strategy.py
│   │   ├── bb_volume_supertrend_strategy.py
│   │   ├── rsi_volume_supertrend_strategy.py
│   │   ├── ichimoku_rsi_atr_volume_strategy.py
│   │   └── base_strategy.py
│   ├── webgui/
│   │   ├── static/
│   │   └── templates/
│   └── ...
├── tests/
└── ...
```

## Strategy and Optimizer Conventions

### Strategy Architecture

- **All strategies inherit from `BaseStrategy`**, which itself inherits from `bt.Strategy`.
- **Parameters** are defined in the `params` tuple and accessed via `self.p`.
- **Trade logging** is standardized: use `self.trades` (a list of trade dicts) and `self.record_trade(trade_dict)` to log trades.
- **Notification hooks** are available: `on_trade_entry`, `on_trade_exit`, and `on_error`.
- **Only Backtrader event-driven methods** are used (`__init__`, `next`, `notify_order`, `notify_trade`, etc.).
- **No custom config dicts or custom backtest loops** are used in strategies.

### Example Strategy Template

```python
import backtrader as bt
from src.strats.base_strategy import BaseStrategy

class MyCustomStrategy(BaseStrategy):
    """
    Backtrader-native strategy template.
    - Inherits from BaseStrategy (standardized trade logging, notification, and event-driven architecture)
    - Uses Backtrader's param system (self.p)
    - Uses self.trades and self.record_trade for trade logging
    - All logic in __init__, next, notify_order, notify_trade
    """
    params = (
        ('my_indicator_period', 14),
        ('printlog', False),
    )

    def __init__(self):
        super().__init__()
        self.my_indicator = bt.indicators.SMA(self.data.close, period=self.p.my_indicator_period)
        self.order = None
        self.entry_price = None
        self.current_trade = None

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return
        if order.status == order.Completed:
            if order.isbuy():
                self.entry_price = order.executed.price
            elif order.issell():
                pass
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            pass
        self.order = None

    def next(self):
        if self.order:
            return
        if not self.position:
            if self.my_indicator[0] > self.data.close[0]:
                self.entry_price = self.data.close[0]
                self.current_trade = {
                    'entry_time': self.data.datetime.datetime(0),
                    'entry_price': self.entry_price,
                }
                size = (self.broker.getvalue() * 0.1) / self.entry_price
                self.order = self.buy(size=size)
        else:
            if self.data.close[0] > self.entry_price * 1.05:
                self.order = self.close()
                if self.current_trade:
                    self.current_trade.update({
                        'exit_time': self.data.datetime.datetime(0),
                        'exit_price': self.data.close[0],
                        'pnl': (self.data.close[0] - self.entry_price) / self.entry_price * 100,
                        'exit_type': 'target'
                    })
                    self.record_trade(self.current_trade)
                    self.current_trade = None
```

### How to Create a New Strategy

1. **Inherit from `BaseStrategy`** in your new strategy class.
2. **Define all parameters** in the `params` tuple.
3. **Initialize indicators** in `__init__` using `self.p` for parameter access.
4. **Implement your trading logic** in `next`, using Backtrader's event-driven methods only.
5. **Log trades** using `self.record_trade(trade_dict)`.
6. **Use notification hooks** (`on_trade_entry`, `on_trade_exit`, `on_error`) as needed.

## Strategies

All strategies follow the conventions above. Example strategies include:

- **MeanReversionRSBBATRStrategy** (`src/strats/rsi_bb_atr_strategy.py`)
- **RSIBollVolumeATRStrategy** (`src/strats/rsi_bb_volume_strategy.py`)
- **BBSuperTrendVolumeBreakoutStrategy** (`src/strats/bb_volume_supertrend_strategy.py`)
- **RsiVolumeSuperTrendStrategy** (`src/strats/rsi_volume_supertrend_strategy.py`)
- **IchimokuRSIATRVolumeStrategy** (`src/strats/ichimoku_rsi_atr_volume_strategy.py`)

## Optimizers

Optimizers use Bayesian optimization to find the best parameters for each strategy. Each optimizer is paired with a strategy and follows a similar interface.

## Development

1. Make sure your virtual environment is activated
2. Install new dependencies with:
```bash
pip install package_name
pip freeze > requirements.txt
```

## Testing

Run tests with:
```bash
pytest
```

## Quick Start Example

Here is a minimal example of how to run a Backtrader strategy using the new conventions:

```python
import backtrader as bt
import pandas as pd
from src.strats.rsi_bb_volume_strategy import RSIBollVolumeATRStrategy

# Load your data (CSV with columns: datetime, open, high, low, close, volume)
df = pd.read_csv('data/all/ETHUSDT_4h_20220101_20230101.csv', parse_dates=['datetime'], index_col='datetime')

# Prepare Backtrader data feed
data = bt.feeds.PandasData(dataname=df)

# Set up Cerebro
cerebro = bt.Cerebro()
cerebro.adddata(data)
cerebro.addstrategy(RSIBollVolumeATRStrategy, printlog=True)
cerebro.broker.setcash(10000.0)
cerebro.broker.setcommission(commission=0.001)

# Run the backtest
print('Starting Portfolio Value: %.2f' % cerebro.broker.getvalue())
cerebro.run()
print('Final Portfolio Value: %.2f' % cerebro.broker.getvalue())

# Access trade logs from the strategy instance
strategy_instance = cerebro.runstrats[0][0]
import pandas as pd
trades_df = pd.DataFrame(strategy_instance.trades)
print(trades_df)
```

- Replace the CSV path and strategy as needed.
- All strategies follow the same conventions for logging and parameterization.

## Quick Start Example: Optimizer

Here is a minimal example of how to run an optimizer for a strategy:

```python
from src.optimizer.rsi_bb_volume_optimizer import RSIBBVolumeOptimizer

# Path to your historical data CSV
csv_path = 'data/all/ETHUSDT_4h_20220101_20230101.csv'

# Create the optimizer instance
optimizer = RSIBBVolumeOptimizer(
    strategy_name='RSIBollVolumeATRStrategy',
    strategy_class=None  # The optimizer will import the correct class internally
)

# Run optimization (this will search for the best parameters)
results = optimizer.run_optimization(
    data_file=csv_path,
    n_calls=20,  # Number of optimization iterations
    n_initial_points=5,  # Number of random initial points
    random_state=42
)

# Print the best result
print('Best parameters:', results['best_params'])
print('Best metrics:', results['best_metrics'])

# Save all results to a file
import json
with open('optimization_results.json', 'w') as f:
    json.dump(results, f, indent=2)
```

- Replace the optimizer and CSV path as needed.
- Each optimizer exposes a `run_optimization` method and uses the standardized strategy interface.
- Results include the best parameters, best metrics, and a full optimization history.

## Usage

### Running the Web GUI

1. Activate your virtual environment.
2. Set environment variables for sensitive config (see `.env.example` or `config/donotshare/donotshare.py`).
3. Start the web GUI:
   ```bash
   python src/management/webgui/app.py
   ```
4. Open your browser to [http://localhost:5000](http://localhost:5000) (or the port you configured).

### Running the REST API

1. Activate your virtual environment.
2. Set environment variables for API credentials and port.
3. Start the API server:
   ```bash
   python src/management/api/api.py
   ```
4. Use tools like `curl`, Postman, or your own scripts to interact with the API.

### Running the Telegram Bot

1. Set your Telegram bot token in the config.
2. Run:
   ```bash
   python src/management/telegram/telegram_mgmt.py
   ```

## Deployment

### Docker (Recommended for Production)

1. Build the Docker image:
   ```bash
   docker build -t crypto-trading-bot .
   ```
2. Run the container:
   ```bash
   docker run -d -p 5000:5000 --env-file .env crypto-trading-bot
   ```
3. For production, use a WSGI server (e.g., Gunicorn) and a reverse proxy (e.g., Nginx) for SSL and static files.

### Environment Variables
- Store all secrets (API keys, DB URIs, email credentials) in a `.env` file or environment variables.
- Example variables:
  - `WEBGUI_LOGIN`, `WEBGUI_PASSWORD`, `WEBGUI_PORT`
  - `API_LOGIN`, `API_PASSWORD`, `API_PORT`
  - `MAIL_USERNAME`, `MAIL_PASSWORD`
  - `TELEGRAM_BOT_TOKEN`

### Database
- By default, uses SQLite for user/session storage. For production, consider PostgreSQL or MySQL.

### Log Files
- Logs are written to `logs/log/app.log`, `logs/log/app_errors.log`, and `logs/log/trades.log`.
- Ensure the `logs/log/` directory exists and is writable.

## Troubleshooting

### Common Issues
- **Web GUI/API not starting**: Check for missing environment variables or port conflicts.
- **Database errors**: Ensure the `db/` directory exists and is writable. For SQLite, check file permissions.
- **No data in charts**: Verify your CSV data files are present in `data/all/` and correctly formatted.
- **Email/Telegram notifications not working**: Double-check credentials and network access.
- **Strategy errors**: Review logs in `logs/log/app.log` and `logs/log/app_errors.log` for stack traces.
- **Docker issues**: Ensure Docker has access to the project directory and environment variables.

### Getting Help
- Check the [CHANGELOG](docs/CHANGELOG.md) for recent changes.
- Review the [OpenAPI spec](docs/openapi.yaml) for API details.
- For bugs or feature requests, open an issue on the project repository.

---

For more information, see the in-code docstrings and comments, or contact the project maintainers. 