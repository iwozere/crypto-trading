"""
ATR-based Exit Mixin

This module implements an exit strategy based on the Average True Range (ATR) indicator.
The strategy exits a position when:
1. Price reaches the take profit level (entry price + ATR * tp_multiplier)
2. Price reaches the stop loss level (entry price - ATR * sl_multiplier)

Parameters:
    atr_period (int): Period for ATR calculation (default: 14)
    tp_multiplier (float): Multiplier for take profit level (default: 2.0)
    sl_multiplier (float): Multiplier for stop loss level (default: 1.0)
    use_dynamic_tp (bool): Whether to adjust TP based on ATR changes (default: False)
    use_dynamic_sl (bool): Whether to adjust SL based on ATR changes (default: False)

This strategy uses ATR to dynamically adjust take profit and stop loss levels based on market
volatility. It's particularly effective in volatile markets where fixed percentage stops might
be too tight or too wide.
"""

from typing import Dict, Any
from src.exit.exit_mixin import BaseExitMixin
import backtrader as bt

class ATRExitMixin(BaseExitMixin):
    """Exit mixin на основе ATR для расчета уровней take profit и stop loss"""
    
    def get_required_params(self) -> list:
        """There are no required parameters - all have default values"""
        return []
    
    def get_default_params(self) -> Dict[str, Any]:
        """Default parameters"""
        return {
            'atr_period': 14,  # Period for ATR calculation
            'tp_multiplier': 2.0,  # Multiplier for take profit level
            'sl_multiplier': 1.0,  # Multiplier for stop loss level
            'use_dynamic_tp': False,  # Whether to adjust TP based on ATR changes
            'use_dynamic_sl': False   # Whether to adjust SL based on ATR changes
        }
    
    def _init_indicators(self):
        """Initialization of ATR indicator"""
        if self.strategy is None:
            raise ValueError("Strategy must be set before initializing indicators")
        
        # Create ATR indicator with parameters from configuration
        self.indicators['atr'] = self.strategy.data.atr(
            period=self.get_param('atr_period')
        )
    
    def should_exit(self, strategy) -> bool:
        """
        Exit logic: Exit when price reaches take profit or stop loss levels
        based on ATR multipliers
        """
        if not self.indicators:
            return False
            
        price = strategy.data.close[0]
        entry_price = strategy.position.price
        atr = self.indicators['atr'][0]
        
        # Calculate take profit and stop loss levels
        if self.get_param('use_dynamic_tp'):
            # Use current ATR for dynamic TP
            tp_level = entry_price + (atr * self.get_param('tp_multiplier'))
        else:
            # Use entry ATR for fixed TP
            tp_level = entry_price + (atr * self.get_param('tp_multiplier'))
            
        if self.get_param('use_dynamic_sl'):
            # Use current ATR for dynamic SL
            sl_level = entry_price - (atr * self.get_param('sl_multiplier'))
        else:
            # Use entry ATR for fixed SL
            sl_level = entry_price - (atr * self.get_param('sl_multiplier'))
        
        # Exit if take profit or stop loss is hit
        return price >= tp_level or price <= sl_level 