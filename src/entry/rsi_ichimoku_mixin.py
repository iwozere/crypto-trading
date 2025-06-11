"""
RSI and Ichimoku Cloud Entry Mixin

This module implements an entry strategy based on the combination of Relative Strength Index (RSI)
and Ichimoku Cloud indicators. The strategy enters a position when:
1. RSI is in the oversold zone (below the configured threshold)
2. Price is below the Ichimoku Cloud (bearish cloud)
3. Price crosses above the Tenkan-sen (Conversion Line)

Parameters:
    rsi_period (int): Period for RSI calculation (default: 14)
    rsi_oversold (float): RSI threshold for oversold condition (default: 30)
    ichimoku_tenkan (int): Period for Tenkan-sen calculation (default: 9)
    ichimoku_kijun (int): Period for Kijun-sen calculation (default: 26)
    ichimoku_senkou_span_b (int): Period for Senkou Span B calculation (default: 52)
    ichimoku_displacement (int): Displacement for Ichimoku Cloud (default: 26)

This strategy combines mean reversion (RSI) with trend following (Ichimoku) to identify potential
reversal points in the market. It's particularly effective in trending markets where you want to
catch the beginning of a new trend after a pullback.
"""

import backtrader as bt
from typing import Dict, Any
from src.entry.entry_mixin import BaseEntryMixin

class RSIIchimokuEntryMixin(BaseEntryMixin):
    """Entry mixin based on RSI and Ichimoku cloud"""
    
    def get_required_params(self) -> list:
        # We can make some parameters required
        return ['tenkan_period', 'kijun_period']
    
    def get_default_params(self) -> Dict[str, Any]:
        return {
            'rsi_period': 14,
            'rsi_oversold': 30,
            'tenkan_period': 9,  # Will be required
            'kijun_period': 26,  # Will be required
            'senkou_span_b_period': 52,
            'displacement': 26,
            'require_above_cloud': True
        }
    
    def _init_indicators(self):
        """Initialize RSI and Ichimoku Cloud indicators"""
        if self.strategy is None:
            raise ValueError("Strategy must be set before initializing indicators")
        
        # Create RSI indicator
        self.indicators['rsi'] = bt.indicators.RSI(
            self.strategy.data.close,
            period=self.get_param('rsi_period')
        )
        
        # Create Ichimoku Cloud components
        self.indicators['tenkan'] = bt.indicators.IchimokuTenkanSen(
            self.strategy.data,
            period=self.get_param('tenkan_period')
        )
        
        self.indicators['kijun'] = bt.indicators.IchimokuKijunSen(
            self.strategy.data,
            period=self.get_param('kijun_period')
        )
        
        self.indicators['senkou_span_a'] = bt.indicators.IchimokuSenkouSpanA(
            self.strategy.data,
            tenkan_period=self.get_param('tenkan_period'),
            kijun_period=self.get_param('kijun_period')
        )
        
        self.indicators['senkou_span_b'] = bt.indicators.IchimokuSenkouSpanB(
            self.strategy.data,
            period=self.get_param('senkou_span_b_period')
        )
        
        self.indicators['chikou_span'] = bt.indicators.IchimokuChikouSpan(
            self.strategy.data,
            displacement=self.get_param('displacement')
        )
    
    def should_enter(self, strategy) -> bool:
        """Entry logic: RSI oversold and Ichimoku Cloud conditions"""
        if not self.indicators:
            return False
        
        rsi = self.indicators['rsi'][0]
        current_price = strategy.data.close[0]
        
        # RSI condition
        rsi_ok = rsi < self.get_param('rsi_oversold')
        
        # Ichimoku conditions
        tenkan = self.indicators['tenkan'][0]
        kijun = self.indicators['kijun'][0]
        senkou_span_a = self.indicators['senkou_span_a'][0]
        senkou_span_b = self.indicators['senkou_span_b'][0]
        
        # Bullish signal: Tenkan-sen crosses above Kijun-sen
        tenkan_kijun_cross = tenkan > kijun
        
        # Additional condition - price above the cloud (if required)
        above_cloud = True
        if self.get_param('require_above_cloud'):
            cloud_top = max(senkou_span_a, senkou_span_b)
            above_cloud = current_price > cloud_top
        
        return rsi_ok and tenkan_kijun_cross and above_cloud