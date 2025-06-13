# Developer Guide

## Adding New Entry/Exit Mixins

### Creating a New Mixin

1. Create a new file in the appropriate directory:
   - For entry mixins: `src/entry/your_mixin_name_mixin.py`
   - For exit mixins: `src/exit/your_mixin_name_mixin.py`

2. Implement your mixin class following this template:

```python
from typing import Any, Dict
import backtrader as bt
from src.entry.entry_mixin import BaseEntryMixin  # or BaseExitMixin for exit mixins

class YourMixin(BaseEntryMixin):  # or BaseExitMixin for exit mixins
    """Your mixin description"""
    
    def get_required_params(self) -> list:
        """List of required parameters"""
        return []
    
    def get_default_params(self) -> Dict[str, Any]:
        """Default parameter values"""
        return {
            "param1": default_value1,
            "param2": default_value2,
        }
    
    def _init_indicators(self):
        """Initialize your indicators"""
        if self.strategy is None:
            raise ValueError("Strategy must be set before initializing indicators")
            
        # Create your indicators here
        # Example:
        self.indicators["indicator1"] = bt.indicators.YourIndicator(
            self.strategy.data.close,
            period=self.get_param("param1")
        )
    
    def should_enter(self) -> bool:  # or should_exit() for exit mixins
        """Your entry/exit logic"""
        if not self.indicators:
            return False
            
        # Implement your logic here
        return your_condition
```

### Registering Your Mixin

1. Add your mixin to the appropriate factory:
   - For entry mixins: `src/entry/entry_mixin_factory.py`
   - For exit mixins: `src/exit/exit_mixin_factory.py`

2. Import your mixin and add it to the registry:

```python
from src.entry.your_mixin_name_mixin import YourMixin  # or appropriate path

ENTRY_MIXIN_REGISTRY = {
    # ... existing mixins ...
    "YourMixin": YourMixin,
}
```

### Creating Configuration Files

1. Create a JSON configuration file in the appropriate directory:
   - For entry mixins: `config/optimizer/entry/your_mixin_name.json`
   - For exit mixins: `config/optimizer/exit/your_mixin_name.json`

2. Define the configuration structure:

```json
{
    "name": "YourMixin",
    "params": {
        "param1": {
            "type": "int",  // or "float", "bool"
            "min": 5,       // for numeric types
            "max": 30,      // for numeric types
            "default": 10
        },
        "param2": {
            "type": "float",
            "min": 0.1,
            "max": 1.0,
            "default": 0.5
        },
        "param3": {
            "type": "bool",
            "default": true
        }
    },
    "description": "Description of your mixin's strategy and parameters"
}
```

3. Configuration file guidelines:
   - Use descriptive parameter names
   - Set reasonable min/max values for optimization
   - Include default values that work well in most cases
   - Add a clear description of the strategy
   - Document any special parameter requirements

Example configuration for RSI and Bollinger Bands mixin:

```json
{
    "name": "RSIBBExitMixin",
    "params": {
        "rsi_period": {
            "type": "int",
            "min": 5,
            "max": 30,
            "default": 14
        },
        "rsi_overbought": {
            "type": "float",
            "min": 60,
            "max": 90,
            "default": 70
        },
        "bb_period": {
            "type": "int",
            "min": 10,
            "max": 50,
            "default": 20
        },
        "bb_stddev": {
            "type": "float",
            "min": 1.0,
            "max": 3.0,
            "default": 2.0
        },
        "use_bb_touch": {
            "type": "bool",
            "default": true
        }
    },
    "description": "Exit strategy based on RSI overbought condition and Bollinger Bands upper band touch. Exits when RSI is overbought and price touches or crosses above the upper Bollinger Band."
}
```

### Using Your Mixin

1. Create a strategy configuration using your mixin:

```python
strategy_config = {
    "entry_logic": {  # or "exit_logic" for exit mixins
        "name": "YourMixin",
        "params": {
            "param1": value1,
            "param2": value2,
        }
    },
    # ... other configuration ...
}
```

2. Use the configuration with the CustomStrategy:

```python
strategy = CustomStrategy(strategy_config=strategy_config)
```

### Best Practices

1. **Indicator Management**:
   - Each mixin maintains its own `indicators` dictionary
   - Use unique names for indicators within your mixin
   - Initialize indicators in `_init_indicators()`

2. **Parameter Handling**:
   - Define default values in `get_default_params()`
   - List required parameters in `get_required_params()`
   - Use `self.get_param()` to safely access parameters

3. **Documentation**:
   - Add docstrings explaining your mixin's purpose
   - Document all parameters and their effects
   - Include usage examples in comments

4. **Testing**:
   - Test your mixin with different parameter combinations
   - Verify indicator calculations
   - Test edge cases and error conditions

5. **Configuration**:
   - Create comprehensive configuration files
   - Set appropriate optimization ranges
   - Document parameter relationships and dependencies
   - Include clear strategy descriptions

### Example: RSI and Bollinger Bands Mixin

Here's a complete example of creating a new mixin:

```python
"""
RSI and Bollinger Bands Mixin

This module implements a strategy based on RSI and Bollinger Bands.
The strategy enters/exits when:
1. RSI is in the oversold/overbought zone
2. Price touches the lower/upper Bollinger Band

Parameters:
    rsi_period (int): Period for RSI calculation
    rsi_threshold (float): RSI threshold for signals
    bb_period (int): Period for Bollinger Bands
    bb_stddev (float): Standard deviation multiplier
"""

class RSIBBMixin(BaseEntryMixin):
    def get_default_params(self) -> Dict[str, Any]:
        return {
            "rsi_period": 14,
            "rsi_threshold": 30,
            "bb_period": 20,
            "bb_stddev": 2.0,
        }
    
    def _init_indicators(self):
        self.indicators["rsi"] = bt.indicators.RSI(
            self.strategy.data.close,
            period=self.get_param("rsi_period")
        )
        
        bb = bt.indicators.BollingerBands(
            self.strategy.data.close,
            period=self.get_param("bb_period"),
            devfactor=self.get_param("bb_stddev")
        )
        self.indicators["bb_upper"] = bb.lines.top
        self.indicators["bb_lower"] = bb.lines.bot
    
    def should_enter(self) -> bool:
        rsi = self.indicators["rsi"][0]
        price = self.strategy.data.close[0]
        bb_lower = self.indicators["bb_lower"][0]
        
        return (rsi < self.get_param("rsi_threshold") and 
                price <= bb_lower * 1.01)
``` 