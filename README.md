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

## Architecture

### Indicator Management

The system uses a centralized indicator management architecture to handle both Backtrader native indicators and TA-Lib indicators consistently.

#### Indicator Factory

The `IndicatorFactory` class (`src/indicator/indicator_factory.py`) is the central component for indicator management:

```python
class IndicatorFactory:
    def __init__(self, data: bt.DataBase, use_talib: bool = False):
        self.data = data
        self.use_talib = use_talib
        self.indicators = {}
```

Key features:
- Creates and manages both TA-Lib and Backtrader indicators
- Handles indicator lifecycle
- Provides consistent interface for all indicators
- Caches indicators to prevent duplicate creation

Available indicators:
- RSI (Relative Strength Index)
- Bollinger Bands
- ATR (Average True Range)
- SMA (Simple Moving Average)

#### Mixin Architecture

Mixins use the IndicatorFactory to create and manage indicators:

```python
class BaseEntryMixin:
    def __init__(self, params: Optional[Dict[str, Any]] = None):
        self.strategy = None
        self.params = params or {}
        self.indicators = {}
        self.indicator_factory = None

    def init_entry(self, strategy, additional_params: Optional[Dict[str, Any]] = None):
        self.strategy = strategy
        self.indicator_factory = IndicatorFactory(
            data=self.strategy.data,
            use_talib=self.strategy.use_talib
        )
```

Benefits:
1. Clean separation of concerns
   - Indicator creation is handled by the factory
   - Mixins focus on strategy logic
   - Strategy manages overall flow

2. Consistent indicator handling
   - Same interface for all indicators
   - Unified error handling
   - Proper data readiness checks

3. Better maintainability
   - Centralized indicator management
   - Easy to add new indicators
   - Clear responsibility boundaries

4. Improved error handling
   - Factory handles indicator creation errors
   - Mixins handle strategy logic errors
   - Clear error boundaries

#### Usage Example

```python
# In a mixin
def _init_indicators(self):
    # Create RSI indicator
    rsi = self.indicator_factory.create_rsi(
        name=self.rsi_name,
        period=self.get_param("rsi_period")
    )
    self.register_indicator(self.rsi_name, rsi)

    # Create Bollinger Bands indicator
    bb = self.indicator_factory.create_bollinger_bands(
        name=self.bb_name,
        period=self.get_param("bb_period"),
        devfactor=self.get_param("bb_stddev")
    )
    self.register_indicator(self.bb_name, bb)
```

#### Data Flow

```
Backtrader Data -> IndicatorFactory -> Indicators -> Mixins -> Strategy Logic
```

1. Backtrader provides data feed
2. IndicatorFactory creates and manages indicators
3. Mixins use indicators for strategy logic
4. Strategy coordinates overall flow

#### Error Handling

The architecture includes comprehensive error handling:
1. Factory handles indicator creation errors
2. Mixins handle strategy logic errors
3. Strategy manages overall error flow

#### Adding New Indicators

To add a new indicator:
1. Add indicator class to `src/indicator/`
2. Add creation method to `IndicatorFactory`
3. Use in mixins through factory

Example:
```python
# In IndicatorFactory
def create_new_indicator(self, name: str, **params) -> Any:
    if name in self.indicators:
        return self.indicators[name]
    
    if self.use_talib:
        indicator = TALibNewIndicator(self.data, **params)
    else:
        indicator = BacktraderNewIndicator(self.data, **params)
    
    self.indicators[name] = indicator
    return indicator
``` 