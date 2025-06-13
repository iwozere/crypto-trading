"""
RSI and Bollinger Bands Entry Mixin

This module implements an entry strategy based on the combination of Relative Strength Index (RSI)
and Bollinger Bands indicators. The strategy enters a position when:
1. RSI is in the oversold zone (below the configured threshold)
2. Price touches or crosses below the lower Bollinger Band
3. Optional volume conditions are met

Parameters:
    rsi_period (int): Period for RSI calculation (default: 14)
    rsi_oversold (float): RSI threshold for oversold condition (default: 30)
    bb_period (int): Period for Bollinger Bands calculation (default: 20)
    bb_stddev (float): Standard deviation multiplier for Bollinger Bands (default: 2.0)
    use_bb_touch (bool): Whether to require price touching the lower band (default: True)
    min_volume (float): Minimum volume required for entry (default: 0)

This strategy is particularly effective in ranging markets where price tends to revert to the mean
after reaching extreme levels.
"""

from typing import Any, Dict, Optional

import backtrader as bt
import numpy as np
from src.entry.base_entry_mixin import BaseEntryMixin


class RSIBBEntryMixin(BaseEntryMixin):
    """Entry mixin based on RSI and Bollinger Bands"""

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        """Initialize the mixin with parameters"""
        super().__init__(params)

    def get_required_params(self) -> list:
        """Returns a list of required parameters"""
        return []

    @classmethod
    def get_default_params(cls) -> Dict[str, Any]:
        """Returns a dictionary of default parameters"""
        return {
            "rsi_period": 14,
            "rsi_oversold": 30,
            "bb_period": 20,
            "bb_std": 2.0,
            "use_talib": False,
        }

    def _init_indicators(self):
        """Initialize RSI and Bollinger Bands indicators"""
        if not hasattr(self, 'strategy'):
            return
            
        # Initialize RSI if not already initialized
        if not hasattr(self.strategy, 'rsi'):
            # Check if TA-Lib should be used based on strategy settings
            use_talib = self.get_param("use_talib", False)
            
            if use_talib:
                try:
                    import talib
                    # Calculate RSI using TA-Lib
                    close_prices = np.array([self.strategy.data.close[i] for i in range(len(self.strategy.data))])
                    rsi_values = talib.RSI(close_prices, timeperiod=self.get_param("rsi_period"))
                    
                    # Initialize Backtrader RSI
                    self.strategy.rsi = bt.indicators.RSI(
                        self.strategy.data,
                        period=self.get_param("rsi_period")
                    )
                    
                    # Update RSI values one by one
                    for i in range(len(self.strategy.data)):
                        if i < len(rsi_values):
                            self.strategy.rsi.array[i] = rsi_values[i]
                except ImportError:
                    self.strategy.logger.warning("TA-Lib not available, using Backtrader's RSI")
                    self.strategy.rsi = bt.indicators.RSI(
                        self.strategy.data,
                        period=self.get_param("rsi_period")
                    )
            else:
                self.strategy.rsi = bt.indicators.RSI(
                    self.strategy.data,
                    period=self.get_param("rsi_period")
                )
        
        # Initialize Bollinger Bands
        use_talib = self.get_param("use_talib", False)
        if use_talib:
            try:
                import talib
                # Calculate Bollinger Bands using TA-Lib
                close_prices = np.array([self.strategy.data.close[i] for i in range(len(self.strategy.data))])
                upper, middle, lower = talib.BBANDS(
                    close_prices,
                    timeperiod=self.get_param("bb_period"),
                    nbdevup=self.get_param("bb_std"),
                    nbdevdn=self.get_param("bb_std")
                )
                
                # Initialize Backtrader Bollinger Bands
                self.strategy.bb = bt.indicators.BollingerBands(
                    self.strategy.data,
                    period=self.get_param("bb_period"),
                    devfactor=self.get_param("bb_std")
                )
                
                # Update BB values one by one
                for i in range(len(self.strategy.data)):
                    if i < len(upper):
                        self.strategy.bb.lines.top[i] = upper[i]
                        self.strategy.bb.lines.mid[i] = middle[i]
                        self.strategy.bb.lines.bot[i] = lower[i]
            except ImportError:
                self.strategy.logger.warning("TA-Lib not available, using Backtrader's Bollinger Bands")
                self.strategy.bb = bt.indicators.BollingerBands(
                    self.strategy.data,
                    period=self.get_param("bb_period"),
                    devfactor=self.get_param("bb_std")
                )
        else:
            self.strategy.bb = bt.indicators.BollingerBands(
                self.strategy.data,
                period=self.get_param("bb_period"),
                devfactor=self.get_param("bb_std")
            )

    def should_enter(self) -> bool:
        """Check if we should enter a position"""
        if not hasattr(self.strategy, 'rsi') or not hasattr(self.strategy, 'bb'):
            return False

        # Check RSI condition
        rsi_oversold = self.strategy.rsi[0] < self.get_param("rsi_oversold")
        
        # Check Bollinger Bands condition
        bb = self.strategy.bb
        current_price = self.strategy.data.close[0]
        
        # Check if price is below lower band
        below_lower = current_price < bb.lines.bot[0]
        
        return rsi_oversold and below_lower
