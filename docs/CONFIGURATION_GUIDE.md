# Configuration Management Guide

This guide explains the new centralized configuration management system that addresses the issues of scattered configurations, lack of schema validation, and difficulty managing environment-specific configs.

## Overview

The new configuration system provides:

1. **Unified Configuration Schema** - All configurations use Pydantic-based schemas with validation
2. **Environment-Specific Configs** - Separate configurations for dev/staging/prod environments
3. **Configuration Registry** - Centralized tracking and discovery of all configurations
4. **Schema Validation** - Comprehensive validation with detailed error messages
5. **Configuration Templates** - Pre-defined templates for common use cases
6. **Hot-reload Support** - Automatic reloading during development

## Architecture

```
config/
├── development/          # Development environment configs
│   ├── trading/
│   ├── optimizer/
│   └── data/
├── staging/             # Staging environment configs
├── production/          # Production environment configs
├── templates/           # Configuration templates
└── schemas/            # Schema definitions
```

## Quick Start

### 1. Initialize Configuration Manager

```python
from src.config import ConfigManager

# Initialize with environment
config_manager = ConfigManager(
    config_dir="config",
    environment="development"
)
```

### 2. Create Configuration from Template

```python
# Create a paper trading bot configuration
trading_config = config_manager.create_config(
    "trading_paper",
    bot_id="my_paper_bot",
    symbol="BTCUSDT",
    initial_balance=5000.0
)

# Save the configuration
config_path = config_manager.save_config(trading_config, "my_paper_bot.json")
```

### 3. Load and Use Configuration

```python
# Load a specific configuration
config = config_manager.get_config("my_paper_bot")

# Get all trading configurations
trading_configs = config_manager.get_trading_configs()

# Search configurations
results = config_manager.search_configs("BTCUSDT", "trading")
```

## Configuration Types

### 1. Trading Configuration

Trading configurations define bot behavior, risk management, and strategy parameters.

```json
{
    "environment": "development",
    "version": "1.0.0",
    "description": "Paper trading bot for strategy testing",
    
    "bot_id": "paper_bot_001",
    "broker": {
        "type": "binance_paper",
        "initial_balance": 10000.0,
        "commission": 0.001
    },
    "trading": {
        "symbol": "BTCUSDT",
        "position_size": 0.1,
        "max_positions": 1,
        "max_drawdown_pct": 20.0,
        "max_exposure": 1.0
    },
    "data": {
        "data_source": "binance",
        "symbol": "BTCUSDT",
        "interval": "1h",
        "lookback_bars": 1000,
        "retry_interval": 60,
        "testnet": true
    },
    "strategy": {
        "type": "custom",
        "entry_logic": {
            "name": "RSIBBVolumeEntryMixin",
            "params": {
                "rsi_period": 14,
                "rsi_oversold": 30,
                "bb_period": 20,
                "bb_dev": 2.0
            }
        },
        "exit_logic": {
            "name": "RSIBBExitMixin",
            "params": {
                "rsi_period": 14,
                "rsi_overbought": 70
            }
        }
    },
    "risk_management": {
        "stop_loss_pct": 5.0,
        "take_profit_pct": 10.0,
        "max_daily_trades": 10,
        "max_daily_loss": 50.0
    },
    "logging": {
        "level": "INFO",
        "save_trades": true,
        "log_file": "logs/paper/trading_bot.log"
    },
    "notifications": {
        "enabled": true,
        "telegram": {
            "enabled": false,
            "notify_on": ["trade_entry", "trade_exit", "error"]
        }
    }
}
```

### 2. Optimizer Configuration

Optimizer configurations define parameter optimization settings.

```json
{
    "environment": "development",
    "version": "1.0.0",
    "description": "Basic optimization configuration",
    
    "optimizer_type": "optuna",
    "initial_capital": 1000.0,
    "commission": 0.001,
    "n_trials": 100,
    "n_jobs": 1,
    "position_size": 0.1,
    
    "entry_strategies": [
        {
            "name": "RSIBBVolumeEntryMixin",
            "params": {
                "rsi_period": {"type": "int", "low": 5, "high": 30, "default": 14},
                "bb_period": {"type": "int", "low": 10, "high": 50, "default": 20}
            }
        }
    ],
    "exit_strategies": [
        {
            "name": "RSIBBExitMixin",
            "params": {
                "rsi_period": {"type": "int", "low": 5, "high": 30, "default": 14}
            }
        }
    ],
    
    "plot": true,
    "save_trades": true,
    "output_dir": "results"
}
```

