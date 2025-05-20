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