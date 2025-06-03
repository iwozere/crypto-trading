# Crypto Trading Platform Developer Guide

This guide explains how to extend the platform by adding new strategies, indicators, and optimizers.

---

## 1. Adding a New Strategy

### a. Use the Strategy Template
- Copy `src/strategy/strategy_template.py` to a new file, e.g. `src/strategy/my_new_strategy.py`.

### b. Fill in the Template
- Update the class name and docstrings.
- Define your parameters in `params`.
- Initialize your indicators in `__init__`.
- Implement your entry/exit logic in `next()`.
- Use `self.record_trade(trade_dict)` to log trades.

#### Example:
```python
from src.strategy.base_strategy import BaseStrategy
import backtrader as bt

class MyNewStrategy(BaseStrategy):
    params = (
        ('my_period', 14),
        ('printlog', True),
    )
    def __init__(self):
        self.sma = bt.indicators.SimpleMovingAverage(self.data.close, period=self.p.my_period)
    def next(self):
        if not self.position and self.data.close[0] > self.sma[0]:
            self.buy()
        elif self.position and self.data.close[0] < self.sma[0]:
            self.close()
```

---

## 2. Adding a New Indicator

### a. Create the Indicator File
- Add your indicator to `src/indicator/`, e.g. `src/indicator/my_indicator.py`.

### b. Define the Indicator Class
- Inherit from `bt.Indicator` or `bt.indicators.Indicator`.
- Implement the calculation logic in `__init__` or `next()`.

#### Example:
```python
import backtrader as bt

class MyIndicator(bt.Indicator):
    lines = ('myline',)
    params = (('period', 14),)
    def __init__(self):
        self.lines.myline = bt.indicators.SimpleMovingAverage(self.data, period=self.p.period)
```

---

## 3. Adding a New Optimizer

### a. Use the Optimizer Template
- Copy `src/optimizer/optimizer_template.py` to a new file, e.g. `src/optimizer/my_new_optimizer.py`.

### b. Fill in the Template
- Update the class name and docstrings.
- Define your parameter search space in `self.search_space`.
- Implement the optimization logic in `optimize_single_file`.
- Implement result plotting in `plot_results` if needed.

#### Example:
```python
from src.optimizer.base_optimizer import BaseOptimizer
from skopt.space import Integer, Real

class MyNewOptimizer(BaseOptimizer):
    def __init__(self):
        super().__init__()
        self.search_space = [
            Integer(10, 30, name='my_period'),
            Real(1.0, 3.0, name='my_threshold'),
        ]
        self.default_params = {'my_period': 14, 'my_threshold': 2.0}
    def optimize_single_file(self, filename):
        # Implement optimization logic here
        pass
```

---

## 4. Registering Your Strategy or Optimizer (Optional)
- If you use a registry or factory pattern, add your new class to the registry in `src/strategy/strategy_registry.py` or similar.

---

## 5. Testing
- Add unit tests for your new strategy in `tests/test_strategies.py`.
- Add unit tests for your new optimizer in `tests/test_optimizers.py`.
- Use pytest for all tests.

---

## 6. Tips
- Follow the structure and docstring style of existing files.
- Use the logging and trade recording utilities in `BaseStrategy`.
- For live trading, ensure your strategy works with the broker interface.

---

For more details, see the code comments and templates in the `src/` directory. 