### 3. Data Configuration

Data configurations define data feed settings.

```json
{
    "environment": "development",
    "version": "1.0.0",
    "description": "Binance data feed configuration",
    
    "data_source": "binance",
    "symbol": "BTCUSDT",
    "interval": "1h",
    "lookback_bars": 1000,
    "retry_interval": 60,
    "testnet": true
}
```

## Environment Management

### Environment-Specific Configurations

The system supports multiple environments with different settings:

```python
# Development environment
dev_config = ConfigManager(config_dir="config", environment="development")

# Staging environment
staging_config = ConfigManager(config_dir="config", environment="staging")

# Production environment
prod_config = ConfigManager(config_dir="config", environment="production")
```

### Environment Variables

Set the environment using environment variables:

```bash
export TRADING_ENV=production
python your_script.py
```

### Environment-Specific Settings

Each environment can have different default values:

- **Development**: Debug logging, hot-reload enabled, testnet APIs
- **Staging**: Info logging, production-like settings, test data
- **Production**: Warning logging, full security, live APIs

## Schema Validation

### Automatic Validation

All configurations are automatically validated against Pydantic schemas:

```python
# This will raise validation errors if invalid
try:
    config = TradingConfig(**config_data)
except ValidationError as e:
    print(f"Configuration validation failed: {e}")
```

### Validation Rules

Common validation rules include:

- **Required Fields**: Essential fields must be present
- **Type Checking**: Fields must have correct data types
- **Range Validation**: Numeric values must be within valid ranges
- **Enum Validation**: String fields must match allowed values
- **Cross-Field Validation**: Related fields must be consistent

### Custom Validation

Add custom validation rules:

```python
@validator('take_profit_pct')
def validate_take_profit(cls, v, values):
    """Ensure take profit is greater than stop loss"""
    if 'stop_loss_pct' in values and v <= values['stop_loss_pct']:
        raise ValueError("Take profit must be greater than stop loss")
    return v
```

## Configuration Templates

### Available Templates

The system provides pre-defined templates:

- `trading_paper`: Paper trading bot with safe defaults
- `trading_live`: Live trading bot with full risk management
- `trading_dev`: Development bot with debugging enabled
- `optimizer_basic`: Basic optimization configuration
- `optimizer_advanced`: Advanced optimization with extended parameters
- `data_binance`: Binance data feed configuration
- `data_yahoo`: Yahoo Finance data feed configuration
- `data_ibkr`: IBKR data feed configuration

### Using Templates

```python
# Create configuration from template
config = config_manager.create_config(
    "trading_paper",
    bot_id="my_bot",
    symbol="ETHUSDT",
    initial_balance=2000.0
)

# List available templates
templates = config_manager.templates.list_templates()
```

## Configuration Registry

### Registry Features

The configuration registry provides:

- **Discovery**: Find configurations by type, tags, or search terms
- **Relationships**: Track relationships between configurations
- **Metadata**: Store additional information about configurations
- **Statistics**: Get usage statistics and metrics

### Registry Usage

```python
# Get all trading configurations
trading_configs = config_manager.get_trading_configs()

# Search configurations
results = config_manager.search_configs("BTCUSDT")

# Get configuration metadata
metadata = config_manager.registry.get_config_metadata("my_bot")

# Get related configurations
related = config_manager.registry.get_related_configs("my_bot")
```

## Hot-Reload Support

### Development Mode

Enable hot-reload for automatic configuration updates:

```python
# Enable hot-reload
config_manager.enable_hot_reload(True)

# Configurations will automatically reload when files change
```

### File Watching

The system watches for changes to:

- JSON configuration files
- YAML configuration files
- Environment-specific directories

## Migration from Old System

### Automatic Migration

Use the migration script to convert old configurations:

