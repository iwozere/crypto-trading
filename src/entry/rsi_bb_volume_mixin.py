from typing import Dict, Any
from src.entry.entry_mixin import BaseEntryMixin

class RSIBBVolumeEntryMixin(BaseEntryMixin):
    """Entry mixin на основе RSI, Bollinger Bands и Volume"""
    
    def get_required_params(self) -> list:
        """There are no required parameters - all have default values"""
        return []
    
    def get_default_params(self) -> Dict[str, Any]:
        """Default parameters"""
        return {
            'rsi_period': 14,
            'rsi_oversold': 30,
            'bb_period': 20,
            'bb_stddev': 2.0,
            'vol_ma_period': 20,
            'use_bb_touch': True,  # Require touching the Bollinger Bands
            'min_volume_multiplier': 1.0  # Minimum volume multiplier compared to MA
        }
    
    def _init_indicators(self):
        """Initialization of RSI, Bollinger Bands and Volume indicators"""
        if self.strategy is None:
            raise ValueError("Strategy must be set before initializing indicators")
        
        # Create indicators with parameters from configuration
        self.indicators['rsi'] = self.strategy.data.rsi(
            period=self.get_param('rsi_period')
        )
        self.indicators['bb'] = self.strategy.data.bollinger_bands(
            period=self.get_param('bb_period'),
            stddev=self.get_param('bb_stddev')
        )
        self.indicators['vol_ma'] = self.strategy.data.sma(
            self.strategy.data.volume,
            period=self.get_param('vol_ma_period')
        )
    
    def should_enter(self, strategy) -> bool:
        """
        Entry logic: RSI in the oversold zone, touching the lower BB band,
        and volume above the moving average
        """
        if not self.indicators:
            return False
        
        rsi = self.indicators['rsi'][0]
        current_price = strategy.data.close[0]
        current_volume = strategy.data.volume[0]
        vol_ma = self.indicators['vol_ma'][0]
        
        # Check RSI
        rsi_oversold = rsi < self.get_param('rsi_oversold')
        
        # Check volume
        volume_ok = current_volume >= vol_ma * self.get_param('min_volume_multiplier')
        
        # Check touching the Bollinger Bands (if enabled)
        bb_condition = True
        if self.get_param('use_bb_touch'):
            bb_lower = self.indicators['bb'].lines.bot[0]
            bb_condition = current_price <= bb_lower * 1.01  # Small tolerance
        
        return rsi_oversold and volume_ok and bb_condition 