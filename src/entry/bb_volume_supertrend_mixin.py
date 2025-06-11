"""
Bollinger Bands, Volume and SuperTrend Entry Mixin

This module implements an entry strategy based on the combination of Bollinger Bands,
Volume, and SuperTrend indicators. The strategy enters a position when:
1. Price touches or crosses below the lower Bollinger Band
2. Volume is above its moving average by the specified multiplier
3. Price is above the SuperTrend indicator (indicating bullish trend)

Parameters:
    bb_period (int): Period for Bollinger Bands calculation (default: 20)
    bb_stddev (float): Standard deviation multiplier for Bollinger Bands (default: 2.0)
    vol_ma_period (int): Period for Volume Moving Average (default: 20)
    st_period (int): Period for SuperTrend calculation (default: 10)
    st_multiplier (float): Multiplier for SuperTrend ATR calculation (default: 3.0)
    use_bb_touch (bool): Whether to require price touching the lower band (default: True)
    min_volume_multiplier (float): Minimum volume multiplier compared to MA (default: 1.0)

This strategy combines mean reversion (Bollinger Bands), volume confirmation, and trend following
(SuperTrend) to identify potential entry points. It's particularly effective in ranging markets
where you want to enter on oversold conditions with strong volume confirmation and trend support.
"""

from typing import Dict, Any
from src.entry.entry_mixin import BaseEntryMixin

class BBVolumeSuperTrendEntryMixin(BaseEntryMixin):
    """Entry mixin на основе Bollinger Bands, Volume и SuperTrend"""
    
    def get_required_params(self) -> list:
        """There are no required parameters - all have default values"""
        return []
    
    def get_default_params(self) -> Dict[str, Any]:
        """Default parameters"""
        return {
            'bb_period': 20,
            'bb_stddev': 2.0,
            'vol_ma_period': 20,
            'st_period': 10,
            'st_multiplier': 3.0,
            'use_bb_touch': True,  # Require touching the Bollinger Bands
            'min_volume_multiplier': 1.0  # Minimum volume multiplier compared to MA
        }
    
    def _init_indicators(self):
        """Initialization of Bollinger Bands, Volume and SuperTrend indicators"""
        if self.strategy is None:
            raise ValueError("Strategy must be set before initializing indicators")
        
        # Create indicators with parameters from configuration
        self.indicators['bb'] = self.strategy.data.bollinger_bands(
            period=self.get_param('bb_period'),
            stddev=self.get_param('bb_stddev')
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
        Entry logic: Price touching lower BB band, volume above MA,
        and price above SuperTrend
        """
        if not self.indicators:
            return False
        
        current_price = strategy.data.close[0]
        current_volume = strategy.data.volume[0]
        vol_ma = self.indicators['vol_ma'][0]
        supertrend = self.indicators['supertrend'][0]
        
        # Check volume
        volume_ok = current_volume >= vol_ma * self.get_param('min_volume_multiplier')
        
        # Check touching the Bollinger Bands (if enabled)
        bb_condition = True
        if self.get_param('use_bb_touch'):
            bb_lower = self.indicators['bb'].lines.bot[0]
            bb_condition = current_price <= bb_lower * 1.01  # Small tolerance
        
        # Check SuperTrend
        supertrend_condition = supertrend < current_price
        
        return bb_condition and volume_ok and supertrend_condition 