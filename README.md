# Trading Framework

A modular framework for developing, testing, and optimizing cryptocurrency and shares trading strategies using Backtrader.

## Project Structure

```
crypto-trading/
├── config/                 # Configuration files
│   ├── donotshare/        # Sensitive configuration files (API keys, etc.)
│   ├── optimizer/         # Optimization configuration
│   └── trading/          # Trading strategy configurations
│
├── data/                  # Data storage directory
│
├── db/                    # Database files
│
├── docs/                  # Documentation
│
├── logs/                  # Log files
│
├── results/              # Backtesting and optimization results
│
├── src/                  # Source code
│   ├── analyzer/         # Analysis tools and metrics
│   ├── broker/          # Exchange/broker integrations
│   ├── data/            # Data handling and processing
│   ├── entry/           # Entry strategy implementations
│   ├── exit/            # Exit strategy implementations
│   ├── indicator/       # Technical indicators
│   ├── management/      # Position and risk management
│   ├── ml/              # Machine learning models
│   ├── notification/    # Notification systems
│   ├── optimizer/       # Strategy optimization
│   ├── plotter/         # Visualization tools
│   ├── screener/        # Market screening tools
│   ├── strategy/        # Trading strategies
│   ├── trading/         # Core trading functionality
│   └── util/            # Utility functions
│
├── tests/               # Test suite
│
├── .gitignore          # Git ignore file
├── requirements.txt    # Python dependencies
├── setup.py           # Package setup file
└── TODO.md            # Project roadmap and tasks
```

## Features

- **Modular Strategy Design**
  - Separate entry and exit logic
  - Mixin-based architecture for easy strategy composition
  - Support for multiple entry and exit strategies

### Source Code (`src/`)
- **Analyzer**: Performance analysis and metrics calculation
- **Broker**: Exchange API integrations and order management
- **Data**: Data fetching, processing, and storage
- **Entry/Exit**: Trading signal generation and position management
- **Indicator**: Technical analysis indicators (RSI, Bollinger Bands, etc.)
- **Management**: Position sizing and risk management
- **ML**: Machine learning models for prediction
- **Notification**: Alert and notification systems
- **Optimizer**: Strategy parameter optimization
- **Plotter**: Data visualization and charting
- **Screener**: Market scanning and opportunity identification
- **Strategy**: Trading strategy implementations
- **Trading**: Core trading engine and execution
- **Util**: Helper functions and utilities

### Data and Results
- `data/`: Historical price data and market information
- `results/`: Backtesting results and optimization outputs
- `logs/`: System and trading logs
- `db/`: Database files for persistent storage

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