# Crypto Trading Strategy Framework

A modular framework for developing, testing, and optimizing cryptocurrency trading strategies using Backtrader.

## Project Structure

```
crypto-trading/
├── config/
│   ├── optimizer/
│   │   ├── entry/              # Entry strategy configurations
│   │   │   ├── RSIBBMixin.json
│   │   │   ├── RSIIchimokuMixin.json
│   │   │   ├── RSIBBVolumeMixin.json
│   │   │   ├── RSIVolumeSuperTrendMixin.json
│   │   │   └── BBVolumeSuperTrendMixin.json
│   │   ├── exit/               # Exit strategy configurations
│   │   │   ├── ATRExitMixin.json
│   │   │   ├── FixedRatioExitMixin.json
│   │   │   ├── MACrossoverExitMixin.json
│   │   │   ├── TimeBasedExitMixin.json
│   │   │   └── TrailingStopExitMixin.json
│   │   ├── optimize_entry.yaml # Entry optimization schema
│   │   ├── optimize_exit.yaml  # Exit optimization schema
│   │   └── optimizer.json      # Main optimizer configuration
├── data/                       # Historical price data
├── src/
│   ├── analyzer/              # Custom analyzers
│   ├── entry/                 # Entry strategy mixins
│   ├── exit/                  # Exit strategy mixins
│   ├── indicators/            # Custom indicators
│   ├── optimizer/             # Optimization framework
│   ├── strategy/              # Strategy implementations
│   └── notification/          # Logging and notifications
└── studies/                   # Optimization results
```

## Features

- **Modular Strategy Design**
  - Separate entry and exit logic
  - Mixin-based architecture for easy strategy composition
  - Support for multiple entry and exit strategies

- **Entry Strategies**
  - RSI + Bollinger Bands
  - RSI + Ichimoku
  - RSI + BB + Volume
  - RSI + Volume + SuperTrend
  - BB + Volume + SuperTrend

- **Exit Strategies**
  - ATR-based exits
  - Fixed ratio exits
  - Moving Average crossover exits
  - Time-based exits
  - Trailing stop exits

- **Optimization Framework**
  - Parameter optimization using Optuna
  - Configurable optimization spaces
  - Comprehensive metrics collection
  - Results storage in JSON format

- **Analysis Tools**
  - Performance metrics (Sharpe, Sortino, Calmar ratios)
  - Risk metrics (Drawdown, Volatility)
  - Trade statistics (Win rate, Profit factor)
  - Custom analyzers for detailed analysis

## Configuration

### Entry/Exit Strategy Configuration

Each strategy mixin has its own JSON configuration file in `config/optimizer/entry/` or `config/optimizer/exit/`. Example:

```json
{
    "name": "RSIBBMixin",
    "params": {
        "rsi_period": {
            "type": "int",
            "low": 5,
            "high": 30,
            "default": 14
        },
        "bb_period": {
            "type": "int",
            "low": 10,
            "high": 50,
            "default": 20
        }
    }
}
```

### Optimizer Configuration

Main optimizer settings in `config/optimizer/optimizer.json`:

```json
{
    "optimizer_settings": {
        "optimizer_type": "optuna",
        "initial_capital": 1000.0,
        "commission": 0.001,
        "risk_free_rate": 0.01,
        "use_talib": true,
        "n_trials": 100
    }
}
```

## Usage

1. **Prepare Data**
   - Place your historical price data in CSV format in the `data/` directory
   - Data should include OHLCV columns

2. **Configure Strategies**
   - Create or modify entry/exit strategy configurations
   - Adjust parameter ranges in JSON files

3. **Run Optimization**
   ```bash
   python src/optimizer/custom_optimizer.py
   ```

4. **Analyze Results**
   - Check the `studies/` directory for optimization results
   - Each result file contains:
     - Best parameters
     - Performance metrics
     - Trade history
     - Analysis results

## Results

Optimization results are saved in JSON format with:
- Best parameters found
- Performance metrics
- Trade history
- Analysis results from all analyzers

Example metrics:
- Sharpe Ratio
- Sortino Ratio
- Calmar Ratio
- Maximum Drawdown
- Win Rate
- Profit Factor
- System Quality Number (SQN)
- And more...

## Dependencies

- backtrader
- pandas
- numpy
- optuna
- ta-lib (optional)

## Installation

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. (Optional) Install TA-Lib for enhanced performance

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request 