import backtrader as bt
from typing import Dict, Any
from .base_entry_mixin import BaseEntryMixin

class RSIVolumeSuperTrendEntryMixin(BaseEntryMixin):
    """
    Entry mixin based on RSI, Volume, and SuperTrend indicators.
    
    Parameters:
    -----------
    rsi_period : int
        Period for RSI calculation (default: 14)
    rsi_oversold : float
        RSI oversold threshold (default: 30)
    volume_ma_period : int
        Period for volume moving average (default: 20)
    volume_threshold : float
        Volume threshold multiplier (default: 1.5)
    supertrend_period : int
        Period for SuperTrend calculation (default: 10)
    supertrend_multiplier : float
        Multiplier for SuperTrend ATR (default: 3.0)
    use_talib : bool
        Whether to use TA-Lib for indicator calculations (default: False)
    """
    
    def __init__(self, params: Dict[str, Any]):
        super().__init__(params)
        self.rsi_period = params.get('rsi_period', 14)
        self.rsi_oversold = params.get('rsi_oversold', 30)
        self.volume_ma_period = params.get('volume_ma_period', 20)
        self.volume_threshold = params.get('volume_threshold', 1.5)
        self.supertrend_period = params.get('supertrend_period', 10)
        self.supertrend_multiplier = params.get('supertrend_multiplier', 3.0)
        self.use_talib = params.get('use_talib', False)
    
    def _init_indicators(self):
        """Initialize indicators"""
        if self.use_talib:
            import talib
            # Create RSI indicator using TA-Lib
            self.rsi = bt.indicators.TALibIndicator(
                self.strategy.data.close,
                talib.RSI,
                period=self.rsi_period
            )
            
            # Create volume MA using TA-Lib
            self.volume_ma = bt.indicators.TALibIndicator(
                self.strategy.data.volume,
                talib.SMA,
                period=self.volume_ma_period
            )
            
            # Create ATR for SuperTrend using TA-Lib
            self.atr = bt.indicators.TALibIndicator(
                self.strategy.data,
                talib.ATR,
                period=self.supertrend_period
            )
        else:
            # Create RSI indicator using Backtrader
            self.rsi = bt.indicators.RSI(
                self.strategy.data.close,
                period=self.rsi_period
            )
            
            # Create volume MA using Backtrader
            self.volume_ma = bt.indicators.SMA(
                self.strategy.data.volume,
                period=self.volume_ma_period
            )
            
            # Create ATR for SuperTrend using Backtrader
            self.atr = bt.indicators.ATR(
                self.strategy.data,
                period=self.supertrend_period
            )
        
        # Calculate SuperTrend
        self._calculate_supertrend()
    
    def _calculate_supertrend(self):
        """Calculate SuperTrend indicator"""
        # Calculate basic upper and lower bands
        hl2 = (self.strategy.data.high + self.strategy.data.low) / 2
        basic_upper = hl2 + (self.supertrend_multiplier * self.atr)
        basic_lower = hl2 - (self.supertrend_multiplier * self.atr)
        
        # Initialize SuperTrend arrays
        self.supertrend = bt.indicators.SuperTrend(
            self.strategy.data,
            period=self.supertrend_period,
            multiplier=self.supertrend_multiplier
        )
    
    def should_enter(self) -> bool:
        """
        Check if we should enter a long position based on RSI, Volume, and SuperTrend.
        
        Returns:
        --------
        bool
            True if we should enter, False otherwise
        """
        # Check if RSI is oversold
        rsi_oversold = self.rsi[0] < self.rsi_oversold
        
        # Check if volume is above threshold
        volume_signal = self.strategy.data.volume[0] > (self.volume_ma[0] * self.volume_threshold)
        
        # Check if price is above SuperTrend
        supertrend_signal = self.strategy.data.close[0] > self.supertrend[0]
        
        return rsi_oversold and volume_signal and supertrend_signal 