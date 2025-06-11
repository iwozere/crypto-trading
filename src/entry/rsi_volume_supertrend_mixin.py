from typing import Dict, Any
from src.entry.entry_mixin import BaseEntryMixin

class RSIVolumeSuperTrendEntryMixin(BaseEntryMixin):
    """Entry mixin на основе RSI, Volume и SuperTrend"""
    
    def get_required_params(self) -> list:
        """There are no required parameters - all have default values"""
        return []
    
    def get_default_params(self) -> Dict[str, Any]:
        """Default parameters"""
        return {
            'rsi_period': 14,
            'rsi_oversold': 30,
            'vol_ma_period': 20,
            'st_period': 10,
            'st_multiplier': 3.0,
            'min_volume_multiplier': 1.0  # Minimum volume multiplier compared to MA
        }
    
    def _init_indicators(self):
        """Initialization of RSI, Volume and SuperTrend indicators"""
        if self.strategy is None:
            raise ValueError("Strategy must be set before initializing indicators")
        
        # Create indicators with parameters from configuration
        self.indicators['rsi'] = self.strategy.data.rsi(
            period=self.get_param('rsi_period')
        )
        self.indicators['vol_ma'] = self.strategy.data.sma(
            self.strategy.data.volume,
            period=self.get_param('vol_ma_period')
        )
        self.indicators['supertrend'] = self.strategy.data.supertrend(
            period=self.get_param('st_period'),
            multiplier=self.get_param('st_multiplier')
        )
    
    def should_enter(self, strategy) -> bool:
        """
        Entry logic: RSI in oversold zone, volume above MA,
        and price above SuperTrend
        """
        if not self.indicators:
            return False
        
        rsi = self.indicators['rsi'][0]
        current_price = strategy.data.close[0]
        current_volume = strategy.data.volume[0]
        vol_ma = self.indicators['vol_ma'][0]
        supertrend = self.indicators['supertrend'][0]
        
        # Check RSI
        rsi_oversold = rsi < self.get_param('rsi_oversold')
        
        # Check volume
        volume_ok = current_volume >= vol_ma * self.get_param('min_volume_multiplier')
        
        # Check SuperTrend
        supertrend_condition = supertrend < current_price
        
        return rsi_oversold and volume_ok and supertrend_condition 