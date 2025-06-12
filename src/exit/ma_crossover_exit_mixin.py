"""
Moving Average Crossover Exit Mixin

This module implements an exit strategy based on price crossing below a moving average.
The strategy exits when:
1. Price crosses below the specified moving average
2. The moving average can be either Simple (SMA) or Exponential (EMA)

Parameters:
    ma_period (int): Period for moving average calculation (default: 20)
    ma_type (str): Type of moving average ('sma' or 'ema') (default: 'sma')
    use_talib (bool): Whether to use TA-Lib for calculations (default: False)

This strategy is particularly effective for:
1. Trend following systems
2. Exiting when trend momentum weakens
3. Protecting profits in trending markets
4. Adapting to different market conditions by using different MA types

The strategy can be used as a standalone exit or combined with other exit strategies
for more robust position management.
"""

from typing import Any, Dict

import backtrader as bt
from src.exit.exit_mixin import BaseExitMixin


class MACrossoverExitMixin(BaseExitMixin):
    """Exit mixin based on price crossing below moving average"""

    # Define default values as class constants
    DEFAULT_MA_PERIOD = 20
    DEFAULT_MA_TYPE = "sma"
    DEFAULT_USE_TALIB = False

    def __init__(self, params: Dict[str, Any]):
        super().__init__(params)
        self.ma_period = params.get("ma_period", self.DEFAULT_MA_PERIOD)
        self.ma_type = params.get("ma_type", self.DEFAULT_MA_TYPE)
        self.use_talib = params.get("use_talib", self.DEFAULT_USE_TALIB)

    def get_required_params(self) -> list:
        """There are no required parameters - all have default values"""
        return []

    def get_default_params(self) -> Dict[str, Any]:
        """Default parameters"""
        return {
            "ma_period": self.DEFAULT_MA_PERIOD,
            "ma_type": self.DEFAULT_MA_TYPE,
            "use_talib": self.DEFAULT_USE_TALIB,
        }

    def _init_indicators(self):
        """Initialization of Moving Average indicator"""
        if self.strategy is None:
            raise ValueError("Strategy must be set before initializing indicators")

        # Create MA indicator with parameters from configuration
        ma_type = self.ma_type.lower()
        
        if self.use_talib:
            try:
                import talib
                
                if ma_type == "sma":
                    self.indicators["ma"] = bt.indicators.TALibIndicator(
                        self.strategy.data.close,
                        talib.SMA,
                        timeperiod=self.ma_period
                    )
                elif ma_type == "ema":
                    self.indicators["ma"] = bt.indicators.TALibIndicator(
                        self.strategy.data.close,
                        talib.EMA,
                        timeperiod=self.ma_period
                    )
                else:
                    raise ValueError(f"Unsupported MA type: {ma_type}")
            except ImportError:
                self.log("TA-Lib not available, falling back to Backtrader indicators")
                self.use_talib = False
        
        if not self.use_talib:
            if ma_type == "sma":
                self.indicators["ma"] = bt.indicators.SMA(
                    self.strategy.data.close, period=self.ma_period
                )
            elif ma_type == "ema":
                self.indicators["ma"] = bt.indicators.EMA(
                    self.strategy.data.close, period=self.ma_period
                )
            else:
                raise ValueError(f"Unsupported MA type: {ma_type}")

    def should_exit(self) -> bool:
        """
        Exit logic: Exit when price crosses below the moving average
        """
        if not self.indicators:
            return False

        current_price = self.strategy.data.close[0]
        ma = self.indicators["ma"][0]

        return current_price < ma