```bash
python src/config/migrate_configs.py --old-dir config --new-dir config_new --backup
```

### Migration Features

- **Automatic Discovery**: Finds all old configuration files
- **Type Detection**: Automatically detects configuration types
- **Schema Transformation**: Converts to new schema format
- **Validation**: Validates migrated configurations
- **Backup**: Creates backup of original files
- **Report**: Generates detailed migration report

### Migration Process

1. **Discovery**: Scan old configuration directory
2. **Transformation**: Convert to new schema format
3. **Validation**: Validate migrated configurations
4. **Organization**: Organize by environment
5. **Backup**: Create backup of original files

## Best Practices

### 1. Environment Separation

- Use separate configurations for each environment
- Never use production configs in development
- Use environment variables for sensitive data

### 2. Configuration Validation

- Always validate configurations before use
- Use type hints and validation rules
- Test configurations in development first

### 3. Version Control

- Version control configuration templates
- Don't version control sensitive data
- Use configuration inheritance for common settings

### 4. Documentation

- Document configuration parameters
- Provide examples for each configuration type
- Keep configuration schemas up to date

### 5. Testing

- Test configurations in isolation
- Validate edge cases and error conditions
- Use automated testing for configuration validation

## Troubleshooting

### Common Issues

1. **Validation Errors**
   - Check required fields are present
   - Verify data types match schema
   - Ensure values are within valid ranges

2. **Configuration Not Found**
   - Check environment setting
   - Verify file paths and naming
   - Use configuration discovery tools

3. **Hot-Reload Not Working**
   - Ensure file watching is enabled
   - Check file permissions
   - Verify file format is supported

### Debug Mode

Enable debug logging for detailed information:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

config_manager = ConfigManager()
```

### Configuration Validation

Validate configurations manually:

```python
# Validate specific file
is_valid, errors, warnings = config_manager.validate_config_file("config.json")

if not is_valid:
    for error in errors:
        print(f"Error: {error}")
```

## API Reference

### ConfigManager

Main configuration management class.

```python
class ConfigManager:
    def __init__(self, config_dir: str = "config", environment: str = None)
    def get_config(self, config_id: str) -> Optional[Any]
    def create_config(self, config_type: str, **kwargs) -> Any
    def save_config(self, config: Any, filename: str = None) -> str
    def delete_config(self, config_id: str) -> bool
    def enable_hot_reload(self, enabled: bool = True)
    def validate_config_file(self, config_path: str) -> tuple[bool, List[str]]
```

### Configuration Schemas

Pydantic-based configuration schemas.

```python
class TradingConfig(ConfigSchema):
    bot_id: str
    broker: Dict[str, Any]
    trading: Dict[str, Any]
    data: DataConfig
    strategy: Dict[str, Any]
    risk_management: RiskManagementConfig
    logging: LoggingConfig
    notifications: NotificationConfig

class OptimizerConfig(ConfigSchema):
    optimizer_type: str
    initial_capital: float
    commission: float
    n_trials: int
    entry_strategies: List[Dict[str, Any]]
    exit_strategies: List[Dict[str, Any]]

class DataConfig(ConfigSchema):
    data_source: DataSourceType
    symbol: str
    interval: str
    lookback_bars: int
```

## Examples

### Complete Example

```python
from src.config import ConfigManager

# Initialize configuration manager
config_manager = ConfigManager(environment="development")

# Create a new trading bot configuration
trading_config = config_manager.create_config(
    "trading_paper",
    bot_id="example_bot",
    symbol="BTCUSDT",
    initial_balance=5000.0,
    description="Example trading bot for testing"
)

# Save the configuration
config_path = config_manager.save_config(trading_config)

# Load and use the configuration
loaded_config = config_manager.get_config("example_bot")

# Enable hot-reload for development
config_manager.enable_hot_reload(True)

# Search for configurations
results = config_manager.search_configs("BTCUSDT")

# Get configuration statistics
stats = config_manager.get_config_summary()
print(f"Total configurations: {stats['total_configs']}")
```

This new configuration system provides a robust, scalable, and maintainable way to manage all aspects of the trading platform configuration. 