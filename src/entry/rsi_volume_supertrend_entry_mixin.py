"""
RSI, Volume, and Supertrend Entry Mixin

This module implements an entry strategy based on the combination of:
1. Relative Strength Index (RSI)
2. Volume analysis
3. Supertrend indicator

The strategy enters a position when:
1. RSI is in the oversold zone (below the configured threshold)
2. Volume is above its moving average
3. Supertrend indicator shows a bullish signal

Parameters:
    rsi_period (int): Period for RSI calculation (default: 14)
    rsi_oversold (float): RSI threshold for oversold condition (default: 30)
    atr_period (int): Period for ATR calculation (default: 10)
    atr_multiplier (float): Multiplier for ATR in Supertrend (default: 3.0)
    volume_ma_period (int): Period for volume moving average (default: 20)
    min_volume_ratio (float): Minimum volume ratio compared to MA (default: 1.5)

This strategy combines mean reversion (RSI), volume confirmation, and trend following (Supertrend)
to identify potential reversal points with strong momentum.
"""

from typing import Any, Dict

import backtrader as bt
import numpy as np
from src.entry.base_entry_mixin import BaseEntryMixin


class RSIVolumeSupertrendEntryMixin(BaseEntryMixin):
    """Entry mixin based on RSI, Volume, and Supertrend"""

    def __init__(self, params=None):
        """Initialize the mixin with parameters"""
        super().__init__()
        self.params = params or self.get_default_params()

    def get_required_params(self) -> list:
        """There are no required parameters - all have default values"""
        return []

    @classmethod
    def get_default_params(cls) -> Dict[str, Any]:
        """Default parameters"""
        return {
            "rsi_period": 14,
            "rsi_oversold": 30,
            "volume_ma_period": 20,
            "supertrend_period": 10,
            "supertrend_multiplier": 3.0,
        }

    def _init_indicators(self):
        """Initialize RSI, Volume MA, and Supertrend indicators"""
        if not hasattr(self, 'strategy'):
            return
            
        # Initialize RSI if not already initialized
        if not hasattr(self.strategy, 'rsi'):
            # Check if TA-Lib should be used based on strategy settings
            use_talib = getattr(self.strategy, 'use_talib', False)
            
            if use_talib:
                try:
                    import talib
                    # Calculate RSI using TA-Lib
                    close_prices = np.array([self.strategy.data.close[i] for i in range(len(self.strategy.data))])
                    rsi_values = talib.RSI(close_prices, timeperiod=self.params["rsi_period"])
                    
                    # Initialize Backtrader RSI
                    self.strategy.rsi = bt.indicators.RSI(
                        self.strategy.data,
                        period=self.params["rsi_period"]
                    )
                    
                    # Update RSI values one by one
                    for i in range(len(self.strategy.data)):
                        if i < len(rsi_values):
                            self.strategy.rsi.array[i] = rsi_values[i]
                except ImportError:
                    self.strategy.logger.warning("TA-Lib not available, using Backtrader's RSI")
                    self.strategy.rsi = bt.indicators.RSI(
                        self.strategy.data,
                        period=self.params["rsi_period"]
                    )
            else:
                self.strategy.rsi = bt.indicators.RSI(
                    self.strategy.data,
                    period=self.params["rsi_period"]
                )
        
        # Initialize Volume MA
        use_talib = getattr(self.strategy, 'use_talib', False)
        if use_talib:
            try:
                import talib
                # Calculate Volume MA using TA-Lib
                volume = np.array([self.strategy.data.volume[i] for i in range(len(self.strategy.data))])
                volume_ma = talib.SMA(volume, timeperiod=self.params["volume_ma_period"])
                
                # Initialize Backtrader Volume MA
                self.strategy.volume_ma = bt.indicators.SMA(
                    self.strategy.data.volume,
                    period=self.params["volume_ma_period"]
                )
                
                # Update Volume MA values one by one
                for i in range(len(self.strategy.data)):
                    if i < len(volume_ma):
                        self.strategy.volume_ma.array[i] = volume_ma[i]
            except ImportError:
                self.strategy.logger.warning("TA-Lib not available, using Backtrader's Volume MA")
                self.strategy.volume_ma = bt.indicators.SMA(
                    self.strategy.data.volume,
                    period=self.params["volume_ma_period"]
                )
        else:
            self.strategy.volume_ma = bt.indicators.SMA(
                self.strategy.data.volume,
                period=self.params["volume_ma_period"]
            )
        
        # Initialize Supertrend
        use_talib = getattr(self.strategy, 'use_talib', False)
        if use_talib:
            try:
                import talib
                # Calculate ATR using TA-Lib
                high_prices = np.array([self.strategy.data.high[i] for i in range(len(self.strategy.data))])
                low_prices = np.array([self.strategy.data.low[i] for i in range(len(self.strategy.data))])
                close_prices = np.array([self.strategy.data.close[i] for i in range(len(self.strategy.data))])
                
                atr = talib.ATR(high_prices, low_prices, close_prices, timeperiod=self.params["supertrend_period"])
                
                # Calculate Supertrend
                supertrend = np.zeros_like(close_prices)
                direction = np.zeros_like(close_prices)
                
                for i in range(1, len(close_prices)):
                    # Calculate basic upper and lower bands
                    basic_upper = (high_prices[i] + low_prices[i]) / 2 + self.params["supertrend_multiplier"] * atr[i]
                    basic_lower = (high_prices[i] + low_prices[i]) / 2 - self.params["supertrend_multiplier"] * atr[i]
                    
                    # Initialize direction
                    if i == 1:
                        direction[i] = 1 if close_prices[i] > basic_upper else -1
                        supertrend[i] = basic_lower if direction[i] == 1 else basic_upper
                    else:
                        # Adjust final upper and lower bands
                        final_upper = basic_upper if (basic_upper < supertrend[i-1] or close_prices[i-1] > supertrend[i-1]) else supertrend[i-1]
                        final_lower = basic_lower if (basic_lower > supertrend[i-1] or close_prices[i-1] < supertrend[i-1]) else supertrend[i-1]
                        
                        # Determine trend direction
                        if supertrend[i-1] == final_upper:
                            direction[i] = 1 if close_prices[i] > final_upper else -1
                        else:
                            direction[i] = -1 if close_prices[i] < final_lower else 1
                        
                        # Set Supertrend value
                        supertrend[i] = final_lower if direction[i] == 1 else final_upper
                
                # Initialize Backtrader Supertrend
                self.strategy.supertrend = bt.indicators.Supertrend(
                    self.strategy.data,
                    period=self.params["supertrend_period"],
                    multiplier=self.params["supertrend_multiplier"]
                )
                
                # Update Supertrend values one by one
                for i in range(len(self.strategy.data)):
                    if i < len(supertrend):
                        self.strategy.supertrend.array[i] = supertrend[i]
            except ImportError:
                self.strategy.logger.warning("TA-Lib not available, using Backtrader's Supertrend")
                self.strategy.supertrend = bt.indicators.Supertrend(
                    self.strategy.data,
                    period=self.params["supertrend_period"],
                    multiplier=self.params["supertrend_multiplier"]
                )
        else:
            self.strategy.supertrend = bt.indicators.Supertrend(
                self.strategy.data,
                period=self.params["supertrend_period"],
                multiplier=self.params["supertrend_multiplier"]
            )

    def should_enter(self) -> bool:
        """Check if we should enter a position"""
        if not hasattr(self.strategy, 'rsi') or not hasattr(self.strategy, 'volume_ma') or not hasattr(self.strategy, 'supertrend'):
            return False

        # Check RSI condition
        rsi_oversold = self.strategy.rsi[0] < self.params["rsi_oversold"]
        
        # Check Volume condition
        volume_increasing = self.strategy.data.volume[0] > self.strategy.volume_ma[0]
        
        # Check Supertrend condition
        current_price = self.strategy.data.close[0]
        supertrend_value = self.strategy.supertrend[0]
        
        # Check if price is above Supertrend (bullish)
        above_supertrend = current_price > supertrend_value
        
        return rsi_oversold and volume_increasing and above_supertrend
