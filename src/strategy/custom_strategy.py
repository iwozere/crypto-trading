# custom_strategy.py - Improved version with a new approach

import backtrader as bt
from typing import Dict, Any
from entry_mixin_factory import get_entry_mixin, get_entry_mixin_from_config
from exit_mixin_factory import get_exit_mixin, get_exit_mixin_from_config

class CustomStrategy(bt.Strategy):
    """
    Main strategy with support for modular entry/exit mixins
    """
    
    def __init__(self):
        super().__init__()
        
        # Initialization of entry mixin
        self._init_entry_mixin()
        
        # Initialization of exit mixin
        self._init_exit_mixin()
    
    def _init_entry_mixin(self):
        """Initialization of entry mixin"""
        entry_logic = self.p.entry_logic
        
        # Variant 1: Configuration contains name and parameters separately
        if isinstance(entry_logic, dict) and 'name' in entry_logic:
            entry_name = entry_logic['name']
            entry_params = entry_logic.get('params', {})
            self.entry_mixin = get_entry_mixin(entry_name, entry_params)
        
        # Variant 2: Full configuration (preferred)
        elif isinstance(entry_logic, dict):
            self.entry_mixin = get_entry_mixin_from_config(entry_logic)
        
        else:
            raise ValueError(f"Invalid entry_logic format: {entry_logic}")
        
        # Initialize the mixin with the strategy
        self.entry_mixin.init_entry(strategy=self)
    
    def _init_exit_mixin(self):
        """Initialization of exit mixin"""
        exit_logic = self.p.exit_logic
        
        if isinstance(exit_logic, dict) and 'name' in exit_logic:
            exit_name = exit_logic['name']
            exit_params = exit_logic.get('params', {})
            self.exit_mixin = get_exit_mixin(exit_name, exit_params)
        
        elif isinstance(exit_logic, dict):
            self.exit_mixin = get_exit_mixin_from_config(exit_logic)
        
        else:
            raise ValueError(f"Invalid exit_logic format: {exit_logic}")
        
        self.exit_mixin.init_exit(strategy=self)

    def next(self):
        """Основной цикл стратегии"""
        # Check entry conditions (if no open positions)
        if not self.position:
            if self.entry_mixin.should_enter(self):
                size = self._calculate_position_size()
                self.buy(size=size)
                print(f"BUY signal at {self.data.datetime.date(0)} - Price: {self.data.close[0]:.2f}")
        
        # Check exit conditions (if there are open positions)
        elif self.position:
            if self.exit_mixin.should_exit(self):
                self.sell(size=self.position.size)
                print(f"SELL signal at {self.data.datetime.date(0)} - Price: {self.data.close[0]:.2f}")
    
    def _calculate_position_size(self) -> float:
        """
        Calculation of position size
        Can be made customizable or moved to a separate mixin
        """
        # Simple calculation - use 90% of available capital
        available_cash = self.broker.get_cash()
        price = self.data.close[0]
        max_shares = int((available_cash * 0.9) / price)
        return max_shares









# Example of creating a strategy with a new approach
def create_strategy_example():
    """Example of creating a strategy with different configurations"""
    
    # Configuration 1: Simple RSI + BB strategy
    strategy_config_1 = {
        'entry_logic': {
            'name': 'RSIBBMixin',
            'params': {
                'rsi_period': 14,
                'rsi_oversold': 30,
                'bb_period': 20,
                'use_bb_touch': True
            }
        },
        'exit_logic': {
            'name': 'FixedRatioExitMixin',
            'params': {
                'profit_ratio': 1.5,
                'stop_loss_ratio': 0.5
            }
        }
    }
    
    # Configuration 2: More complex strategy with RSI + Ichimoku
    strategy_config_2 = {
        'entry_logic': {
            'name': 'RSIIchimokuMixin',
            'params': {
                'rsi_period': 21,
                'rsi_oversold': 25,
                'tenkan_period': 9,
                'kijun_period': 26,
                'require_above_cloud': True
            }
        },
        'exit_logic': {
            'name': 'TrailingStopExitMixin',
            'params': {
                'trail_percent': 5.0,
                'min_profit_percent': 2.0
            }
        }
    }
    
    return strategy_config_1, strategy_config_2

# Utilities for working with configurations
class StrategyConfigBuilder:
    """Helper for creating strategy configurations"""
    
    def __init__(self):
        self.config = {}
    
    def set_entry_mixin(self, name: str, params: Dict[str, Any] = None):
        """Set entry mixin"""
        self.config['entry_logic'] = {
            'name': name,
            'params': params