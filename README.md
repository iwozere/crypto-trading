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
│   │   └── rsi_volume_supertrend_strategy.py
│   ├── webgui/
│   │   ├── static/
│   │   └── templates/
│   └── ...
├── tests/
└── ...
```

## Optimizers and Strategies

This project includes four main trading strategies and their corresponding optimizers. Each optimizer uses Bayesian optimization to find the best parameters for its strategy.

### Strategies

- **MeanReversionRSBBATRStrategy**
  - *Description*: A mean-reversion strategy using Bollinger Bands, RSI, and ATR. Designed for ranging/sideways markets (e.g., forex pairs, altcoins) and timeframes from 5m to 4H. High win rate in sideways markets, but can be whipsawed during breakouts.
  - *File*: `src/strats/rsi_bb_atr_strategy.py`

- **RSIBollVolumeATRStrategy**
  - *Description*: A mean-reversion strategy that combines RSI, Bollinger Bands, and Volume with ATR-based position management. Suitable for assets with mean-reverting behavior and volume spikes.
  - *File*: `src/strats/rsi_bb_volume_strategy.py`

- **BBSuperTrendVolumeBreakoutStrategy**
  - *Description*: A breakout strategy using Bollinger Bands, SuperTrend, and Volume. Designed for volatile breakout markets (crypto, small-cap stocks). Captures big moves early, but needs filtering to avoid fakeouts.
  - *File*: `src/strats/bb_volume_supertrend_strategy.py`

- **RsiVolumeSuperTrendStrategy**
  - *Description*: A trend-following strategy using SuperTrend for trend direction, RSI for pullback entries, and Volume for confirmation. ATR is used for risk management. Best for trending markets (crypto, strong stocks, indices).
  - *File*: `src/strats/rsi_volume_supertrend_strategy.py`

### Optimizers

- **MeanReversionRSBBATROptimizer**
  - *Description*: Optimizes the MeanReversionRSBBATRStrategy for ranging/sideways markets. Uses Bayesian optimization to maximize risk-adjusted returns.
  - *File*: `src/optimizer/rsi_bb_atr_optimizer.py`

- **RsiBBVolumeOptimizer**
  - *Description*: Optimizes the RSIBollVolumeATRStrategy for mean-reverting, volume-driven markets. Uses Bayesian optimization to maximize profit and minimize drawdown.
  - *File*: `src/optimizer/rsi_bb_volume_optimizer.py`

- **BBSuperTrendVolumeBreakoutOptimizer**
  - *Description*: Optimizes the BBSuperTrendVolumeBreakoutStrategy for volatile breakout markets. Uses Bayesian optimization to capture large moves while filtering out fakeouts.
  - *File*: `src/optimizer/bb_volume_supertrend_optimizer.py`

- **RsiVolumeSuperTrendOptimizer**
  - *Description*: Optimizes the RsiVolumeSuperTrendStrategy for trending markets. Uses Bayesian optimization to maximize trend capture and minimize whipsaws.
  - *File*: `src/optimizer/rsi_volume_supertrend_optimizer.py`

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